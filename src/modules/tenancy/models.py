"""Model do tenant (instituição).

NÃO herda TenantMixin: é o registro dos próprios tenants, portanto não é
filtrado por tenant_id. Herda apenas id (UUID) + timestamps + soft delete.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenant"

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    subdominio: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        unique=True,
        index=True,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
