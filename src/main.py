"""Ponto de entrada: cria o app FastAPI, registra handlers e routers.

API-first: uma API JSON única e versionada (`/v1`). Os routers de cada módulo
são registrados aqui conforme as fatias verticais forem implementadas.
"""

from fastapi import FastAPI

from src.core.config import settings
from src.core.exceptions import register_exception_handlers

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
)

register_exception_handlers(app)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Healthcheck simples (sem tocar no banco)."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


# Registro dos routers de módulo (fatias verticais) — descomentar conforme criados:
# from src.modules.identidade.router import router as identidade_router
# app.include_router(identidade_router, prefix=settings.api_v1_prefix)
