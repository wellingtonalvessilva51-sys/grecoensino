"""criar tabelas do academico (ano_letivo, curso, serie, disciplina, turma,
turma_disciplina_professor, matricula)

Revision ID: 0004_academico
Revises: 0003_pessoas
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# identificadores usados pelo Alembic
revision: str = "0004_academico"
down_revision: Union[str, None] = "0003_pessoas"
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
        "ano_letivo",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.String(length=100), nullable=True),
        sa.Column("situacao", sa.String(length=20), server_default="aberto", nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "ano", name="uq_ano_letivo_tenant_ano"),
    )
    op.create_index("ix_ano_letivo_tenant_id", "ano_letivo", ["tenant_id"])

    op.create_table(
        "curso",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("codigo", sa.String(length=30), nullable=True),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_curso_tenant_id", "curso", ["tenant_id"])

    op.create_table(
        "serie",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("curso_id", sa.Uuid(), sa.ForeignKey("curso.id"), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=True),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("curso_id", "nome", name="uq_serie_curso_nome"),
    )
    op.create_index("ix_serie_tenant_id", "serie", ["tenant_id"])
    op.create_index("ix_serie_curso_id", "serie", ["curso_id"])

    op.create_table(
        "disciplina",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("codigo", sa.String(length=30), nullable=True),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_disciplina_tenant_id", "disciplina", ["tenant_id"])

    op.create_table(
        "turma",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("serie_id", sa.Uuid(), sa.ForeignKey("serie.id"), nullable=False),
        sa.Column("ano_letivo_id", sa.Uuid(), sa.ForeignKey("ano_letivo.id"), nullable=False),
        sa.Column("nome", sa.String(length=50), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("serie_id", "ano_letivo_id", "nome", name="uq_turma_serie_ano_nome"),
    )
    op.create_index("ix_turma_tenant_id", "turma", ["tenant_id"])
    op.create_index("ix_turma_serie_id", "turma", ["serie_id"])
    op.create_index("ix_turma_ano_letivo_id", "turma", ["ano_letivo_id"])

    op.create_table(
        "turma_disciplina_professor",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("turma_id", sa.Uuid(), sa.ForeignKey("turma.id"), nullable=False),
        sa.Column("disciplina_id", sa.Uuid(), sa.ForeignKey("disciplina.id"), nullable=False),
        sa.Column("professor_id", sa.Uuid(), sa.ForeignKey("pessoa.id"), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("turma_id", "disciplina_id", name="uq_tdp_turma_disciplina"),
    )
    op.create_index("ix_tdp_tenant_id", "turma_disciplina_professor", ["tenant_id"])
    op.create_index("ix_tdp_turma_id", "turma_disciplina_professor", ["turma_id"])
    op.create_index("ix_tdp_disciplina_id", "turma_disciplina_professor", ["disciplina_id"])
    op.create_index("ix_tdp_professor_id", "turma_disciplina_professor", ["professor_id"])

    op.create_table(
        "matricula",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), sa.ForeignKey("pessoa.id"), nullable=False),
        sa.Column("turma_id", sa.Uuid(), sa.ForeignKey("turma.id"), nullable=False),
        sa.Column("situacao", sa.String(length=20), server_default="ativa", nullable=False),
        sa.Column("data_matricula", sa.Date(), nullable=False),
        *_colunas_padrao(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("aluno_id", "turma_id", name="uq_matricula_aluno_turma"),
    )
    op.create_index("ix_matricula_tenant_id", "matricula", ["tenant_id"])
    op.create_index("ix_matricula_aluno_id", "matricula", ["aluno_id"])
    op.create_index("ix_matricula_turma_id", "matricula", ["turma_id"])


def downgrade() -> None:
    op.drop_table("matricula")
    op.drop_table("turma_disciplina_professor")
    op.drop_table("turma")
    op.drop_table("disciplina")
    op.drop_table("serie")
    op.drop_table("curso")
    op.drop_table("ano_letivo")
