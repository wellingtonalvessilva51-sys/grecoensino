"""Ponto de entrada: cria o app FastAPI, registra handlers e routers.

API-first: uma API JSON única e versionada (`/v1`). Os routers de cada módulo
são registrados aqui conforme as fatias verticais forem implementadas.
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from src.core.config import settings
from src.core.exceptions import AppError, register_exception_handlers
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

# CORS por último → camada mais externa: trata o preflight (OPTIONS) do front
# antes da resolução de tenant. Origens vêm da config (Vite dev por padrão).
# X-Tenant-ID é liberado por allow_headers="*" (o front envia esse header em dev).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Routers dos módulos (fatias verticais).
from src.modules.academico.router import router as academico_router  # noqa: E402
from src.modules.comunicacao.router import router as comunicacao_router  # noqa: E402
from src.modules.financeiro.router import router as financeiro_router  # noqa: E402
from src.modules.identidade.router import router as identidade_router  # noqa: E402
from src.modules.pessoas.router import router as pessoas_router  # noqa: E402

app.include_router(identidade_router, prefix=settings.api_v1_prefix)
app.include_router(pessoas_router, prefix=settings.api_v1_prefix)
app.include_router(academico_router, prefix=settings.api_v1_prefix)
app.include_router(financeiro_router, prefix=settings.api_v1_prefix)
app.include_router(comunicacao_router, prefix=settings.api_v1_prefix)


# --- Front web (SPA) --------------------------------------------------------
# Deploy single-service: o FastAPI serve o build do front (web/dist). A config
# de runtime (tenant demo, base da API) é injetada no index.html como
# `window.__ENV__`, sem precisar rebuildar o front por ambiente.
_FRONT_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
# Prefixos que são da API/infra e nunca devem cair no fallback da SPA.
_RESERVADOS = ("v1", "docs", "redoc", "openapi.json", "health")


def _index_injetado() -> str:
    html = (_FRONT_DIST / "index.html").read_text(encoding="utf-8")
    env = {"tenantId": settings.demo_tenant_id or "", "apiBaseUrl": ""}
    script = f"<script>window.__ENV__={json.dumps(env)}</script>"
    return html.replace("</head>", f"{script}</head>", 1)


# Serve o front só fora de development (em dev usa-se o Vite em :5173; em testes
# não deve sombrear o 404 estruturado da API).
if _FRONT_DIST.is_dir() and settings.environment != "development":
    _INDEX_HTML = _index_injetado()

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    def servir_spa(full_path: str) -> FileResponse | HTMLResponse:
        if full_path.startswith(_RESERVADOS):
            raise AppError("nao_encontrado", "Recurso não encontrado.", status_code=404)
        # Arquivo estático existente (assets, ícone, manifest, sw...) — com guarda
        # contra path traversal.
        if full_path:
            alvo = (_FRONT_DIST / full_path).resolve()
            if alvo.is_file() and _FRONT_DIST.resolve() in alvo.parents:
                return FileResponse(alvo)
        # Qualquer outra rota → index.html (roteamento client-side).
        return HTMLResponse(_INDEX_HTML)
