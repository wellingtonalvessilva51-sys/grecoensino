"""criar tabela auditoria_log (trilha append-only — §9)

Revision ID: 0006_auditoria_log
Revises: 0005_config_academica
Create Date: 2026-07-07

Append-only: só `created_at` (sem `updated_at`/`deleted_at`). Tenant-scoped.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# identificadores usados pelo Alembic
revision: str = "0006_auditoria_log"
down_revision: Union[str, None] = "0005_config_academica"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auditoria_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
        sa.Column("acao", sa.String(length=30), nullable=False),
        sa.Column("entidade", sa.String(length=50), nullable=False),
        sa.Column("entidade_id", sa.Uuid(), nullable=True),
        sa.Column("dados_antes", JSONB(), nullable=True),
        sa.Column("dados_depois", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auditoria_log_tenant_id", "auditoria_log", ["tenant_id"])
    op.create_index("ix_auditoria_log_usuario_id", "auditoria_log", ["usuario_id"])
    op.create_index("ix_auditoria_log_entidade", "auditoria_log", ["entidade"])
    op.create_index("ix_auditoria_log_entidade_id", "auditoria_log", ["entidade_id"])


def downgrade() -> None:
    op.drop_table("auditoria_log")
