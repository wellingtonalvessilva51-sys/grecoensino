"""Testes do gancho automático: matrícula com cobrança inicial gera o título (§6)."""

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
            p_dep = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Dependente"))

            ano = academico.criar_ano_letivo(db, AnoLetivoCreate(ano=2026))
            curso = academico.criar_curso(db, CursoCreate(nome="EF"))
            serie = academico.criar_serie(db, SerieCreate(curso_id=curso.id, nome="1º ano", ordem=1))
            turma = academico.criar_turma(db, TurmaCreate(serie_id=serie.id, ano_letivo_id=ano.id, nome="A"))
            turma2 = academico.criar_turma(db, TurmaCreate(serie_id=serie.id, ano_letivo_id=ano.id, nome="B"))
        finally:
            reset_current_tenant(tok)

    env = SimpleNamespace(
        client=TestClient(app),
        id_a=id_a,
        tok_sec=criar_access_token(usuario_id=u_sec.id, tenant_id=id_a, papeis=["secretaria"]),
        aluno_id=p_dep.id,
        turma_id=turma.id,
        turma2_id=turma2.id,
    )
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


def _h(env):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {env.tok_sec}"}


def _matricular(env, turma_id, cobranca=None):
    payload = {"aluno_id": str(env.aluno_id), "turma_id": str(turma_id)}
    if cobranca is not None:
        payload["cobranca_inicial"] = cobranca
    return env.client.post("/v1/academico/matriculas", json=payload, headers=_h(env))


def _titulos(env):
    return env.client.get(
        f"/v1/financeiro/titulos?aluno_id={env.aluno_id}", headers=_h(env)
    ).json()


def test_matricula_com_cobranca_gera_titulo(ambiente):
    r = _matricular(
        ambiente,
        ambiente.turma_id,
        cobranca={"valor": 450, "competencia": "2026-03", "vencimento": "2026-03-10"},
    )
    assert r.status_code == 201
    titulos = _titulos(ambiente)
    assert len(titulos) == 1
    t = titulos[0]
    assert float(t["valor_total"]) == 450.0
    assert t["competencia"] == "2026-03"
    assert t["status"] == "pendente"
    assert t["itens"][0]["descricao"] == "MENSALIDADE"


def test_matricula_sem_cobranca_nao_gera_titulo(ambiente):
    r = _matricular(ambiente, ambiente.turma_id)
    assert r.status_code == 201
    assert _titulos(ambiente) == []


def test_gancho_idempotente_nao_duplica_competencia(ambiente):
    # Já existe título para 2026-05 (criado manualmente).
    ambiente.client.post(
        "/v1/financeiro/titulos",
        json={
            "aluno_id": str(ambiente.aluno_id),
            "competencia": "2026-05",
            "vencimento": "2026-05-10",
            "itens": [{"descricao": "MENSALIDADE", "valor": 500}],
        },
        headers=_h(ambiente),
    )
    # Matricular com cobrança na MESMA competência não deve duplicar nem falhar.
    r = _matricular(
        ambiente,
        ambiente.turma_id,
        cobranca={"valor": 450, "competencia": "2026-05", "vencimento": "2026-05-10"},
    )
    assert r.status_code == 201
    titulos = [t for t in _titulos(ambiente) if t["competencia"] == "2026-05"]
    assert len(titulos) == 1
    assert float(titulos[0]["valor_total"]) == 500.0  # manteve o título original
