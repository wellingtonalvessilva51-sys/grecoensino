"""criar tabela pagamento (pagamentos parciais do titulo)

Revision ID: 0010_pagamento
Revises: 0009_titulo
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# identificadores usados pelo Alembic
revision: str = "0010_pagamento"
down_revision: Union[str, None] = "0009_titulo"
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
        "pagamento",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("titulo_id", sa.Uuid(), sa.ForeignKey("titulo.id"), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("data_pagamento", sa.Date(), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pagamento_tenant_id", "pagamento", ["tenant_id"])
    op.create_index("ix_pagamento_titulo_id", "pagamento", ["titulo_id"])


def downgrade() -> None:
    op.drop_table("pagamento")
