"""Contratos (Pydantic v2) da Identidade.

Nota: e-mail como `str` (não `EmailStr`) para não exigir a dependência
`email-validator` no MVP; validação mais rígida entra se necessário.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    senha: str = Field(min_length=1, max_length=200)


class TokenResposta(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expira_em_min: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=255)
    senha: str = Field(min_length=8, max_length=200)
    papeis: list[str] = Field(default_factory=list)


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    ativo: bool
    papeis: list[str] = Field(default_factory=list)
