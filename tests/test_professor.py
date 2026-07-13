"""Testes da área do professor: minhas atribuições e alunos da turma (ACL de docência)."""

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
from src.modules.pessoas.schemas import PessoaCreate
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

            p_prof = pessoas.criar_pessoa(db, PessoaCreate(nome="Prof. Ana", usuario_id=u_prof.id))
            pessoas.criar_pessoa(db, PessoaCreate(nome="Prof. Beto", usuario_id=u_prof2.id))
            p_a1 = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Um"))
            p_a2 = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Dois"))

            ano = academico.criar_ano_letivo(db, AnoLetivoCreate(ano=2026))
            curso = academico.criar_curso(db, CursoCreate(nome="EF"))
            serie = academico.criar_serie(db, SerieCreate(curso_id=curso.id, nome="5º ano", ordem=5))
            disc = academico.criar_disciplina(db, DisciplinaCreate(nome="Matemática"))
            turma = academico.criar_turma(db, TurmaCreate(serie_id=serie.id, ano_letivo_id=ano.id, nome="A"))
            academico.atribuir_disciplina(db, turma.id, AtribuicaoCreate(disciplina_id=disc.id, professor_id=p_prof.id))
            academico.criar_matricula(db, MatriculaCreate(aluno_id=p_a1.id, turma_id=turma.id))
            academico.criar_matricula(db, MatriculaCreate(aluno_id=p_a2.id, turma_id=turma.id))
        finally:
            reset_current_tenant(tok)

    env = SimpleNamespace(
        client=TestClient(app),
        id_a=id_a,
        tok_sec=criar_access_token(usuario_id=u_sec.id, tenant_id=id_a, papeis=["secretaria"]),
        tok_prof=criar_access_token(usuario_id=u_prof.id, tenant_id=id_a, papeis=["professor"]),
        tok_prof2=criar_access_token(usuario_id=u_prof2.id, tenant_id=id_a, papeis=["professor"]),
        turma_id=turma.id,
    )
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


def _h(env, token):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {token}"}


def test_professor_ve_suas_atribuicoes(ambiente):
    r = ambiente.client.get("/v1/academico/professor/atribuicoes", headers=_h(ambiente, ambiente.tok_prof))
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["disciplina_nome"] == "Matemática"
    assert body[0]["turma_nome"] == "A"
    assert body[0]["serie_nome"] == "5º ano"
    assert body[0]["ano"] == 2026


def test_professor_sem_atribuicoes_vazio(ambiente):
    r = ambiente.client.get("/v1/academico/professor/atribuicoes", headers=_h(ambiente, ambiente.tok_prof2))
    assert r.status_code == 200
    assert r.json() == []


def test_professor_ve_matriculas_da_turma(ambiente):
    r = ambiente.client.get(f"/v1/academico/turmas/{ambiente.turma_id}/matriculas", headers=_h(ambiente, ambiente.tok_prof))
    assert r.status_code == 200
    nomes = {m["aluno_nome"] for m in r.json()}
    assert nomes == {"Aluno Um", "Aluno Dois"}


def test_professor_de_fora_nao_ve_matriculas_403(ambiente):
    r = ambiente.client.get(f"/v1/academico/turmas/{ambiente.turma_id}/matriculas", headers=_h(ambiente, ambiente.tok_prof2))
    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "sem_permissao_turma"


def test_secretaria_ve_matriculas_da_turma(ambiente):
    r = ambiente.client.get(f"/v1/academico/turmas/{ambiente.turma_id}/matriculas", headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_matriculas_turma_inexistente_404(ambiente):
    r = ambiente.client.get(f"/v1/academico/turmas/{uuid.uuid4()}/matriculas", headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 404
