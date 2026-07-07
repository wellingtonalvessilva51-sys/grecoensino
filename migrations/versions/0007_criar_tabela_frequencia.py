"""criar tabela frequencia (presença diária por dia letivo)

Revision ID: 0007_frequencia
Revises: 0006_auditoria_log
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# identificadores usados pelo Alembic
revision: str = "0007_frequencia"
down_revision: Union[str, None] = "0006_auditoria_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas_padrao() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "frequencia",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("matricula_id", sa.Uuid(), sa.ForeignKey("matricula.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("presente", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("justificada", sa.Boolean(), server_default=sa.false(), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("matricula_id", "data", name="uq_frequencia_matricula_data"),
    )
    op.create_index("ix_frequencia_tenant_id", "frequencia", ["tenant_id"])
    op.create_index("ix_frequencia_matricula_id", "frequencia", ["matricula_id"])


def downgrade() -> None:
    op.drop_table("frequencia")
