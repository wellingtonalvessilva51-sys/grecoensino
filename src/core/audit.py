"""Trilha de auditoria (append-only) — CLAUDE.md §9.

Obrigatória em Notas e Financeiro: registrar quem mudou o quê, quando e em qual
tenant, na tabela `auditoria_log`. Nunca é atualizada nem apagada (append-only),
por isso o model tem só `created_at` — sem `updated_at`/`deleted_at`.

É tenant-scoped (`TenantMixin`): o guard do passo 2 carimba o `tenant_id` no
insert e filtra as leituras por tenant automaticamente.

LGPD: os snapshots `dados_antes`/`dados_depois` NÃO devem conter dado pessoal
sensível (CPF, endereço, dado financeiro em claro). Quem chama passa apenas os
campos relevantes da mudança (ex.: valor da nota, período).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.types import JSON

from src.shared.models import Base, TenantMixin, UUIDPrimaryKeyMixin

# JSON portável: JSONB no Postgres, JSON genérico no SQLite (testes).
JSONDict = JSON().with_variant(JSONB(), "postgresql")


class AuditoriaLog(Base, UUIDPrimaryKeyMixin, TenantMixin):
    """Registro imutável de uma mudança auditável (append-only)."""

    __tablename__ = "auditoria_log"

    # Quem fez a ação (usuário autenticado). Nullable: ações de sistema/seed.
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), nullable=True, index=True
    )
    # Ação realizada: "criar", "atualizar", "remover", ...
    acao: Mapped[str] = mapped_column(String(30), nullable=False)
    # Entidade afetada: "nota", "titulo", ...
    entidade: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), nullable=True, index=True
    )
    # Snapshots sem dado pessoal sensível (ver docstring do módulo).
    dados_antes: Mapped[dict | None] = mapped_column(JSONDict, nullable=True)
    dados_depois: Mapped[dict | None] = mapped_column(JSONDict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def registrar(
    db: Session,
    *,
    acao: str,
    entidade: str,
    entidade_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    dados_antes: dict | None = None,
    dados_depois: dict | None = None,
) -> AuditoriaLog:
    """Anexa um registro de auditoria à sessão atual (append-only).

    NÃO faz commit: participa da mesma transação da mudança auditada, para que a
    trilha e o dado alterado sejam gravados atomicamente. O `tenant_id` é
    carimbado pelo guard no flush. Quem chama commita.
    """
    log = AuditoriaLog(
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        usuario_id=usuario_id,
        dados_antes=dados_antes,
        dados_depois=dados_depois,
    )
    db.add(log)
    db.flush()
    return log


def listar(
    db: Session,
    *,
    entidade: str | None = None,
    entidade_id: uuid.UUID | None = None,
) -> list[AuditoriaLog]:
    """Lista a trilha do tenant atual (mais recente primeiro), opcionalmente filtrada."""
    stmt = select(AuditoriaLog)
    if entidade is not None:
        stmt = stmt.where(AuditoriaLog.entidade == entidade)
    if entidade_id is not None:
        stmt = stmt.where(AuditoriaLog.entidade_id == entidade_id)
    return list(db.scalars(stmt.order_by(AuditoriaLog.created_at.desc())).all())
