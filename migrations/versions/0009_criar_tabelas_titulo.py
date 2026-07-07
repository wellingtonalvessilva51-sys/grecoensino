"""criar tabelas do financeiro (titulo, titulo_item)

Revision ID: 0009_titulo
Revises: 0008_nota
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# identificadores usados pelo Alembic
revision: str = "0009_titulo"
down_revision: Union[str, None] = "0008_nota"
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
        "titulo",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), sa.ForeignKey("pessoa.id"), nullable=False),
        sa.Column("competencia", sa.String(length=7), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=True),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pendente", nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("aluno_id", "competencia", name="uq_titulo_aluno_competencia"),
    )
    op.create_index("ix_titulo_tenant_id", "titulo", ["tenant_id"])
    op.create_index("ix_titulo_aluno_id", "titulo", ["aluno_id"])

    op.create_table(
        "titulo_item",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("titulo_id", sa.Uuid(), sa.ForeignKey("titulo.id"), nullable=False),
        sa.Column("descricao", sa.String(length=100), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_titulo_item_tenant_id", "titulo_item", ["tenant_id"])
    op.create_index("ix_titulo_item_titulo_id", "titulo_item", ["titulo_id"])


def downgrade() -> None:
    op.drop_table("titulo_item")
    op.drop_table("titulo")
