"""Serviço de Pessoas: CRUD, vínculos e autorização de recurso (ACL §8)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.exceptions import AppError
from src.modules.pessoas.models import (
    Contato,
    Endereco,
    Pessoa,
    VinculoResponsavelAluno,
)
from src.modules.pessoas.schemas import (
    ContatoRead,
    EnderecoRead,
    PessoaCreate,
    PessoaRead,
    PessoaUpdate,
    VinculoCreate,
)

# Papéis que enxergam qualquer pessoa dentro do tenant.
PAPEIS_PRIVILEGIADOS = {"admin_tenant", "secretaria", "financeiro", "admin_plataforma"}


# --- Leitura auxiliar -------------------------------------------------------
def _contatos(db: Session, pessoa_id: uuid.UUID) -> list[Contato]:
    stmt = select(Contato).where(
        Contato.pessoa_id == pessoa_id, Contato.deleted_at.is_(None)
    )
    return list(db.scalars(stmt).all())


def _enderecos(db: Session, pessoa_id: uuid.UUID) -> list[Endereco]:
    stmt = select(Endereco).where(
        Endereco.pessoa_id == pessoa_id, Endereco.deleted_at.is_(None)
    )
    return list(db.scalars(stmt).all())


def montar_read(db: Session, pessoa: Pessoa) -> PessoaRead:
    return PessoaRead(
        id=pessoa.id,
        nome=pessoa.nome,
        cpf=pessoa.cpf,
        data_nascimento=pessoa.data_nascimento,
        usuario_id=pessoa.usuario_id,
        contatos=[ContatoRead.model_validate(c) for c in _contatos(db, pessoa.id)],
        enderecos=[EnderecoRead.model_validate(e) for e in _enderecos(db, pessoa.id)],
    )


# --- CRUD -------------------------------------------------------------------
def criar_pessoa(db: Session, dados: PessoaCreate) -> Pessoa:
    pessoa = Pessoa(
        nome=dados.nome,
        cpf=dados.cpf,
        data_nascimento=dados.data_nascimento,
        usuario_id=dados.usuario_id,
    )
    db.add(pessoa)
    db.flush()  # id disponível; tenant carimbado no before_flush do guard

    for c in dados.contatos:
        db.add(Contato(pessoa_id=pessoa.id, tipo=c.tipo, valor=c.valor))
    for e in dados.enderecos:
        db.add(
            Endereco(
                pessoa_id=pessoa.id,
                logradouro=e.logradouro,
                numero=e.numero,
                complemento=e.complemento,
                bairro=e.bairro,
                cidade=e.cidade,
                uf=e.uf,
                cep=e.cep,
            )
        )

    db.commit()
    db.refresh(pessoa)
    return pessoa


def obter_pessoa(db: Session, pessoa_id: uuid.UUID) -> Pessoa | None:
    stmt = select(Pessoa).where(
        Pessoa.id == pessoa_id, Pessoa.deleted_at.is_(None)
    )
    return db.scalars(stmt).first()


def listar_pessoas(
    db: Session, ids: list[uuid.UUID] | None = None
) -> list[Pessoa]:
    stmt = select(Pessoa).where(Pessoa.deleted_at.is_(None))
    if ids is not None:
        if not ids:
            return []
        stmt = stmt.where(Pessoa.id.in_(ids))
    return list(db.scalars(stmt.order_by(Pessoa.nome)).all())


def atualizar_pessoa(db: Session, pessoa: Pessoa, dados: PessoaUpdate) -> Pessoa:
    campos = dados.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(pessoa, campo, valor)
    db.commit()
    db.refresh(pessoa)
    return pessoa


def remover_pessoa(db: Session, pessoa: Pessoa) -> None:
    pessoa.deleted_at = datetime.now(timezone.utc)
    db.commit()


# --- Vínculos ---------------------------------------------------------------
def criar_vinculo(db: Session, dados: VinculoCreate) -> VinculoResponsavelAluno:
    if dados.responsavel_id == dados.aluno_id:
        raise AppError(
            "vinculo_invalido", "Responsável e aluno não podem ser a mesma pessoa.", status_code=400
        )
    if obter_pessoa(db, dados.responsavel_id) is None:
        raise AppError("responsavel_inexistente", "Responsável não encontrado.", status_code=404)
    if obter_pessoa(db, dados.aluno_id) is None:
        raise AppError("aluno_inexistente", "Aluno não encontrado.", status_code=404)

    vinculo = VinculoResponsavelAluno(
        responsavel_id=dados.responsavel_id,
        aluno_id=dados.aluno_id,
        financeiro=dados.financeiro,
    )
    db.add(vinculo)
    db.commit()
    db.refresh(vinculo)
    return vinculo


def dependentes_de(db: Session, responsavel_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = select(VinculoResponsavelAluno.aluno_id).where(
        VinculoResponsavelAluno.responsavel_id == responsavel_id,
        VinculoResponsavelAluno.deleted_at.is_(None),
    )
    return list(db.scalars(stmt).all())


def pessoa_do_usuario(db: Session, usuario_id: uuid.UUID) -> Pessoa | None:
    stmt = select(Pessoa).where(
        Pessoa.usuario_id == usuario_id, Pessoa.deleted_at.is_(None)
    )
    return db.scalars(stmt).first()


# --- Autorização de recurso (ACL) ------------------------------------------
def ids_visiveis(db: Session, principal) -> list[uuid.UUID] | None:
    """None = vê todas as pessoas do tenant; senão a lista de ids permitidos."""
    if PAPEIS_PRIVILEGIADOS.intersection(principal.papeis):
        return None
    minha = pessoa_do_usuario(db, principal.usuario.id)
    if minha is None:
        return []
    return [minha.id, *dependentes_de(db, minha.id)]


def pode_ver_pessoa(db: Session, principal, pessoa_id: uuid.UUID) -> bool:
    ids = ids_visiveis(db, principal)
    return ids is None or pessoa_id in ids
