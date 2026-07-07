"""Testes da Configuração Acadêmica: defaults, edição, validação, RBAC e isolamento."""

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
from src.modules.identidade import service as identidade
from src.modules.identidade.schemas import UsuarioCreate
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
            u_admin = identidade.criar_usuario(db, UsuarioCreate(nome="Admin", email="admin@a.dev", senha="senha1234", papeis=["admin_tenant"]))
            u_resp = identidade.criar_usuario(db, UsuarioCreate(nome="Resp", email="resp@a.dev", senha="senha1234", papeis=["responsavel"]))
        finally:
            reset_current_tenant(tok)

        tok_b = set_current_tenant(id_b)
        try:
            u_admin_b = identidade.criar_usuario(db, UsuarioCreate(nome="AdminB", email="admin@b.dev", senha="senha1234", papeis=["admin_tenant"]))
        finally:
            reset_current_tenant(tok_b)

    env = SimpleNamespace(
        client=TestClient(app),
        id_a=id_a,
        id_b=id_b,
        tok_admin=criar_access_token(usuario_id=u_admin.id, tenant_id=id_a, papeis=["admin_tenant"]),
        tok_resp=criar_access_token(usuario_id=u_resp.id, tenant_id=id_a, papeis=["responsavel"]),
        tok_admin_b=criar_access_token(usuario_id=u_admin_b.id, tenant_id=id_b, papeis=["admin_tenant"]),
    )
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


def _h(tenant_id, token):
    return {"X-Tenant-ID": str(tenant_id), "Authorization": f"Bearer {token}"}


def test_config_nasce_com_defaults(ambiente):
    r = ambiente.client.get("/v1/academico/config", headers=_h(ambiente.id_a, ambiente.tok_admin))
    assert r.status_code == 200
    body = r.json()
    assert float(body["media_minima"]) == 6.0
    assert body["num_periodos"] == 4
    assert [float(p) for p in body["pesos_periodos"]] == [1, 1, 1, 1]
    assert float(body["frequencia_minima_percentual"]) == 75.0


def test_admin_edita_config(ambiente):
    r = ambiente.client.put(
        "/v1/academico/config",
        json={
            "media_minima": 7.0,
            "num_periodos": 3,
            "pesos_periodos": [1, 1, 2],
            "frequencia_minima_percentual": 80,
        },
        headers=_h(ambiente.id_a, ambiente.tok_admin),
    )
    assert r.status_code == 200
    assert float(r.json()["media_minima"]) == 7.0
    assert r.json()["num_periodos"] == 3

    # persistiu
    r2 = ambiente.client.get("/v1/academico/config", headers=_h(ambiente.id_a, ambiente.tok_admin))
    assert [float(p) for p in r2.json()["pesos_periodos"]] == [1, 1, 2]


def test_pesos_incompativeis_com_num_periodos_422(ambiente):
    r = ambiente.client.put(
        "/v1/academico/config",
        json={
            "media_minima": 6.0,
            "num_periodos": 4,
            "pesos_periodos": [1, 1, 1],  # só 3 pesos para 4 períodos
            "frequencia_minima_percentual": 75,
        },
        headers=_h(ambiente.id_a, ambiente.tok_admin),
    )
    assert r.status_code == 422


def test_peso_nao_positivo_422(ambiente):
    r = ambiente.client.put(
        "/v1/academico/config",
        json={
            "media_minima": 6.0,
            "num_periodos": 2,
            "pesos_periodos": [1, 0],
            "frequencia_minima_percentual": 75,
        },
        headers=_h(ambiente.id_a, ambiente.tok_admin),
    )
    assert r.status_code == 422


def test_responsavel_nao_edita_config_403(ambiente):
    r = ambiente.client.put(
        "/v1/academico/config",
        json={
            "media_minima": 5.0,
            "num_periodos": 4,
            "pesos_periodos": [1, 1, 1, 1],
            "frequencia_minima_percentual": 75,
        },
        headers=_h(ambiente.id_a, ambiente.tok_resp),
    )
    assert r.status_code == 403


def test_responsavel_pode_ler_config(ambiente):
    r = ambiente.client.get("/v1/academico/config", headers=_h(ambiente.id_a, ambiente.tok_resp))
    assert r.status_code == 200


def test_isolamento_config_por_tenant(ambiente):
    # Escola A muda para média 9; escola B deve continuar no default 6.
    ambiente.client.put(
        "/v1/academico/config",
        json={
            "media_minima": 9.0,
            "num_periodos": 4,
            "pesos_periodos": [1, 1, 1, 1],
            "frequencia_minima_percentual": 75,
        },
        headers=_h(ambiente.id_a, ambiente.tok_admin),
    )
    r = ambiente.client.get("/v1/academico/config", headers=_h(ambiente.id_b, ambiente.tok_admin_b))
    assert float(r.json()["media_minima"]) == 6.0
