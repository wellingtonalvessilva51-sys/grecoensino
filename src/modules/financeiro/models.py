"""Models do Financeiro: titulo, titulo_item, pagamento.

Consolidação (§4): um único título por vencimento agrupa mensalidade + atividades
(ex.: "ETAPA, VÔLEI, ROBÓTICA, LIV") — modelado como `titulo` (1) → `titulo_item`
(N). A regra "um título por vencimento" é reforçada pela unique (aluno, competência).

Todos tenant-scoped (herdam DomainBase → filtrados pelo guard do passo 2). FK para
`pessoa.id` (aluno) referenciada por string, sem importar o módulo pessoas (§6).
"""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models import DomainBase


class Titulo(DomainBase):
    __tablename__ = "titulo"
    __table_args__ = (
        # §4: um único título por vencimento (competência) para o mesmo aluno.
        UniqueConstraint("aluno_id", "competencia", name="uq_titulo_aluno_competencia"),
    )

    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("pessoa.id"), nullable=False, index=True
    )
    competencia: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Calculado no servidor a partir dos itens (nunca confiar no cliente).
    valor_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # pendente | parcial | liquidado (derivado dos pagamentos).
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")


class TituloItem(DomainBase):
    __tablename__ = "titulo_item"

    titulo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("titulo.id"), nullable=False, index=True
    )
    descricao: Mapped[str] = mapped_column(String(100), nullable=False)  # ex.: "VÔLEI"
    valor: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


class Pagamento(DomainBase):
    __tablename__ = "pagamento"

    titulo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("titulo.id"), nullable=False, index=True
    )
    valor: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    data_pagamento: Mapped[date] = mapped_column(Date, nullable=False)
