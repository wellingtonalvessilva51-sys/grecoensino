"""Contratos (Pydantic v2) do Acadêmico."""

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SituacaoAno = Literal["aberto", "fechado"]
SituacaoMatricula = Literal["ativa", "trancada", "transferida", "cancelada"]


class AnoLetivoCreate(BaseModel):
    ano: int = Field(ge=1900, le=3000)
    descricao: str | None = Field(default=None, max_length=100)
    situacao: SituacaoAno = "aberto"


class AnoLetivoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ano: int
    descricao: str | None
    situacao: str


class CursoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    codigo: str | None = Field(default=None, max_length=30)


class CursoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str
    codigo: str | None


class SerieCreate(BaseModel):
    curso_id: uuid.UUID
    nome: str = Field(min_length=1, max_length=100)
    ordem: int | None = None


class SerieRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    curso_id: uuid.UUID
    nome: str
    ordem: int | None


class DisciplinaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    codigo: str | None = Field(default=None, max_length=30)


class DisciplinaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str
    codigo: str | None


class TurmaCreate(BaseModel):
    serie_id: uuid.UUID
    ano_letivo_id: uuid.UUID
    nome: str = Field(min_length=1, max_length=50)


class TurmaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    serie_id: uuid.UUID
    ano_letivo_id: uuid.UUID
    nome: str


class AtribuicaoCreate(BaseModel):
    """Associa uma disciplina e um professor a uma turma (turma_disciplina_professor)."""

    disciplina_id: uuid.UUID
    professor_id: uuid.UUID


class AtribuicaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    turma_id: uuid.UUID
    disciplina_id: uuid.UUID
    professor_id: uuid.UUID


class MatriculaCreate(BaseModel):
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    situacao: SituacaoMatricula = "ativa"
    data_matricula: date | None = None


class MatriculaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    situacao: str
    data_matricula: date
