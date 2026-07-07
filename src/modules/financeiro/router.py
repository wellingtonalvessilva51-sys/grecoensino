"""Rotas do Financeiro: título consolidado.

Escrita: RBAC secretaria/financeiro/admin_tenant. Leitura: ACL de aluno
(qualquer responsável vinculado vê os títulos do dependente).
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.exceptions import AppError
from src.modules.financeiro import service
from src.modules.financeiro.schemas import (
    PagamentoCreate,
    PagamentoRead,
    StatusTitulo,
    TituloCreate,
    TituloRead,
)
from src.shared.deps import Principal, get_current_user, require_papel

router = APIRouter(prefix="/financeiro", tags=["financeiro"])

_ESCRITA = require_papel("secretaria", "financeiro", "admin_tenant")
_CRIADO = status.HTTP_201_CREATED


def _titulo_visivel(db: Session, principal: Principal, titulo_id: uuid.UUID):
    """Carrega o título respeitando a ACL, senão 404 (não vaza existência)."""
    titulo = service.obter_titulo(db, titulo_id)
    if titulo is None or not service.pode_ver_titulo(db, principal, titulo):
        raise AppError("titulo_nao_encontrado", "Título não encontrado.", status_code=404)
    return titulo


@router.post("/titulos", response_model=TituloRead, status_code=_CRIADO)
def criar_titulo(
    dados: TituloCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(_ESCRITA),
):
    titulo = service.criar_titulo(db, principal, dados)
    return service.montar_read(db, titulo)


@router.get("/titulos", response_model=list[TituloRead])
def listar_titulos(
    status: StatusTitulo | None = None,
    aluno_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    titulos = service.listar_titulos(db, principal, status=status, aluno_id=aluno_id)
    return [service.montar_read(db, t) for t in titulos]


@router.get("/titulos/{titulo_id}", response_model=TituloRead)
def obter_titulo(
    titulo_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    titulo = _titulo_visivel(db, principal, titulo_id)
    return service.montar_read(db, titulo)


# --- Pagamento (parcial) ----------------------------------------------------
@router.post(
    "/titulos/{titulo_id}/pagamentos", response_model=PagamentoRead, status_code=_CRIADO
)
def registrar_pagamento(
    titulo_id: uuid.UUID,
    dados: PagamentoCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(_ESCRITA),
):
    return service.registrar_pagamento(db, principal, titulo_id, dados)


@router.get("/titulos/{titulo_id}/pagamentos", response_model=list[PagamentoRead])
def listar_pagamentos(
    titulo_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    _titulo_visivel(db, principal, titulo_id)
    return service.listar_pagamentos(db, titulo_id)
