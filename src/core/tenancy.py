"""Resolução do tenant atual (NÃO-NEGOCIÁVEL — ver CLAUDE.md §7).

Duas peças:
- um ContextVar com o tenant da request em andamento;
- um middleware ASGI que resolve o tenant no servidor e o injeta no contexto.

Ordem de resolução nesta fase (antes da Identidade/JWT do passo 3):
  1. header `X-Tenant-ID` — APENAS quando ENVIRONMENT=development (atalho de dev/testes);
  2. subdomínio do Host (`escola-a.<base_domain>` → subdomínio "escola-a").
Quando o JWT existir, o claim do token passa a ter precedência.

Nunca por parâmetro de URL manipulável pelo cliente. O reforço de que toda query
filtra por tenant fica em `tenant_guard.py` (fail-closed).
"""

import uuid
from contextvars import ContextVar, Token

from starlette.types import ASGIApp, Receive, Scope, Send

from src.core.config import settings
from src.core.exceptions import AppError

_current_tenant: ContextVar[uuid.UUID | None] = ContextVar(
    "current_tenant", default=None
)


def set_current_tenant(tenant_id: uuid.UUID | None) -> Token:
    return _current_tenant.set(tenant_id)


def reset_current_tenant(token: Token) -> None:
    _current_tenant.reset(token)


def get_current_tenant() -> uuid.UUID | None:
    return _current_tenant.get()


def require_current_tenant() -> uuid.UUID:
    """Retorna o tenant atual ou falha fechado (nunca segue sem tenant)."""
    tenant_id = _current_tenant.get()
    if tenant_id is None:
        raise AppError(
            codigo="tenant_ausente",
            mensagem="Operação sobre recurso multi-tenant sem tenant resolvido.",
            status_code=500,
        )
    return tenant_id


def _extrair_subdominio(host: str) -> str | None:
    """Extrai o rótulo de subdomínio de um Host, dado o base_domain configurado."""
    host = host.split(":")[0].strip().lower()
    sufixo = "." + settings.base_domain.lower()
    if not host.endswith(sufixo):
        return None
    rotulo = host[: -len(sufixo)]
    # Só um nível de subdomínio e nada de "www".
    if not rotulo or "." in rotulo or rotulo == "www":
        return None
    return rotulo


class TenantResolverMiddleware:
    """Middleware ASGI puro: resolve o tenant e o deixa no ContextVar.

    ASGI puro (em vez de BaseHTTPMiddleware) para garantir que o ContextVar
    setado aqui propague para o endpoint na mesma task async.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        tenant_id = self._resolver(headers)

        token = set_current_tenant(tenant_id) if tenant_id is not None else None
        try:
            await self.app(scope, receive, send)
        finally:
            if token is not None:
                reset_current_tenant(token)

    def _resolver(self, headers: dict[str, str]) -> uuid.UUID | None:
        # 1. Atalho de desenvolvimento.
        if settings.environment == "development":
            bruto = headers.get("x-tenant-id")
            if bruto:
                try:
                    return uuid.UUID(bruto)
                except ValueError:
                    return None

        # 2. Subdomínio do Host → lookup no registro de tenants.
        subdominio = _extrair_subdominio(headers.get("host", ""))
        if subdominio:
            # Import tardio evita ciclo de import (database → tenant_guard → tenancy).
            from src.core.database import SessionLocal
            from src.modules.tenancy import service

            with SessionLocal() as db:
                tenant = service.buscar_por_subdominio(db, subdominio)
                if tenant is not None:
                    return tenant.id

        return None
