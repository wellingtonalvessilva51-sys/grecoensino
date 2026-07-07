"""Contratos (Pydantic v2) de Pessoas."""

import re
import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TipoContato = Literal["email", "telefone", "celular"]


class ContatoIn(BaseModel):
    tipo: TipoContato
    valor: str = Field(min_length=1, max_length=255)


class ContatoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tipo: str
    valor: str


class EnderecoIn(BaseModel):
    logradouro: str = Field(min_length=1, max_length=200)
    numero: str = Field(min_length=1, max_length=20)
    complemento: str | None = Field(default=None, max_length=100)
    bairro: str | None = Field(default=None, max_length=100)
    cidade: str = Field(min_length=1, max_length=100)
    uf: str = Field(min_length=2, max_length=2)
    cep: str = Field(min_length=8, max_length=9)

    @field_validator("cep")
    @classmethod
    def _cep_digitos(cls, v: str) -> str:
        digitos = re.sub(r"\D", "", v)
        if len(digitos) != 8:
            raise ValueError("CEP deve ter 8 dígitos.")
        return digitos

    @field_validator("uf")
    @classmethod
    def _uf_maiuscula(cls, v: str) -> str:
        return v.upper()


class EnderecoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    logradouro: str
    numero: str
    complemento: str | None
    bairro: str | None
    cidade: str
    uf: str
    cep: str


def _normalizar_cpf(v: str | None) -> str | None:
    if v is None:
        return None
    digitos = re.sub(r"\D", "", v)
    if len(digitos) != 11:
        raise ValueError("CPF deve ter 11 dígitos.")  # TODO: dígito verificador
    return digitos


class PessoaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    cpf: str | None = None
    data_nascimento: date | None = None
    usuario_id: uuid.UUID | None = None
    contatos: list[ContatoIn] = Field(default_factory=list)
    enderecos: list[EnderecoIn] = Field(default_factory=list)

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str | None) -> str | None:
        return _normalizar_cpf(v)


class PessoaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    cpf: str | None = None
    data_nascimento: date | None = None

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str | None) -> str | None:
        return _normalizar_cpf(v)


class PessoaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str
    cpf: str | None
    data_nascimento: date | None
    usuario_id: uuid.UUID | None
    contatos: list[ContatoRead] = Field(default_factory=list)
    enderecos: list[EnderecoRead] = Field(default_factory=list)


class VinculoCreate(BaseModel):
    responsavel_id: uuid.UUID
    aluno_id: uuid.UUID
    financeiro: bool = False


class VinculoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    responsavel_id: uuid.UUID
    aluno_id: uuid.UUID
    financeiro: bool
