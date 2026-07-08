"""criar tabelas da comunicacao (recado, recado_destinatario)

Revision ID: 0011_recado
Revises: 0010_pagamento
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# identificadores usados pelo Alembic
revision: str = "0011_recado"
down_revision: Union[str, None] = "0010_pagamento"
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
        "recado",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("autor_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recado_tenant_id", "recado", ["tenant_id"])
    op.create_index("ix_recado_autor_usuario_id", "recado", ["autor_usuario_id"])

    op.create_table(
        "recado_destinatario",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("recado_id", sa.Uuid(), sa.ForeignKey("recado.id"), nullable=False),
        sa.Column("pessoa_id", sa.Uuid(), sa.ForeignKey("pessoa.id"), nullable=False),
        sa.Column("lido_em", sa.DateTime(timezone=True), nullable=True),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recado_id", "pessoa_id", name="uq_recado_destinatario"),
    )
    op.create_index("ix_recado_destinatario_tenant_id", "recado_destinatario", ["tenant_id"])
    op.create_index("ix_recado_destinatario_recado_id", "recado_destinatario", ["recado_id"])
    op.create_index("ix_recado_destinatario_pessoa_id", "recado_destinatario", ["pessoa_id"])


def downgrade() -> None:
    op.drop_table("recado_destinatario")
    op.drop_table("recado")
