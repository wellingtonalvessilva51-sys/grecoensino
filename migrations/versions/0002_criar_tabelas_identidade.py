"""criar tabelas de identidade (usuario, papel, usuario_papel, sessao)

Revision ID: 0002_identidade
Revises: 0001_tenant
Create Date: 2026-07-07

Cria as tabelas da Identidade e faz o seed do catálogo dos 7 papéis (§8) com
UUIDs estáveis, garantindo-os em todo ambiente após o upgrade.
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from src.modules.identidade.models import CATALOGO_PAPEIS

# identificadores usados pelo Alembic
revision: str = "0002_identidade"
down_revision: Union[str, None] = "0001_tenant"
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
    # papel (global)
    op.create_table(
        "papel",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_papel_codigo", "papel", ["codigo"], unique=True)

    # usuario (tenant-scoped)
    op.create_table(
        "usuario",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),
    )
    op.create_index("ix_usuario_tenant_id", "usuario", ["tenant_id"])
    op.create_index("ix_usuario_email", "usuario", ["email"])

    # usuario_papel (tenant-scoped)
    op.create_table(
        "usuario_papel",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("papel_id", sa.Uuid(), sa.ForeignKey("papel.id"), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "papel_id", name="uq_usuario_papel"),
    )
    op.create_index("ix_usuario_papel_tenant_id", "usuario_papel", ["tenant_id"])
    op.create_index("ix_usuario_papel_usuario_id", "usuario_papel", ["usuario_id"])
    op.create_index("ix_usuario_papel_papel_id", "usuario_papel", ["papel_id"])

    # sessao (tenant-scoped)
    op.create_table(
        "sessao",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("refresh_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessao_tenant_id", "sessao", ["tenant_id"])
    op.create_index("ix_sessao_usuario_id", "sessao", ["usuario_id"])
    op.create_index("ix_sessao_refresh_hash", "sessao", ["refresh_hash"])

    # seed do catálogo de papéis
    papel_tbl = sa.table(
        "papel",
        sa.column("id", sa.Uuid()),
        sa.column("codigo", sa.String()),
        sa.column("nome", sa.String()),
    )
    op.bulk_insert(
        papel_tbl,
        [
            {"id": uuid.UUID(pid), "codigo": codigo, "nome": nome}
            for pid, codigo, nome in CATALOGO_PAPEIS
        ],
    )


def downgrade() -> None:
    op.drop_table("sessao")
    op.drop_table("usuario_papel")
    op.drop_table("usuario")
    op.drop_index("ix_papel_codigo", table_name="papel")
    op.drop_table("papel")
