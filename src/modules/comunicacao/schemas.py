"""Contratos (Pydantic v2) da Comunicação."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecadoCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    mensagem: str = Field(min_length=1)
    destinatarios: list[uuid.UUID] = Field(min_length=1)  # pessoa_id (aluno/responsável)


class RecadoRead(BaseModel):
    """Visão do autor: o recado enviado + quantos destinatários."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    titulo: str
    mensagem: str
    autor_usuario_id: uuid.UUID
    created_at: datetime
    total_destinatarios: int


class RecadoInboxItem(BaseModel):
    """Visão do destinatário (caixa de entrada): o recado + o próprio lido_em."""

    destinatario_id: uuid.UUID  # id do recado_destinatario (para marcar como lido)
    recado_id: uuid.UUID
    titulo: str
    mensagem: str
    created_at: datetime
    pessoa_id: uuid.UUID  # a quem este item se destina (o próprio ou um dependente)
    lido_em: datetime | None
