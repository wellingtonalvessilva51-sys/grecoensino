"""Ponto de entrada: cria o app FastAPI, registra handlers e routers.

API-first: uma API JSON única e versionada (`/v1`). Os routers de cada módulo
são registrados aqui conforme as fatias verticais forem implementadas.
"""

from fastapi import FastAPI

from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.tenancy import TenantResolverMiddleware, get_current_tenant

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
)

register_exception_handlers(app)

# Resolve o tenant da request (subdomínio / header de dev) e o injeta no contexto.
app.add_middleware(TenantResolverMiddleware)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Healthcheck simples (sem tocar no banco)."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


if settings.environment == "development":

    @app.get(f"{settings.api_v1_prefix}/_debug/tenant-atual", tags=["dev"])
    def _tenant_atual() -> dict[str, str | None]:
        """DEV-ONLY (temporário): mostra o tenant resolvido para a request.

        Sem tocar no banco e sem dado pessoal. Serve para conferir a resolução
        de tenant via `X-Tenant-ID` (dev) ou subdomínio do Host. Remover quando
        houver fatia de domínio real para exercitar o isolamento.
        """
        tenant_id = get_current_tenant()
        return {"tenant_id": str(tenant_id) if tenant_id is not None else None}


# Registro dos routers de módulo (fatias verticais) — descomentar conforme criados:
# from src.modules.identidade.router import router as identidade_router
# app.include_router(identidade_router, prefix=settings.api_v1_prefix)
