"""Testes de Notas: ACL de disciplina, período vs config, upsert e auditoria (§9)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.core.tenant_guard  # noqa: F401
from src.core import audit
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
            mat = academico.criar_disciplina(db, DisciplinaCreate(nome="Matemática"))
            port = academico.criar_disciplina(db, DisciplinaCreate(nome="Português"))
            turma = academico.criar_turma(db, TurmaCreate(serie_id=serie.id, ano_letivo_id=ano.id, nome="A"))
            # p_prof leciona Matemática; p_prof2 leciona Português (mesma turma).
            academico.atribuir_disciplina(db, turma.id, AtribuicaoCreate(disciplina_id=mat.id, professor_id=p_prof.id))
            academico.atribuir_disciplina(db, turma.id, AtribuicaoCreate(disciplina_id=port.id, professor_id=p_prof2.id))
            mat_dep = academico.criar_matricula(db, MatriculaCreate(aluno_id=p_dep.id, turma_id=turma.id))
            mat_outro = academico.criar_matricula(db, MatriculaCreate(aluno_id=p_outro.id, turma_id=turma.id))
        finally:
            reset_current_tenant(tok)

    env = SimpleNamespace(
        Session=Session,
        client=TestClient(app),
        id_a=id_a,
        tok_sec=criar_access_token(usuario_id=u_sec.id, tenant_id=id_a, papeis=["secretaria"]),
        tok_prof=criar_access_token(usuario_id=u_prof.id, tenant_id=id_a, papeis=["professor"]),
        tok_prof2=criar_access_token(usuario_id=u_prof2.id, tenant_id=id_a, papeis=["professor"]),
        tok_resp=criar_access_token(usuario_id=u_resp.id, tenant_id=id_a, papeis=["responsavel"]),
        u_prof_id=u_prof.id,
        disc_mat_id=mat.id,
        disc_port_id=port.id,
        mat_dep_id=mat_dep.id,
        mat_outro_id=mat_outro.id,
    )
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


def _h(env, token):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {token}"}


def _nota(env, token, disciplina_id, periodo, valor, matricula_id=None):
    return env.client.post(
        "/v1/academico/notas",
        json={
            "matricula_id": str(matricula_id or env.mat_dep_id),
            "disciplina_id": str(disciplina_id),
            "periodo": periodo,
            "valor": valor,
        },
        headers=_h(env, token),
    )


def _trilha_notas(env):
    tok = set_current_tenant(env.id_a)
    try:
        with env.Session() as db:
            return audit.listar(db, entidade="nota")
    finally:
        reset_current_tenant(tok)


def test_professor_da_disciplina_lanca(ambiente):
    r = _nota(ambiente, ambiente.tok_prof, ambiente.disc_mat_id, 1, 8.5)
    assert r.status_code == 201
    assert float(r.json()["valor"]) == 8.5


def test_professor_de_outra_disciplina_403(ambiente):
    # p_prof2 leciona Português, tenta lançar em Matemática
    r = _nota(ambiente, ambiente.tok_prof2, ambiente.disc_mat_id, 1, 7.0)
    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "sem_permissao_disciplina"


def test_secretaria_lanca(ambiente):
    r = _nota(ambiente, ambiente.tok_sec, ambiente.disc_mat_id, 2, 9.0)
    assert r.status_code == 201


def test_periodo_fora_da_config_400(ambiente):
    # config default: num_periodos = 4
    r = _nota(ambiente, ambiente.tok_prof, ambiente.disc_mat_id, 5, 7.0)
    assert r.status_code == 400
    assert r.json()["erro"]["codigo"] == "periodo_invalido"


def test_upsert_relancar_atualiza_valor(ambiente):
    _nota(ambiente, ambiente.tok_prof, ambiente.disc_mat_id, 1, 6.0)
    r = _nota(ambiente, ambiente.tok_prof, ambiente.disc_mat_id, 1, 9.5)
    assert r.status_code == 201
    assert float(r.json()["valor"]) == 9.5
    lst = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_dep_id}/notas",
        headers=_h(ambiente, ambiente.tok_sec),
    ).json()
    p1 = [n for n in lst if n["periodo"] == 1 and n["disciplina_id"] == str(ambiente.disc_mat_id)]
    assert len(p1) == 1  # não duplicou


def test_auditoria_registra_criacao_e_atualizacao(ambiente):
    _nota(ambiente, ambiente.tok_prof, ambiente.disc_mat_id, 1, 6.0)
    _nota(ambiente, ambiente.tok_prof, ambiente.disc_mat_id, 1, 9.5)

    trilha = _trilha_notas(ambiente)
    acoes = [log.acao for log in trilha]
    assert "criar" in acoes
    assert "atualizar" in acoes

    atualizacao = next(log for log in trilha if log.acao == "atualizar")
    assert atualizacao.usuario_id == ambiente.u_prof_id
    assert atualizacao.dados_antes["valor"] == 6.0
    assert atualizacao.dados_depois["valor"] == 9.5


def test_responsavel_ve_notas_do_dependente(ambiente):
    _nota(ambiente, ambiente.tok_prof, ambiente.disc_mat_id, 1, 8.0)
    r = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_dep_id}/notas",
        headers=_h(ambiente, ambiente.tok_resp),
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_responsavel_nao_ve_notas_de_outro_404(ambiente):
    r = ambiente.client.get(
        f"/v1/academico/matriculas/{ambiente.mat_outro_id}/notas",
        headers=_h(ambiente, ambiente.tok_resp),
    )
    assert r.status_code == 404
