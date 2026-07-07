"""criar tabelas de pessoas (pessoa, endereco, contato, vinculo_responsavel_aluno)

Revision ID: 0003_pessoas
Revises: 0002_identidade
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# identificadores usados pelo Alembic
revision: str = "0003_pessoas"
down_revision: Union[str, None] = "0002_identidade"
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
        "pessoa",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=True),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=True),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "cpf", name="uq_pessoa_tenant_cpf"),
        sa.UniqueConstraint("tenant_id", "usuario_id", name="uq_pessoa_tenant_usuario"),
    )
    op.create_index("ix_pessoa_tenant_id", "pessoa", ["tenant_id"])
    op.create_index("ix_pessoa_usuario_id", "pessoa", ["usuario_id"])

    op.create_table(
        "endereco",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("pessoa_id", sa.Uuid(), sa.ForeignKey("pessoa.id"), nullable=False),
        sa.Column("logradouro", sa.String(length=200), nullable=False),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("complemento", sa.String(length=100), nullable=True),
        sa.Column("bairro", sa.String(length=100), nullable=True),
        sa.Column("cidade", sa.String(length=100), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("cep", sa.String(length=8), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_endereco_tenant_id", "endereco", ["tenant_id"])
    op.create_index("ix_endereco_pessoa_id", "endereco", ["pessoa_id"])

    op.create_table(
        "contato",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("pessoa_id", sa.Uuid(), sa.ForeignKey("pessoa.id"), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("valor", sa.String(length=255), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contato_tenant_id", "contato", ["tenant_id"])
    op.create_index("ix_contato_pessoa_id", "contato", ["pessoa_id"])

    op.create_table(
        "vinculo_responsavel_aluno",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("responsavel_id", sa.Uuid(), sa.ForeignKey("pessoa.id"), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), sa.ForeignKey("pessoa.id"), nullable=False),
        sa.Column("financeiro", sa.Boolean(), server_default=sa.false(), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("responsavel_id", "aluno_id", name="uq_vinculo_resp_aluno"),
    )
    op.create_index(
        "ix_vinculo_tenant_id", "vinculo_responsavel_aluno", ["tenant_id"]
    )
    op.create_index(
        "ix_vinculo_responsavel_id", "vinculo_responsavel_aluno", ["responsavel_id"]
    )
    op.create_index(
        "ix_vinculo_aluno_id", "vinculo_responsavel_aluno", ["aluno_id"]
    )


def downgrade() -> None:
    op.drop_table("vinculo_responsavel_aluno")
    op.drop_table("contato")
    op.drop_table("endereco")
    op.drop_table("pessoa")
