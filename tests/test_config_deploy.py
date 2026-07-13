"""Testes de config relevantes ao deploy: normalização da DATABASE_URL e flag do header."""

from src.core.config import Settings


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
    assert Settings(environment="production", allow_tenant_header=None).tenant_header_enabled is False
    # Flag explícita vence (deploy demo em produção).
    assert Settings(environment="production", allow_tenant_header=True).tenant_header_enabled is True
    assert Settings(environment="development", allow_tenant_header=False).tenant_header_enabled is False
