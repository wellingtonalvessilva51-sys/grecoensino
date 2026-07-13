"""Configuração da aplicação via Pydantic Settings (lê variáveis de ambiente)."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Aplicação
    app_name: str = "Gestão Educacional"
    environment: str = "development"
    api_v1_prefix: str = "/v1"

    # Domínio base usado para extrair o subdomínio do Host (multi-tenancy).
    # Ex.: base_domain="localhost" → "escola-a.localhost" resolve tenant "escola-a".
    base_domain: str = "localhost"

    # CORS: origens do front permitidas (separadas por vírgula). Default = Vite dev.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Habilita o atalho de tenant via header X-Tenant-ID. Se None, liga só em
    # development. Em produção com deploy single-tenant (demo), pode ligar
    # explicitamente com ALLOW_TENANT_HEADER=true.
    allow_tenant_header: bool | None = None

    # Deploy demo single-tenant: id do tenant injetado no front (window.__ENV__)
    # e usado pelo seed para criar a escola com id estável.
    demo_tenant_id: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def tenant_header_enabled(self) -> bool:
        if self.allow_tenant_header is not None:
            return self.allow_tenant_header
        return self.environment == "development"

    # Banco (PostgreSQL via psycopg3)
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/gestao_educacional"
    )

    @field_validator("database_url")
    @classmethod
    def _normalizar_database_url(cls, v: str) -> str:
        """Aceita a DATABASE_URL do Railway (postgres:// / postgresql://) e força
        o driver psycopg3 exigido pela aplicação."""
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    # Auth (usado a partir da fatia de Identidade)
    jwt_secret: str = "troque-em-producao"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 30

    # IA (Anthropic)
    anthropic_api_key: str | None = None


settings = Settings()
