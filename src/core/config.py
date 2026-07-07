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

    # Banco (PostgreSQL via psycopg3)
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/gestao_educacional"
    )

    # Auth (usado a partir da fatia de Identidade)
    jwt_secret: str = "troque-em-producao"
    jwt_access_expire_minutes: int = 15

    # IA (Anthropic)
    anthropic_api_key: str | None = None


settings = Settings()
