"""Testes de Frequência: RBAC/ACL de docência, upsert e cálculo do percentual."""

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
from src.shared.deps import Principal
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
            u_prof = identidade.criar_usuario(db, UsuarioCreate(nome="Prof", email="prof@a.dev", senha="senha1234", papeis=["professor"]))
            u_prof2 = identidade.criar_usuario(db, UsuarioCreate(nome="Prof2", email="prof2@a.dev", senha="senha1234", papeis=["professor"]))
            u_resp = identidade.criar_usuario(db, UsuarioCreate(nome="Resp", email="resp@a.dev", senha="senha1234", papeis=["responsavel"]))

            p_prof = pessoas.criar_pessoa(db, PessoaCreate(nome="Professor", usuario_id=u_prof.id))
            p_prof2 = pessoas.criar_pessoa(db, PessoaCreate(nome="Professor Outro", usuario_id=u_prof2.id))
            p_resp = pessoas.criar_pessoa(db, PessoaCreate(nome="Responsável", usuario_id=u_resp.id))
            p_dep = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Dependente"))
            p_outro = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Outro"))
            pessoas.criar_vinculo(db, VinculoCreate(responsavel_id=p_resp.id, aluno_id=p_dep.id))

            ano = academico.criar_ano_letivo(db, AnoLetivoCreate(ano=2026))
            curso = academico.criar_curso(db, CursoCreate(nome="EF"))
            serie = academico.criar_serie(db, SerieCreate(curso_id=curso.id, nome="1º ano", ordem=1))
            disciplina = academico.criar_disciplina(db, DisciplinaCreate(nome="Matemática"))
            turma = academico.criar_turma(db, TurmaCreate(serie_id=serie.id, ano_letivo_id=ano.id, nome="A"))
            # p_prof leciona nesta turma; p_prof2 não.
            prof_principal = Principal(usuario=u_prof, papeis=["professor"])
            academico.atribuir_disciplina(db, turma.id, AtribuicaoCreate(disciplina_id=disciplina.id, professor_id=p_prof.id))
            mat_dep = academico.criar_matricula(db, MatriculaCreate(aluno_id=p_dep.id, turma_id=turma.id))
            mat_outro = academico.criar_matricula(db, MatriculaCreate(aluno_id=p_outro.id, turma_id=turma.id))
        finally:
            reset_current_tenant(tok)

    env = SimpleNamespace(
        client=TestClient(app),
        id_a=id_a,
        tok_sec=criar_access_token(usuario_id=u_sec.id, tenant_id=id_a, papeis=["secretaria"]),
        tok_prof=criar_access_token(usuario_id=u_prof.id, tenant_id=id_a, papeis=["professor"]),
        tok_prof2=criar_access_token(usuario_id=u_prof2.id, tenant_id=id_a, papeis=["professor"]),
        tok_resp=criar_access_token(usuario_id=u_resp.id, tenant_id=id_a, papeis=["responsavel"]),
        mat_dep_id=mat_dep.id,
        mat_outro_id=mat_outro.id,
    )
    _ = prof_principal  # (só documental; a ACL real usa o token)
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


def _h(env, token):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {token}"}


def _reg(env, token, matricula_id, data, presente=True, justificada=False):
    return env.client.post(
        "/v1/academico/frequencias",
        json={
            "matricula_id": str(matricula_id),
            "data": data,
            "presente": presente,
            "justificada": justificada,
        },
        headers=_h(env, token),
    )


def test_professor_da_turma_lanca(ambiente):
    r = _reg(ambiente, ambiente.tok_prof, ambiente.mat_dep_id, "2026-03-02")
    assert r.status_code == 201
    assert r.json()["presente"] is True


def test_professor_de_fora_403(ambiente):
    r = _reg(ambiente, ambiente.tok_prof2, ambiente.mat_dep_id, "2026-03-02")
    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "sem_permissao_turma"


def test_secretaria_lanca(ambiente):
    r = _reg(ambiente, ambiente.tok_sec, ambiente.mat_dep_id, "2026-03-03", presente=False, justificada=True)
    assert r.status_code == 201
    assert r.json()["presente"] is False
    assert r.json()["justificada"] is True


def test_upsert_relancar_mesmo_dia_atualiza(ambiente):
    _reg(ambiente, ambiente.tok_prof, ambiente.mat_dep_id, "2026-03-04", presente=True)
    r = _reg(ambiente, ambiente.tok_prof, ambiente.mat_dep_id, "2026-03-04", presente=False)
    assert r.status_code == 201
    assert r.json()["presente"] is False
    # não duplicou: só um registro para o dia
    lst = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_dep_id}/frequencias",
        headers=_h(ambiente, ambiente.tok_sec),
    )
    dias = [f for f in lst.json() if f["data"] == "2026-03-04"]
    assert len(dias) == 1


def test_resumo_percentual(ambiente):
    # 3 presenças em 4 dias letivos = 75% → suficiente (mínimo default 75%)
    _reg(ambiente, ambiente.tok_prof, ambiente.mat_dep_id, "2026-03-02", presente=True)
    _reg(ambiente, ambiente.tok_prof, ambiente.mat_dep_id, "2026-03-03", presente=True)
    _reg(ambiente, ambiente.tok_prof, ambiente.mat_dep_id, "2026-03-04", presente=True)
    _reg(ambiente, ambiente.tok_prof, ambiente.mat_dep_id, "2026-03-05", presente=False, justificada=True)

    r = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_dep_id}/frequencia-resumo",
        headers=_h(ambiente, ambiente.tok_sec),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dias_letivos"] == 4
    assert body["presencas"] == 3
    assert body["faltas"] == 1
    assert body["faltas_justificadas"] == 1
    assert float(body["percentual"]) == 75.0
    assert float(body["frequencia_minima"]) == 75.0
    assert body["suficiente"] is True


def test_resumo_sem_registros_nao_suficiente(ambiente):
    r = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_dep_id}/frequencia-resumo",
        headers=_h(ambiente, ambiente.tok_sec),
    )
    body = r.json()
    assert body["dias_letivos"] == 0
    assert float(body["percentual"]) == 0.0
    assert body["suficiente"] is False


def test_responsavel_ve_frequencia_do_dependente(ambiente):
    _reg(ambiente, ambiente.tok_prof, ambiente.mat_dep_id, "2026-03-02", presente=True)
    r = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_dep_id}/frequencias",
        headers=_h(ambiente, ambiente.tok_resp),
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_responsavel_nao_ve_frequencia_de_outro_404(ambiente):
    r = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_outro_id}/frequencias",
        headers=_h(ambiente, ambiente.tok_resp),
    )
    assert r.status_code == 404
