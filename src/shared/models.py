"""Base declarativa e mixins compartilhados por todos os models de domínio.

Convenção (CLAUDE.md §10): todo model de domínio tem
`id (UUID)`, `tenant_id`, `created_at`, `updated_at`, `deleted_at` (soft delete).

Use `DomainBase` para herdar tudo de uma vez, ou combine os mixins conforme
a necessidade.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa única do projeto (alvo do Alembic autogenerate)."""


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )


class TenantMixin:
    # Índice: todo índice composto de domínio deve começar por tenant_id.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        nullable=False,
        index=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class DomainBase(
    Base,
    UUIDPrimaryKeyMixin,
    TenantMixin,
    TimestampMixin,
    SoftDeleteMixin,
):
    """Base pronta para models de domínio: id + tenant_id + timestamps + soft delete."""

    __abstract__ = True
