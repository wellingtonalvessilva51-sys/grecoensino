"""Contratos (Pydantic v2) do Financeiro."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

StatusTitulo = Literal["pendente", "parcial", "liquidado"]

_COMPETENCIA = r"^\d{4}-(0[1-9]|1[0-2])$"  # "YYYY-MM"


class TituloItemCreate(BaseModel):
    descricao: str = Field(min_length=1, max_length=100)
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class TituloItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    descricao: str
    valor: Decimal


class TituloCreate(BaseModel):
    aluno_id: uuid.UUID
    competencia: str = Field(pattern=_COMPETENCIA)  # "YYYY-MM"
    vencimento: date
    descricao: str | None = Field(default=None, max_length=200)
    itens: list[TituloItemCreate] = Field(min_length=1)

    @field_validator("itens")
    @classmethod
    def _itens_nao_vazios(cls, v: list[TituloItemCreate]) -> list[TituloItemCreate]:
        if not v:
            raise ValueError("O título precisa de ao menos um item.")
        return v


class TituloRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    aluno_id: uuid.UUID
    competencia: str
    vencimento: date
    descricao: str | None
    valor_total: Decimal
    status: str
    total_pago: Decimal
    saldo: Decimal
    itens: list[TituloItemRead]


class PagamentoCreate(BaseModel):
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    data_pagamento: date | None = None  # default: hoje


class PagamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    titulo_id: uuid.UUID
    valor: Decimal
    data_pagamento: date
