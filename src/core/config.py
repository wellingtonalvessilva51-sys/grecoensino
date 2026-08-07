"""Configuração da aplicação via Pydantic Settings (lê variáveis de ambiente)."""

import logging

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Valores de placeholder que NUNCA podem valer como segredo em produção.
JWT_SECRETS_PROIBIDOS = {
    "",
    "troque-em-producao",
    "troque-por-um-segredo-forte",
    "changeme",
    "secret",
}
JWT_SECRET_TAMANHO_MINIMO = 32


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

    # Seed demo (`scripts.seed_dev`) cria usuários com senhas conhecidas. Se
    # None, liga só em development. Em produção exige ALLOW_DEMO_SEED=true
    # explícito — base com dado real nunca deve receber login demo.
    allow_demo_seed: bool | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def tenant_header_enabled(self) -> bool:
        if self.allow_tenant_header is not None:
            return self.allow_tenant_header
        return self.environment == "development"

    @property
    def demo_seed_enabled(self) -> bool:
        if self.allow_demo_seed is not None:
            return self.allow_demo_seed
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

    @model_validator(mode="after")
    def _exigir_segredo_de_producao(self) -> "Settings":
        """Em produção o app se recusa a subir com JWT_SECRET de placeholder.

        Segredo previsível = qualquer um forja um access token. Só bloqueia
        valores conhecidamente inseguros (não quebra deploy por tamanho); um
        segredo curto vira aviso no log.
        """
        if not self.is_production:
            return self
        if self.jwt_secret.strip().lower() in JWT_SECRETS_PROIBIDOS:
            raise ValueError(
                "JWT_SECRET está com valor de placeholder em produção. "
                'Gere um segredo forte: python -c "import secrets;print(secrets.token_urlsafe(48))"'
            )
        if len(self.jwt_secret) < JWT_SECRET_TAMANHO_MINIMO:
            logger.warning(
                "JWT_SECRET tem menos de %d caracteres — considere rotacionar por um mais longo.",
                JWT_SECRET_TAMANHO_MINIMO,
            )
        return self


settings = Settings()
