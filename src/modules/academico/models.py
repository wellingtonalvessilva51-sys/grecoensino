"""Models do Acadêmico: estrutura curricular + matrícula.

Todos tenant-scoped (herdam DomainBase → filtrados pelo guard do passo 2).
FKs para `pessoa.id` (aluno/professor) referenciam por string, sem importar o
módulo pessoas — a validação de existência é feita via pessoas.service (§6).
"""

import uuid
from datetime import date

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models import DomainBase


class AnoLetivo(DomainBase):
    __tablename__ = "ano_letivo"
    __table_args__ = (UniqueConstraint("tenant_id", "ano", name="uq_ano_letivo_tenant_ano"),)

    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    situacao: Mapped[str] = mapped_column(String(20), nullable=False, default="aberto")


class Curso(DomainBase):
    __tablename__ = "curso"

    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(30), nullable=True)


class Serie(DomainBase):
    __tablename__ = "serie"
    __table_args__ = (UniqueConstraint("curso_id", "nome", name="uq_serie_curso_nome"),)

    curso_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("curso.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    ordem: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Disciplina(DomainBase):
    __tablename__ = "disciplina"

    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(30), nullable=True)


class Turma(DomainBase):
    __tablename__ = "turma"
    __table_args__ = (
        UniqueConstraint(
            "serie_id", "ano_letivo_id", "nome", name="uq_turma_serie_ano_nome"
        ),
    )

    serie_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("serie.id"), nullable=False, index=True
    )
    ano_letivo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("ano_letivo.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(50), nullable=False)


class TurmaDisciplinaProfessor(DomainBase):
    __tablename__ = "turma_disciplina_professor"
    __table_args__ = (
        UniqueConstraint("turma_id", "disciplina_id", name="uq_tdp_turma_disciplina"),
    )

    turma_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("turma.id"), nullable=False, index=True
    )
    disciplina_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("disciplina.id"), nullable=False, index=True
    )
    professor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("pessoa.id"), nullable=False, index=True
    )


class Matricula(DomainBase):
    __tablename__ = "matricula"
    __table_args__ = (
        UniqueConstraint("aluno_id", "turma_id", name="uq_matricula_aluno_turma"),
    )

    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("pessoa.id"), nullable=False, index=True
    )
    turma_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("turma.id"), nullable=False, index=True
    )
    situacao: Mapped[str] = mapped_column(String(20), nullable=False, default="ativa")
    data_matricula: Mapped[date] = mapped_column(nullable=False)
