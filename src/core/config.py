"""Configuração da aplicação via Pydantic Settings (lê variáveis de ambiente)."""

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

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Banco (PostgreSQL via psycopg3)
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/gestao_educacional"
    )

    # Auth (usado a partir da fatia de Identidade)
    jwt_secret: str = "troque-em-producao"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 30

    # IA (Anthropic)
    anthropic_api_key: str | None = None


settings = Settings()
