"""Serviço da Comunicação: recados institucionais.

Envio por secretaria/professor/admin (RBAC no router). Caixa de entrada por ACL:
cada usuário vê os recados destinados a si e aos seus dependentes (mesma regra
dos demais módulos, via pessoa própria + `dependentes_de`). Sem auditoria — §9
exige trilha só em Notas e Financeiro.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.exceptions import AppError
from src.modules.comunicacao.models import Recado, RecadoDestinatario
from src.modules.comunicacao.schemas import (
    RecadoCreate,
    RecadoInboxItem,
    RecadoRead,
)
from src.modules.pessoas import service as pessoas


def _ativos(model):
    return select(model).where(model.deleted_at.is_(None))


def _inbox_ids(db: Session, principal) -> list[uuid.UUID]:
    """Pessoas cujas mensagens este usuário pode ler: a própria + dependentes."""
    minha = pessoas.pessoa_do_usuario(db, principal.usuario.id)
    if minha is None:
        return []
    return [minha.id, *pessoas.dependentes_de(db, minha.id)]


def _total_destinatarios(db: Session, recado_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(
            _ativos(RecadoDestinatario)
            .where(RecadoDestinatario.recado_id == recado_id)
            .subquery()
        )
    ) or 0


# --- Envio ------------------------------------------------------------------
def criar_recado(db: Session, principal, dados: RecadoCreate) -> RecadoRead:
    destinatarios = list(dict.fromkeys(dados.destinatarios))  # remove duplicados
    for pessoa_id in destinatarios:
        if pessoas.obter_pessoa(db, pessoa_id) is None:
            raise AppError(
                "destinatario_inexistente",
                "Um dos destinatários não foi encontrado.",
                status_code=404,
            )

    recado = Recado(
        autor_usuario_id=principal.usuario.id,
        titulo=dados.titulo,
        mensagem=dados.mensagem,
    )
    db.add(recado)
    db.flush()

    for pessoa_id in destinatarios:
        db.add(RecadoDestinatario(recado_id=recado.id, pessoa_id=pessoa_id))

    db.commit()
    db.refresh(recado)
    return _montar_read(recado, len(destinatarios))


def _montar_read(recado: Recado, total: int) -> RecadoRead:
    return RecadoRead(
        id=recado.id,
        titulo=recado.titulo,
        mensagem=recado.mensagem,
        autor_usuario_id=recado.autor_usuario_id,
        created_at=recado.created_at,
        total_destinatarios=total,
    )


def listar_enviados(db: Session, principal) -> list[RecadoRead]:
    stmt = _ativos(Recado).where(Recado.autor_usuario_id == principal.usuario.id)
    recados = list(db.scalars(stmt.order_by(Recado.created_at.desc())).all())
    return [_montar_read(r, _total_destinatarios(db, r.id)) for r in recados]


# --- Caixa de entrada (destinatário) ----------------------------------------
def listar_inbox(db: Session, principal) -> list[RecadoInboxItem]:
    ids = _inbox_ids(db, principal)
    if not ids:
        return []
    stmt = (
        select(RecadoDestinatario, Recado)
        .join(Recado, Recado.id == RecadoDestinatario.recado_id)
        .where(
            RecadoDestinatario.pessoa_id.in_(ids),
            RecadoDestinatario.deleted_at.is_(None),
            Recado.deleted_at.is_(None),
        )
        .order_by(Recado.created_at.desc())
    )
    itens = []
    for rd, recado in db.execute(stmt).all():
        itens.append(
            RecadoInboxItem(
                destinatario_id=rd.id,
                recado_id=recado.id,
                titulo=recado.titulo,
                mensagem=recado.mensagem,
                created_at=recado.created_at,
                pessoa_id=rd.pessoa_id,
                lido_em=rd.lido_em,
            )
        )
    return itens


def marcar_lido(
    db: Session, principal, destinatario_id: uuid.UUID
) -> RecadoDestinatario:
    rd = db.scalars(
        _ativos(RecadoDestinatario).where(RecadoDestinatario.id == destinatario_id)
    ).first()
    if rd is None or rd.pessoa_id not in _inbox_ids(db, principal):
        raise AppError("recado_nao_encontrado", "Recado não encontrado.", status_code=404)
    if rd.lido_em is None:
        rd.lido_em = datetime.now(timezone.utc)
        db.commit()
        db.refresh(rd)
    return rd
