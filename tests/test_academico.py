"""Testes do Acadêmico: RBAC de escrita, validações, duplicata e ACL de matrícula."""

import uuid
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
        tb = Tenant(nome="Escola B", subdominio="escola-b")
        db.add_all([ta, tb])
        db.commit()
        id_a, id_b = ta.id, tb.id

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
            curso = academico.criar_curso(db, CursoCreate(nome="Ensino Fundamental"))
            serie = academico.criar_serie(db, SerieCreate(curso_id=curso.id, nome="1º ano", ordem=1))
            disciplina = academico.criar_disciplina(db, DisciplinaCreate(nome="Matemática"))
            turma = academico.criar_turma(db, TurmaCreate(serie_id=serie.id, ano_letivo_id=ano.id, nome="A"))
            mat_dep = academico.criar_matricula(db, MatriculaCreate(aluno_id=p_dep.id, turma_id=turma.id))
        finally:
            reset_current_tenant(tok)

        tok_b = set_current_tenant(id_b)
        try:
            curso_b = academico.criar_curso(db, CursoCreate(nome="Curso B"))
        finally:
            reset_current_tenant(tok_b)

    env = SimpleNamespace(
        client=TestClient(app),
        id_a=id_a,
        tok_sec=criar_access_token(usuario_id=u_sec.id, tenant_id=id_a, papeis=["secretaria"]),
        tok_resp=criar_access_token(usuario_id=u_resp.id, tenant_id=id_a, papeis=["responsavel"]),
        turma_id=turma.id,
        serie_id=serie.id,
        ano_id=ano.id,
        disciplina_id=disciplina.id,
        professor_id=p_prof.id,
        aluno_dep_id=p_dep.id,
        aluno_outro_id=p_outro.id,
        mat_dep_id=mat_dep.id,
        curso_b_id=curso_b.id,
    )
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


def _h(env, token):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {token}"}


def test_secretaria_cria_curso(ambiente):
    r = ambiente.client.post("/v1/academico/cursos", json={"nome": "Ensino Médio"}, headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 201


def test_responsavel_nao_cria_curso_403(ambiente):
    r = ambiente.client.post("/v1/academico/cursos", json={"nome": "X"}, headers=_h(ambiente, ambiente.tok_resp))
    assert r.status_code == 403


def test_matricula_nova_aluno(ambiente):
    r = ambiente.client.post(
        "/v1/academico/matriculas",
        json={"aluno_id": str(ambiente.aluno_outro_id), "turma_id": str(ambiente.turma_id)},
        headers=_h(ambiente, ambiente.tok_sec),
    )
    assert r.status_code == 201
    assert r.json()["situacao"] == "ativa"
    assert r.json()["aluno_nome"] == "Aluno Outro"  # nome, não só UUID


def test_matricula_duplicada_409(ambiente):
    r = ambiente.client.post(
        "/v1/academico/matriculas",
        json={"aluno_id": str(ambiente.aluno_dep_id), "turma_id": str(ambiente.turma_id)},
        headers=_h(ambiente, ambiente.tok_sec),
    )
    assert r.status_code == 409
    assert r.json()["erro"]["codigo"] == "matricula_duplicada"


def test_acl_responsavel_ve_matricula_do_dependente(ambiente):
    r = ambiente.client.get(f"/v1/academico/matriculas/{ambiente.mat_dep_id}", headers=_h(ambiente, ambiente.tok_resp))
    assert r.status_code == 200


def test_acl_responsavel_nao_ve_matricula_de_outro(ambiente):
    # secretaria matricula o outro aluno; responsável não pode vê-la
    criada = ambiente.client.post(
        "/v1/academico/matriculas",
        json={"aluno_id": str(ambiente.aluno_outro_id), "turma_id": str(ambiente.turma_id)},
        headers=_h(ambiente, ambiente.tok_sec),
    )
    mid = criada.json()["id"]
    r = ambiente.client.get(f"/v1/academico/matriculas/{mid}", headers=_h(ambiente, ambiente.tok_resp))
    assert r.status_code == 404


def test_acl_lista_matriculas_responsavel_so_dependente(ambiente):
    r = ambiente.client.get("/v1/academico/matriculas", headers=_h(ambiente, ambiente.tok_resp))
    ids = {m["id"] for m in r.json()}
    assert ids == {str(ambiente.mat_dep_id)}


def test_atribuir_disciplina_professor(ambiente):
    r = ambiente.client.post(
        f"/v1/academico/turmas/{ambiente.turma_id}/disciplinas",
        json={"disciplina_id": str(ambiente.disciplina_id), "professor_id": str(ambiente.professor_id)},
        headers=_h(ambiente, ambiente.tok_sec),
    )
    assert r.status_code == 201


def test_atribuir_professor_inexistente_404(ambiente):
    r = ambiente.client.post(
        f"/v1/academico/turmas/{ambiente.turma_id}/disciplinas",
        json={"disciplina_id": str(ambiente.disciplina_id), "professor_id": str(uuid.uuid4())},
        headers=_h(ambiente, ambiente.tok_sec),
    )
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "professor_inexistente"


def test_turma_com_serie_inexistente_404(ambiente):
    r = ambiente.client.post(
        "/v1/academico/turmas",
        json={"serie_id": str(uuid.uuid4()), "ano_letivo_id": str(ambiente.ano_id), "nome": "B"},
        headers=_h(ambiente, ambiente.tok_sec),
    )
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "serie_inexistente"


def test_matricula_aluno_inexistente_404(ambiente):
    r = ambiente.client.post(
        "/v1/academico/matriculas",
        json={"aluno_id": str(uuid.uuid4()), "turma_id": str(ambiente.turma_id)},
        headers=_h(ambiente, ambiente.tok_sec),
    )
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "aluno_inexistente"


def test_turma_read_tem_serie_e_ano(ambiente):
    r = ambiente.client.get("/v1/academico/turmas", headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 200
    t = r.json()[0]
    assert t["serie_nome"] == "1º ano"
    assert t["ano"] == 2026


def test_isolamento_tenant_cursos(ambiente):
    r = ambiente.client.get("/v1/academico/cursos", headers=_h(ambiente, ambiente.tok_sec))
    ids = {c["id"] for c in r.json()}
    assert str(ambiente.curso_b_id) not in ids  # curso do tenant B não vaza para A
