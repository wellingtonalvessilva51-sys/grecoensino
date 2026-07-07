"""Rotas de Pessoas: CRUD (RBAC de escrita) + leitura filtrada por ACL (§8)."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.exceptions import AppError
from src.modules.pessoas import service
from src.modules.pessoas.schemas import (
    PessoaCreate,
    PessoaRead,
    PessoaUpdate,
    VinculoCreate,
    VinculoRead,
)
from src.shared.deps import Principal, get_current_user, require_papel

router = APIRouter(prefix="/pessoas", tags=["pessoas"])

# Papéis que podem escrever no cadastro de pessoas/vínculos.
_ESCRITA = require_papel("secretaria", "admin_tenant")


@router.post("", response_model=PessoaRead, status_code=status.HTTP_201_CREATED)
def criar_pessoa(
    dados: PessoaCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(_ESCRITA),
) -> PessoaRead:
    pessoa = service.criar_pessoa(db, dados)
    return service.montar_read(db, pessoa)


@router.get("", response_model=list[PessoaRead])
def listar_pessoas(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
) -> list[PessoaRead]:
    ids = service.ids_visiveis(db, principal)
    pessoas = service.listar_pessoas(db, ids)
    return [service.montar_read(db, p) for p in pessoas]


@router.get("/{pessoa_id}", response_model=PessoaRead)
def obter_pessoa(
    pessoa_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
) -> PessoaRead:
    pessoa = service.obter_pessoa(db, pessoa_id)
    # 404 tanto para inexistente quanto para não-autorizado (não vaza existência).
    if pessoa is None or not service.pode_ver_pessoa(db, principal, pessoa_id):
        raise AppError("pessoa_nao_encontrada", "Pessoa não encontrada.", status_code=404)
    return service.montar_read(db, pessoa)


@router.patch("/{pessoa_id}", response_model=PessoaRead)
def atualizar_pessoa(
    pessoa_id: uuid.UUID,
    dados: PessoaUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(_ESCRITA),
) -> PessoaRead:
    pessoa = service.obter_pessoa(db, pessoa_id)
    if pessoa is None:
        raise AppError("pessoa_nao_encontrada", "Pessoa não encontrada.", status_code=404)
    pessoa = service.atualizar_pessoa(db, pessoa, dados)
    return service.montar_read(db, pessoa)


@router.delete("/{pessoa_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_pessoa(
    pessoa_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(_ESCRITA),
) -> None:
    pessoa = service.obter_pessoa(db, pessoa_id)
    if pessoa is None:
        raise AppError("pessoa_nao_encontrada", "Pessoa não encontrada.", status_code=404)
    service.remover_pessoa(db, pessoa)


@router.post("/vinculos", response_model=VinculoRead, status_code=status.HTTP_201_CREATED)
def criar_vinculo(
    dados: VinculoCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(_ESCRITA),
) -> VinculoRead:
    vinculo = service.criar_vinculo(db, dados)
    return VinculoRead.model_validate(vinculo)
