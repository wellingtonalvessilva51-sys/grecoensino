"""Models de Pessoas: pessoa, endereco, contato, vinculo_responsavel_aluno.

Todos tenant-scoped (herdam DomainBase → filtrados pelo guard do passo 2).
Pessoa é genérica: aluno/responsável vêm do vínculo; professor, do usuario_papel.
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models import DomainBase


class Pessoa(DomainBase):
    __tablename__ = "pessoa"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cpf", name="uq_pessoa_tenant_cpf"),
        UniqueConstraint("tenant_id", "usuario_id", name="uq_pessoa_tenant_usuario"),
    )

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Liga a pessoa a um login quando houver (aluno pequeno pode não ter).
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("usuario.id"), nullable=True, index=True
    )


class Endereco(DomainBase):
    __tablename__ = "endereco"

    pessoa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("pessoa.id"), nullable=False, index=True
    )
    logradouro: Mapped[str] = mapped_column(String(200), nullable=False)
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    complemento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cidade: Mapped[str] = mapped_column(String(100), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    cep: Mapped[str] = mapped_column(String(8), nullable=False)


class Contato(DomainBase):
    __tablename__ = "contato"

    pessoa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("pessoa.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # email/telefone/celular
    valor: Mapped[str] = mapped_column(String(255), nullable=False)


class VinculoResponsavelAluno(DomainBase):
    __tablename__ = "vinculo_responsavel_aluno"
    __table_args__ = (
        UniqueConstraint("responsavel_id", "aluno_id", name="uq_vinculo_resp_aluno"),
    )

    responsavel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("pessoa.id"), nullable=False, index=True
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("pessoa.id"), nullable=False, index=True
    )
    # Indica o responsável financeiro (quem recebe os títulos).
    financeiro: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
