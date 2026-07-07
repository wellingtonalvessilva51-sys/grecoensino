"""Models da Identidade: usuario, papel, usuario_papel, sessao.

- Usuario/UsuarioPapel/Sessao são tenant-scoped (herdam DomainBase → o guard do
  passo 2 os filtra por tenant automaticamente).
- Papel é global (catálogo fixo dos 7 papéis do §8), portanto sem TenantMixin.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models import (
    Base,
    DomainBase,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

# Catálogo fixo dos papéis (§8). UUIDs estáveis para o mesmo papel em todo
# ambiente — usados tanto pela migration quanto pelo seed/serviço.
CATALOGO_PAPEIS: list[tuple[str, str, str]] = [
    ("00000000-0000-0000-0000-0000000000a1", "aluno", "Aluno"),
    ("00000000-0000-0000-0000-0000000000a2", "responsavel", "Responsável"),
    ("00000000-0000-0000-0000-0000000000a3", "professor", "Professor"),
    ("00000000-0000-0000-0000-0000000000a4", "secretaria", "Secretaria"),
    ("00000000-0000-0000-0000-0000000000a5", "financeiro", "Financeiro"),
    ("00000000-0000-0000-0000-0000000000a6", "admin_tenant", "Admin da Instituição"),
    ("00000000-0000-0000-0000-0000000000a7", "admin_plataforma", "Admin da Plataforma"),
]


class Usuario(DomainBase):
    __tablename__ = "usuario"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),
    )

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Papel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "papel"

    codigo: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)


class UsuarioPapel(DomainBase):
    __tablename__ = "usuario_papel"
    __table_args__ = (
        UniqueConstraint("usuario_id", "papel_id", name="uq_usuario_papel"),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("usuario.id"), nullable=False, index=True
    )
    papel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("papel.id"), nullable=False, index=True
    )


class Sessao(DomainBase):
    __tablename__ = "sessao"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("usuario.id"), nullable=False, index=True
    )
    # sha256 hex do refresh token (opaco). Nunca guardamos o token em claro.
    refresh_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
