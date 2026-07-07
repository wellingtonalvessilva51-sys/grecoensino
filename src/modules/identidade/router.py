"""Rotas de autenticação: login, refresh, logout, logout-all, me."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import AppError
from src.core.security import criar_access_token
from src.core.tenancy import require_current_tenant
from src.modules.identidade import service
from src.modules.identidade.models import Usuario
from src.modules.identidade.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResposta,
    UsuarioRead,
)
from src.shared.deps import Principal, get_current_user

router = APIRouter(prefix="/auth", tags=["identidade"])


def _emitir(db: Session, usuario: Usuario) -> TokenResposta:
    papeis = service.codigos_papeis(db, usuario.id)
    access = criar_access_token(
        usuario_id=usuario.id, tenant_id=usuario.tenant_id, papeis=papeis
    )
    refresh = service.criar_sessao(db, usuario.id)
    return TokenResposta(
        access_token=access,
        refresh_token=refresh,
        expira_em_min=settings.jwt_access_expire_minutes,
    )


@router.post("/login", response_model=TokenResposta)
def login(dados: LoginRequest, db: Session = Depends(get_db)) -> TokenResposta:
    require_current_tenant()  # tenant vem do transporte (subdomínio / X-Tenant-ID)
    usuario = service.autenticar(db, dados.email, dados.senha)
    if usuario is None:
        # Mensagem genérica: não revela se o e-mail existe.
        raise AppError("credenciais_invalidas", "E-mail ou senha inválidos.", status_code=401)
    return _emitir(db, usuario)


@router.post("/refresh", response_model=TokenResposta)
def refresh(dados: RefreshRequest, db: Session = Depends(get_db)) -> TokenResposta:
    require_current_tenant()
    resultado = service.rotacionar_sessao(db, dados.refresh_token)
    if resultado is None:
        raise AppError("refresh_invalido", "Refresh token inválido ou expirado.", status_code=401)
    usuario, novo_refresh = resultado
    papeis = service.codigos_papeis(db, usuario.id)
    access = criar_access_token(
        usuario_id=usuario.id, tenant_id=usuario.tenant_id, papeis=papeis
    )
    return TokenResposta(
        access_token=access,
        refresh_token=novo_refresh,
        expira_em_min=settings.jwt_access_expire_minutes,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(dados: LogoutRequest, db: Session = Depends(get_db)) -> None:
    require_current_tenant()
    service.revogar_sessao(db, dados.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service.revogar_todas(db, principal.usuario.id)


@router.get("/me", response_model=UsuarioRead)
def me(principal: Principal = Depends(get_current_user)) -> UsuarioRead:
    u = principal.usuario
    return UsuarioRead(
        id=u.id, nome=u.nome, email=u.email, ativo=u.ativo, papeis=principal.papeis
    )
