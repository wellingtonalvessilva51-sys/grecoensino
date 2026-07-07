"""Testes da fatia de Identidade: login/refresh/logout, RBAC (403) e tenant confusion."""

import uuid

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.core.tenant_guard  # noqa: F401  (registra o guard)
from src.core.database import get_db
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.main import app
from src.modules.identidade import service
from src.modules.identidade.schemas import UsuarioCreate
from src.modules.tenancy.models import Tenant
from src.shared.deps import require_papel
from src.shared.models import Base

# Rota-sonda só para exercitar o require_papel (403).
_SONDA = "/v1/_probe/admin-plataforma"
if not any(getattr(r, "path", None) == _SONDA for r in app.router.routes):

    @app.get(_SONDA)
    def _probe(_=Depends(require_papel("admin_plataforma"))):
        return {"ok": True}


ADMIN_EMAIL = "admin@escola-a.dev"
ADMIN_SENHA = "admin12345"


@pytest.fixture()
def ambiente():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    def _get_db_override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db_override

    with Session() as db:
        service.garantir_papeis_catalogo(db)
        tenant_a = Tenant(nome="Escola A", subdominio="escola-a")
        tenant_b = Tenant(nome="Escola B", subdominio="escola-b")
        db.add_all([tenant_a, tenant_b])
        db.commit()
        id_a, id_b = tenant_a.id, tenant_b.id

        token = set_current_tenant(id_a)
        try:
            service.criar_usuario(
                db,
                UsuarioCreate(
                    nome="Admin", email=ADMIN_EMAIL, senha=ADMIN_SENHA,
                    papeis=["admin_tenant"],
                ),
            )
        finally:
            reset_current_tenant(token)

    client = TestClient(app)
    try:
        yield client, id_a, id_b
    finally:
        app.dependency_overrides.clear()


def _login(client, tenant_id, email=ADMIN_EMAIL, senha=ADMIN_SENHA):
    return client.post(
        "/v1/auth/login",
        json={"email": email, "senha": senha},
        headers={"X-Tenant-ID": str(tenant_id)},
    )


def test_login_ok_retorna_tokens(ambiente):
    client, id_a, _ = ambiente
    r = _login(client, id_a)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["access_token"] and corpo["refresh_token"]
    assert corpo["token_type"] == "bearer"


def test_login_senha_errada_401_generico(ambiente):
    client, id_a, _ = ambiente
    r = _login(client, id_a, senha="errada")
    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "credenciais_invalidas"


def test_login_email_inexistente_401(ambiente):
    client, id_a, _ = ambiente
    r = _login(client, id_a, email="ninguem@escola-a.dev")
    assert r.status_code == 401


def test_me_sem_token_401(ambiente):
    client, id_a, _ = ambiente
    r = client.get("/v1/auth/me", headers={"X-Tenant-ID": str(id_a)})
    assert r.status_code == 401


def test_me_com_token_retorna_papeis(ambiente):
    client, id_a, _ = ambiente
    access = _login(client, id_a).json()["access_token"]
    r = client.get(
        "/v1/auth/me",
        headers={"X-Tenant-ID": str(id_a), "Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL
    assert "admin_tenant" in r.json()["papeis"]


def test_papel_insuficiente_403_estruturado(ambiente):
    client, id_a, _ = ambiente
    access = _login(client, id_a).json()["access_token"]
    r = client.get(
        "/v1/_probe/admin-plataforma",
        headers={"X-Tenant-ID": str(id_a), "Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "permissao_negada"


def test_refresh_rotaciona_e_invalida_antigo(ambiente):
    client, id_a, _ = ambiente
    r1 = _login(client, id_a).json()["refresh_token"]

    r = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": r1},
        headers={"X-Tenant-ID": str(id_a)},
    )
    assert r.status_code == 200
    r2 = r.json()["refresh_token"]
    assert r2 != r1

    # reusar o refresh antigo deve falhar (rotação)
    reuso = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": r1},
        headers={"X-Tenant-ID": str(id_a)},
    )
    assert reuso.status_code == 401


def test_logout_revoga_refresh(ambiente):
    client, id_a, _ = ambiente
    r1 = _login(client, id_a).json()["refresh_token"]

    saida = client.post(
        "/v1/auth/logout",
        json={"refresh_token": r1},
        headers={"X-Tenant-ID": str(id_a)},
    )
    assert saida.status_code == 204

    r = client.post(
        "/v1/auth/refresh",
        json={"refresh_token": r1},
        headers={"X-Tenant-ID": str(id_a)},
    )
    assert r.status_code == 401


def test_tenant_confusion_token_de_a_no_tenant_b(ambiente):
    client, id_a, id_b = ambiente
    access = _login(client, id_a).json()["access_token"]
    # token emitido para A, mas requisição chega com transporte do tenant B
    r = client.get(
        "/v1/auth/me",
        headers={"X-Tenant-ID": str(id_b), "Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "tenant_incompativel"
