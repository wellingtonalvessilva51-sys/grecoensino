"""Contratos (Pydantic v2) do módulo tenancy."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    # Subdomínio: apenas minúsculas, dígitos e hífen (rótulo DNS válido).
    subdominio: str = Field(min_length=1, max_length=63, pattern=r"^[a-z0-9-]+$")


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    subdominio: str
    ativo: bool
