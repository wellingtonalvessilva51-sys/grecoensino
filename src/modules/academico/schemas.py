"""Contratos (Pydantic v2) do Acadêmico."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SituacaoAno = Literal["aberto", "fechado"]
SituacaoMatricula = Literal["ativa", "trancada", "transferida", "cancelada"]


class ConfigAcademicaUpdate(BaseModel):
    """Regras que a escola define. Todos os campos juntos (upsert)."""

    media_minima: Decimal = Field(ge=0, le=10)
    num_periodos: int = Field(ge=1, le=12)
    pesos_periodos: list[Decimal] = Field(min_length=1)
    frequencia_minima_percentual: Decimal = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _validar(self) -> "ConfigAcademicaUpdate":
        if len(self.pesos_periodos) != self.num_periodos:
            raise ValueError("pesos_periodos deve ter exatamente num_periodos itens.")
        if any(p <= 0 for p in self.pesos_periodos):
            raise ValueError("Todo peso de período deve ser maior que zero.")
        return self


class ConfigAcademicaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    media_minima: Decimal
    num_periodos: int
    pesos_periodos: list[Decimal]
    frequencia_minima_percentual: Decimal


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
    serie_nome: str
    ano_letivo_id: uuid.UUID
    ano: int
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


class CobrancaInicial(BaseModel):
    """Opcional: gera 1 título de mensalidade ao matricular (§6). Sem isto, a
    matrícula não gera título — a secretaria cria manualmente depois."""

    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    competencia: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # "YYYY-MM"
    vencimento: date


class MatriculaCreate(BaseModel):
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    situacao: SituacaoMatricula = "ativa"
    data_matricula: date | None = None
    cobranca_inicial: CobrancaInicial | None = None


class MatriculaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str
    turma_id: uuid.UUID
    situacao: str
    data_matricula: date


class NotaCreate(BaseModel):
    matricula_id: uuid.UUID
    disciplina_id: uuid.UUID
    periodo: int = Field(ge=1, le=12)  # limite fino validado contra a config
    valor: Decimal = Field(ge=0, le=10)


class NotaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    matricula_id: uuid.UUID
    disciplina_id: uuid.UUID
    periodo: int
    valor: Decimal


class FrequenciaCreate(BaseModel):
    matricula_id: uuid.UUID
    data: date
    presente: bool = True
    justificada: bool = False  # só relevante quando presente=False


class FrequenciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    matricula_id: uuid.UUID
    data: date
    presente: bool
    justificada: bool


class FrequenciaResumo(BaseModel):
    """Consolidado de frequência da matrícula, comparado ao mínimo da escola."""

    matricula_id: uuid.UUID
    dias_letivos: int  # dias com registro
    presencas: int
    faltas: int
    faltas_justificadas: int
    percentual: Decimal  # presencas / dias_letivos * 100
    frequencia_minima: Decimal  # da config da escola
    suficiente: bool  # percentual >= frequencia_minima


# Situação por disciplina e final. Sem recuperação nesta fase (decisão do MVP).
SituacaoDisciplina = Literal["cursando", "aprovado", "reprovado_nota"]
SituacaoFinal = Literal[
    "cursando", "aprovado", "reprovado_nota", "reprovado_frequencia"
]


class BoletimDisciplina(BaseModel):
    disciplina_id: uuid.UUID
    disciplina_nome: str
    media: Decimal  # média anual ponderada pelos pesos da config
    periodos_lancados: int
    completa: bool  # todos os períodos da config têm nota
    situacao: SituacaoDisciplina


class BoletimRead(BaseModel):
    """Boletim calculado on-the-fly (não editável direto) — junta as duas regras
    configuráveis da escola: média/situação e frequência mínima (§4)."""

    matricula_id: uuid.UUID
    aluno_nome: str
    media_minima: Decimal
    num_periodos: int
    disciplinas: list[BoletimDisciplina]
    frequencia: FrequenciaResumo
    situacao_final: SituacaoFinal
