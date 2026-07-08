"""Rotas da Comunicação: recados.

Envio: RBAC secretaria/professor/admin_tenant. Leitura da caixa de entrada e
marcação de leitura: qualquer autenticado, restrito por ACL (própria pessoa +
dependentes).
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.comunicacao import service
from src.modules.comunicacao.schemas import (
    RecadoCreate,
    RecadoInboxItem,
    RecadoRead,
)
from src.shared.deps import Principal, get_current_user, require_papel

router = APIRouter(prefix="/comunicacao", tags=["comunicacao"])

_ENVIA = require_papel("secretaria", "professor", "admin_tenant")
_CRIADO = status.HTTP_201_CREATED


@router.post("/recados", response_model=RecadoRead, status_code=_CRIADO)
def criar_recado(
    dados: RecadoCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(_ENVIA),
):
    return service.criar_recado(db, principal, dados)


@router.get("/recados/enviados", response_model=list[RecadoRead])
def listar_enviados(
    db: Session = Depends(get_db),
    principal: Principal = Depends(_ENVIA),
):
    return service.listar_enviados(db, principal)


@router.get("/recados", response_model=list[RecadoInboxItem])
def listar_inbox(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    return service.listar_inbox(db, principal)


@router.post("/recados/destinatarios/{destinatario_id}/lido", response_model=RecadoInboxItem)
def marcar_lido(
    destinatario_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    rd = service.marcar_lido(db, principal, destinatario_id)
    # Recarrega como item de inbox para devolver o recado completo + lido_em.
    itens = [i for i in service.listar_inbox(db, principal) if i.destinatario_id == rd.id]
    return itens[0]
