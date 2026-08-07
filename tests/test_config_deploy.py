"""Testes de config relevantes ao deploy: DATABASE_URL, flags de tenant/seed e segredo."""

import pytest
from pydantic import ValidationError

from src.core.config import Settings

SEGREDO_FORTE = "x" * 48


def test_normaliza_database_url_do_railway():
    # Railway costuma expor postgres:// ou postgresql://; a app exige psycopg3.
    s = Settings(database_url="postgres://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"

    s2 = Settings(database_url="postgresql://u:p@host:5432/db")
    assert s2.database_url == "postgresql+psycopg://u:p@host:5432/db"

    # Já normalizada permanece.
    s3 = Settings(database_url="postgresql+psycopg://u:p@host/db")
    assert s3.database_url == "postgresql+psycopg://u:p@host/db"


def test_tenant_header_enabled():
    # Default: ligado só em development.
    assert Settings(environment="development", allow_tenant_header=None).tenant_header_enabled is True
    assert Settings(environment="production", allow_tenant_header=None, jwt_secret=SEGREDO_FORTE).tenant_header_enabled is False
    # Flag explícita vence (deploy demo em produção).
    assert Settings(environment="production", allow_tenant_header=True, jwt_secret=SEGREDO_FORTE).tenant_header_enabled is True
    assert Settings(environment="development", allow_tenant_header=False).tenant_header_enabled is False


def test_demo_seed_enabled():
    # Default: seed demo só em development — produção não recria login de vitrine.
    assert Settings(environment="development", allow_demo_seed=None).demo_seed_enabled is True
    assert Settings(environment="production", allow_demo_seed=None, jwt_secret=SEGREDO_FORTE).demo_seed_enabled is False
    # Flag explícita vence (deploy de vitrine assumido conscientemente).
    assert Settings(environment="production", allow_demo_seed=True, jwt_secret=SEGREDO_FORTE).demo_seed_enabled is True
    assert Settings(environment="development", allow_demo_seed=False).demo_seed_enabled is False


@pytest.mark.parametrize("segredo", ["troque-em-producao", "troque-por-um-segredo-forte", "", "CHANGEME"])
def test_producao_recusa_jwt_secret_de_placeholder(segredo):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret=segredo)


def test_placeholder_e_segredo_curto_nao_bloqueiam_fora_de_producao():
    # Dev/local segue rodando com o default — a exigência é só de produção.
    assert Settings(environment="development", jwt_secret="troque-em-producao").jwt_secret
    # Em produção, segredo curto passa (só vira aviso) — não derruba deploy existente.
    assert Settings(environment="production", jwt_secret="curto-mas-nao-placeholder").is_production
