"""Models da Comunicação: recado + recado_destinatario.

Recado institucional simples: um autor (usuário) envia um recado a N destinatários
(pessoas — alunos/responsáveis). Cada destinatário tem seu próprio `lido_em`.

Tenant-scoped (herdam DomainBase → filtrados pelo guard do passo 2). FKs para
`usuario.id`/`pessoa.id` por string, sem importar os outros módulos (§6).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models import DomainBase


class Recado(DomainBase):
    __tablename__ = "recado"

    autor_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("usuario.id"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)


class RecadoDestinatario(DomainBase):
    __tablename__ = "recado_destinatario"
    __table_args__ = (
        UniqueConstraint("recado_id", "pessoa_id", name="uq_recado_destinatario"),
    )

    recado_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("recado.id"), nullable=False, index=True
    )
    pessoa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("pessoa.id"), nullable=False, index=True
    )
    lido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
