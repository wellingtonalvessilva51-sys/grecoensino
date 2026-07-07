"""Dependências comuns aos módulos: usuário atual (JWT) e RBAC por papel.

Concilia o tenant do transporte (passo 2) com o claim do JWT: se o transporte já
resolveu um tenant, o claim precisa bater; caso contrário, o claim é adotado como
autoritativo. Autorização de papel retorna 403 estruturado.
"""

import uuid
from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.exceptions import AppError
from src.core.security import decodificar_access_token
from src.core.tenancy import (
    get_current_tenant,
    reset_current_tenant,
    set_current_tenant,
)
from src.modules.identidade import service
from src.modules.identidade.models import Usuario


class Principal:
    """Usuário autenticado + seus códigos de papéis."""

    def __init__(self, usuario: Usuario, papeis: list[str]) -> None:
        self.usuario = usuario
        self.papeis = papeis


def _extrair_bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise AppError("nao_autenticado", "Autenticação obrigatória.", status_code=401)
    return auth[len("bearer ") :].strip()


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Iterator[Principal]:
    token = _extrair_bearer(request)
    claims = decodificar_access_token(token)
    try:
        tenant_do_token = uuid.UUID(claims["tenant_id"])
        usuario_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError):
        raise AppError("token_invalido", "Token malformado.", status_code=401)

    atual = get_current_tenant()
    ctx_token = None
    if atual is None:
        # Sem transporte: o claim do JWT é autoritativo.
        ctx_token = set_current_tenant(tenant_do_token)
    elif atual != tenant_do_token:
        raise AppError(
            "tenant_incompativel",
            "Token não pertence ao tenant desta requisição.",
            status_code=401,
        )

    try:
        usuario = service.buscar_usuario_por_id(db, usuario_id)
        if usuario is None:
            raise AppError("nao_autenticado", "Usuário inválido.", status_code=401)
        papeis = service.codigos_papeis(db, usuario.id)
        yield Principal(usuario=usuario, papeis=papeis)
    finally:
        if ctx_token is not None:
            reset_current_tenant(ctx_token)


def require_papel(*codigos: str):
    """Fábrica de dependência: exige ao menos um dos papéis; senão 403 estruturado."""

    def _dependencia(principal: Principal = Depends(get_current_user)) -> Principal:
        if not set(codigos).intersection(principal.papeis):
            raise AppError(
                "permissao_negada",
                "Papel sem permissão para esta ação.",
                status_code=403,
            )
        return principal

    return _dependencia
