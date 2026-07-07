"""Testes de cenário do Boletim (§4): média ponderada + situação combinando as
duas regras configuráveis da escola (média mínima E frequência mínima)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.core.tenant_guard  # noqa: F401
from src.core.database import get_db
from src.core.security import criar_access_token
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.main import app
from src.modules.academico import service as academico
from src.modules.academico.schemas import (
    AnoLetivoCreate,
    AtribuicaoCreate,
    CursoCreate,
    DisciplinaCreate,
    MatriculaCreate,
    SerieCreate,
    TurmaCreate,
)
from src.modules.identidade import service as identidade
from src.modules.identidade.schemas import UsuarioCreate
from src.modules.pessoas import service as pessoas
from src.modules.pessoas.schemas import PessoaCreate, VinculoCreate
from src.modules.tenancy.models import Tenant
from src.shared.models import Base


@pytest.fixture()
def ambiente():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def _get_db_override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db_override

    with Session() as db:
        identidade.garantir_papeis_catalogo(db)
        ta = Tenant(nome="Escola A", subdominio="escola-a")
        db.add(ta)
        db.commit()
        id_a = ta.id

        tok = set_current_tenant(id_a)
        try:
            u_sec = identidade.criar_usuario(db, UsuarioCreate(nome="Sec", email="sec@a.dev", senha="senha1234", papeis=["secretaria"]))
            u_resp = identidade.criar_usuario(db, UsuarioCreate(nome="Resp", email="resp@a.dev", senha="senha1234", papeis=["responsavel"]))

            p_prof = pessoas.criar_pessoa(db, PessoaCreate(nome="Professor"))
            p_resp = pessoas.criar_pessoa(db, PessoaCreate(nome="Responsável", usuario_id=u_resp.id))
            p_dep = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Dependente"))
            p_outro = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Outro"))
            pessoas.criar_vinculo(db, VinculoCreate(responsavel_id=p_resp.id, aluno_id=p_dep.id))

            ano = academico.criar_ano_letivo(db, AnoLetivoCreate(ano=2026))
            curso = academico.criar_curso(db, CursoCreate(nome="EF"))
            serie = academico.criar_serie(db, SerieCreate(curso_id=curso.id, nome="1º ano", ordem=1))
            disc = academico.criar_disciplina(db, DisciplinaCreate(nome="Matemática"))
            turma = academico.criar_turma(db, TurmaCreate(serie_id=serie.id, ano_letivo_id=ano.id, nome="A"))
            academico.atribuir_disciplina(db, turma.id, AtribuicaoCreate(disciplina_id=disc.id, professor_id=p_prof.id))
            mat_dep = academico.criar_matricula(db, MatriculaCreate(aluno_id=p_dep.id, turma_id=turma.id))
            mat_outro = academico.criar_matricula(db, MatriculaCreate(aluno_id=p_outro.id, turma_id=turma.id))
        finally:
            reset_current_tenant(tok)

    env = SimpleNamespace(
        client=TestClient(app),
        id_a=id_a,
        tok_sec=criar_access_token(usuario_id=u_sec.id, tenant_id=id_a, papeis=["secretaria"]),
        tok_resp=criar_access_token(usuario_id=u_resp.id, tenant_id=id_a, papeis=["responsavel"]),
        disc_id=disc.id,
        mat_dep_id=mat_dep.id,
        mat_outro_id=mat_outro.id,
    )
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


_DIAS = ["2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05"]


def _h(env):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {env.tok_sec}"}


def _config(env, media_minima, num_periodos, pesos, freq_min=75):
    r = env.client.put(
        "/v1/academico/config",
        json={
            "media_minima": media_minima,
            "num_periodos": num_periodos,
            "pesos_periodos": pesos,
            "frequencia_minima_percentual": freq_min,
        },
        headers=_h(env),
    )
    assert r.status_code == 200


def _notas(env, valores, matricula_id=None):
    for periodo, valor in enumerate(valores, start=1):
        r = env.client.post(
            "/v1/academico/notas",
            json={
                "matricula_id": str(matricula_id or env.mat_dep_id),
                "disciplina_id": str(env.disc_id),
                "periodo": periodo,
                "valor": valor,
            },
            headers=_h(env),
        )
        assert r.status_code == 201


def _frequencia(env, presencas, total, matricula_id=None):
    """Lança `total` dias, os `presencas` primeiros como presente."""
    for i in range(total):
        r = env.client.post(
            "/v1/academico/frequencias",
            json={
                "matricula_id": str(matricula_id or env.mat_dep_id),
                "data": _DIAS[i],
                "presente": i < presencas,
            },
            headers=_h(env),
        )
        assert r.status_code == 201


def _boletim(env, token=None):
    return env.client.get(
        f"/v1/academico/matriculas/{env.mat_dep_id}/boletim",
        headers={"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {token or env.tok_sec}"},
    )


def test_aprovado(ambiente):
    _notas(ambiente, [7, 7, 7, 7])
    _frequencia(ambiente, 4, 4)  # 100%
    b = _boletim(ambiente).json()
    assert float(b["disciplinas"][0]["media"]) == 7.0
    assert b["disciplinas"][0]["situacao"] == "aprovado"
    assert b["situacao_final"] == "aprovado"


def test_reprovado_por_nota(ambiente):
    _notas(ambiente, [5, 5, 5, 5])  # média 5 < 6
    _frequencia(ambiente, 4, 4)
    b = _boletim(ambiente).json()
    assert b["disciplinas"][0]["situacao"] == "reprovado_nota"
    assert b["situacao_final"] == "reprovado_nota"


def test_reprovado_por_frequencia(ambiente):
    _notas(ambiente, [8, 8, 8, 8])  # média ok
    _frequencia(ambiente, 2, 4)  # 50% < 75%
    b = _boletim(ambiente).json()
    assert b["disciplinas"][0]["situacao"] == "aprovado"
    assert float(b["frequencia"]["percentual"]) == 50.0
    assert b["situacao_final"] == "reprovado_frequencia"


def test_cursando_com_periodo_faltando(ambiente):
    _notas(ambiente, [7, 7, 7])  # só 3 de 4 períodos
    _frequencia(ambiente, 4, 4)
    b = _boletim(ambiente).json()
    assert b["disciplinas"][0]["completa"] is False
    assert b["disciplinas"][0]["situacao"] == "cursando"
    assert b["situacao_final"] == "cursando"


def test_media_ponderada_respeita_pesos(ambiente):
    # pesos [1,1,1,3]: (10+10+10+2*3)/6 = 36/6 = 6.0 (média simples seria 8.0)
    _config(ambiente, media_minima=6.0, num_periodos=4, pesos=[1, 1, 1, 3])
    _notas(ambiente, [10, 10, 10, 2])
    _frequencia(ambiente, 4, 4)
    b = _boletim(ambiente).json()
    assert float(b["disciplinas"][0]["media"]) == 6.0
    assert b["situacao_final"] == "aprovado"  # 6.0 >= 6.0


def test_media_minima_configuravel_muda_situacao(ambiente):
    # Mesmas notas (média 6.0), mas a escola exige 7.0 → reprovado_nota.
    _config(ambiente, media_minima=7.0, num_periodos=4, pesos=[1, 1, 1, 1])
    _notas(ambiente, [6, 6, 6, 6])
    _frequencia(ambiente, 4, 4)
    b = _boletim(ambiente).json()
    assert float(b["media_minima"]) == 7.0
    assert b["disciplinas"][0]["situacao"] == "reprovado_nota"
    assert b["situacao_final"] == "reprovado_nota"


def test_num_periodos_configuravel(ambiente):
    # Escola com 2 períodos: 2 notas já fecham o ano.
    _config(ambiente, media_minima=6.0, num_periodos=2, pesos=[1, 1])
    _notas(ambiente, [6, 8])  # média 7.0
    _frequencia(ambiente, 4, 4)
    b = _boletim(ambiente).json()
    assert b["num_periodos"] == 2
    assert b["disciplinas"][0]["completa"] is True
    assert float(b["disciplinas"][0]["media"]) == 7.0
    assert b["situacao_final"] == "aprovado"


def test_responsavel_ve_boletim_do_dependente(ambiente):
    _notas(ambiente, [7, 7, 7, 7])
    _frequencia(ambiente, 4, 4)
    r = _boletim(ambiente, token=ambiente.tok_resp)
    assert r.status_code == 200
    assert r.json()["situacao_final"] == "aprovado"


def test_responsavel_nao_ve_boletim_de_outro_404(ambiente):
    r = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_outro_id}/boletim",
        headers={"X-Tenant-ID": str(ambiente.id_a), "Authorization": f"Bearer {ambiente.tok_resp}"},
    )
    assert r.status_code == 404
