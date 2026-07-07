"""criar tabela nota (nota por período e disciplina)

Revision ID: 0008_nota
Revises: 0007_frequencia
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# identificadores usados pelo Alembic
revision: str = "0008_nota"
down_revision: Union[str, None] = "0007_frequencia"
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
        "nota",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("matricula_id", sa.Uuid(), sa.ForeignKey("matricula.id"), nullable=False),
        sa.Column("disciplina_id", sa.Uuid(), sa.ForeignKey("disciplina.id"), nullable=False),
        sa.Column("periodo", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(4, 2), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "matricula_id", "disciplina_id", "periodo", name="uq_nota_matricula_disc_periodo"
        ),
    )
    op.create_index("ix_nota_tenant_id", "nota", ["tenant_id"])
    op.create_index("ix_nota_matricula_id", "nota", ["matricula_id"])
    op.create_index("ix_nota_disciplina_id", "nota", ["disciplina_id"])


def downgrade() -> None:
    op.drop_table("nota")
