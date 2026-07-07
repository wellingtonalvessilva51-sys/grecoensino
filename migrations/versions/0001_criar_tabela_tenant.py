"""criar tabela tenant

Revision ID: 0001_tenant
Revises:
Create Date: 2026-07-07

Primeira migration: registro dos tenants (instituições). Escrita à mão via
Alembic (não há PostgreSQL local para autogenerate online) — é o caminho
correto; o schema nunca é alterado manualmente no banco.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# identificadores usados pelo Alembic
revision: str = "0001_tenant"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("subdominio", sa.String(length=63), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
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
    )
    op.create_index(
        "ix_tenant_subdominio", "tenant", ["subdominio"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_subdominio", table_name="tenant")
    op.drop_table("tenant")
