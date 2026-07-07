"""criar tabela config_academica (regras acadêmicas configuráveis por escola)

Revision ID: 0005_config_academica
Revises: 0004_academico
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# identificadores usados pelo Alembic
revision: str = "0005_config_academica"
down_revision: Union[str, None] = "0004_academico"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "config_academica",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("media_minima", sa.Numeric(4, 2), server_default="6.00", nullable=False),
        sa.Column("num_periodos", sa.Integer(), server_default="4", nullable=False),
        sa.Column("pesos_periodos", JSONB(), nullable=False),
        sa.Column(
            "frequencia_minima_percentual",
            sa.Numeric(5, 2),
            server_default="75.00",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_config_academica_tenant"),
    )
    op.create_index("ix_config_academica_tenant_id", "config_academica", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("config_academica")
