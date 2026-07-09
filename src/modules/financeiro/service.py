"""Serviço do Financeiro: título consolidado (titulo 1→N titulo_item).

Auditoria obrigatória (§9): criação de título grava em auditoria_log. ACL de
leitura reusa `pessoas.ids_visiveis` (qualquer responsável vinculado vê os
títulos do dependente; secretaria/financeiro/admin veem tudo).

Nota LGPD (§9): valores só são gravados na trilha de auditoria (registro
controlado) — nunca em log/stdout em texto claro.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core import audit
from src.core.exceptions import AppError
from src.modules.financeiro.models import Pagamento, Titulo, TituloItem
from src.modules.financeiro.schemas import (
    PagamentoCreate,
    TituloCreate,
    TituloItemCreate,
    TituloItemRead,
    TituloRead,
)
from src.modules.pessoas import service as pessoas

ZERO = Decimal("0.00")


def _total_pago(db: Session, titulo_id: uuid.UUID) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(Pagamento.valor), 0)).where(
            Pagamento.titulo_id == titulo_id, Pagamento.deleted_at.is_(None)
        )
    )
    return Decimal(total or 0)


def _status_por_pagamento(valor_total: Decimal, total_pago: Decimal) -> str:
    if total_pago <= ZERO:
        return "pendente"
    if total_pago < valor_total:
        return "parcial"
    return "liquidado"


def _ativos(model):
    return select(model).where(model.deleted_at.is_(None))


def _obter(db: Session, model, id_: uuid.UUID):
    return db.scalars(_ativos(model).where(model.id == id_)).first()


def _itens(db: Session, titulo_id: uuid.UUID) -> list[TituloItem]:
    stmt = _ativos(TituloItem).where(TituloItem.titulo_id == titulo_id)
    return list(db.scalars(stmt.order_by(TituloItem.descricao)).all())


# --- Leitura / montagem -----------------------------------------------------
def montar_read(db: Session, titulo: Titulo) -> TituloRead:
    valor_total = Decimal(titulo.valor_total)
    total_pago = _total_pago(db, titulo.id)
    aluno = pessoas.obter_pessoa(db, titulo.aluno_id)
    return TituloRead(
        id=titulo.id,
        aluno_id=titulo.aluno_id,
        aluno_nome=aluno.nome if aluno is not None else "",
        competencia=titulo.competencia,
        vencimento=titulo.vencimento,
        descricao=titulo.descricao,
        valor_total=valor_total,
        status=titulo.status,
        total_pago=total_pago,
        saldo=valor_total - total_pago,
        itens=[TituloItemRead.model_validate(i) for i in _itens(db, titulo.id)],
    )


# --- Criação ----------------------------------------------------------------
def criar_titulo(db: Session, principal, dados: TituloCreate) -> Titulo:
    if pessoas.obter_pessoa(db, dados.aluno_id) is None:
        raise AppError("aluno_inexistente", "Aluno não encontrado.", status_code=404)

    # §4: um único título por vencimento (competência) para o aluno.
    duplicado = db.scalars(
        _ativos(Titulo).where(
            Titulo.aluno_id == dados.aluno_id,
            Titulo.competencia == dados.competencia,
        )
    ).first()
    if duplicado is not None:
        raise AppError(
            "titulo_duplicado",
            "Já existe título para este aluno nesta competência.",
            status_code=409,
        )

    valor_total = sum((i.valor for i in dados.itens), ZERO)
    titulo = Titulo(
        aluno_id=dados.aluno_id,
        competencia=dados.competencia,
        vencimento=dados.vencimento,
        descricao=dados.descricao,
        valor_total=valor_total,
        status="pendente",
    )
    db.add(titulo)
    db.flush()  # id disponível para itens e auditoria

    for item in dados.itens:
        db.add(TituloItem(titulo_id=titulo.id, descricao=item.descricao, valor=item.valor))

    audit.registrar(
        db,
        acao="criar",
        entidade="titulo",
        entidade_id=titulo.id,
        usuario_id=principal.usuario.id,
        dados_depois={
            "aluno_id": str(dados.aluno_id),
            "competencia": dados.competencia,
            "vencimento": dados.vencimento.isoformat(),
            "valor_total": float(valor_total),
            "itens": [
                {"descricao": i.descricao, "valor": float(i.valor)} for i in dados.itens
            ],
        },
    )
    db.commit()
    db.refresh(titulo)
    return titulo


# --- Consultas + ACL --------------------------------------------------------
def obter_titulo(db: Session, titulo_id: uuid.UUID) -> Titulo | None:
    return _obter(db, Titulo, titulo_id)


def pode_ver_titulo(db: Session, principal, titulo: Titulo) -> bool:
    ids = pessoas.ids_visiveis(db, principal)  # None = privilegiado
    return ids is None or titulo.aluno_id in ids


def listar_titulos(
    db: Session,
    principal,
    status: str | None = None,
    aluno_id: uuid.UUID | None = None,
) -> list[Titulo]:
    ids = pessoas.ids_visiveis(db, principal)
    stmt = _ativos(Titulo)
    if ids is not None:
        if not ids:
            return []
        stmt = stmt.where(Titulo.aluno_id.in_(ids))
    if aluno_id is not None:
        stmt = stmt.where(Titulo.aluno_id == aluno_id)
    if status is not None:
        stmt = stmt.where(Titulo.status == status)
    return list(db.scalars(stmt.order_by(Titulo.vencimento)).all())


# --- Pagamento (parcial) ----------------------------------------------------
def registrar_pagamento(
    db: Session, principal, titulo_id: uuid.UUID, dados: PagamentoCreate
) -> Pagamento:
    titulo = _obter(db, Titulo, titulo_id)
    if titulo is None:
        raise AppError("titulo_nao_encontrado", "Título não encontrado.", status_code=404)

    valor_total = Decimal(titulo.valor_total)
    pago_atual = _total_pago(db, titulo_id)
    saldo = valor_total - pago_atual
    if dados.valor > saldo:
        raise AppError(
            "pagamento_excede_saldo",
            "Valor do pagamento excede o saldo devedor do título.",
            status_code=400,
        )

    pagamento = Pagamento(
        titulo_id=titulo_id,
        valor=dados.valor,
        data_pagamento=dados.data_pagamento or date.today(),
    )
    db.add(pagamento)
    db.flush()

    novo_total = pago_atual + dados.valor
    titulo.status = _status_por_pagamento(valor_total, novo_total)

    audit.registrar(
        db,
        acao="pagar",
        entidade="pagamento",
        entidade_id=pagamento.id,
        usuario_id=principal.usuario.id,
        dados_depois={
            "titulo_id": str(titulo_id),
            "valor": float(dados.valor),
            "total_pago": float(novo_total),
            "status": titulo.status,
        },
    )
    db.commit()
    db.refresh(pagamento)
    return pagamento


def listar_pagamentos(db: Session, titulo_id: uuid.UUID) -> list[Pagamento]:
    stmt = _ativos(Pagamento).where(Pagamento.titulo_id == titulo_id)
    return list(db.scalars(stmt.order_by(Pagamento.data_pagamento)).all())


# --- Geração automática (chamada por academico ao matricular, §6) ------------
def gerar_titulo_matricula(
    db: Session,
    principal,
    aluno_id: uuid.UUID,
    competencia: str,
    vencimento: date,
    valor: Decimal,
) -> Titulo | None:
    """Gera 1 título de mensalidade ao matricular. Idempotente por competência:
    se já houver título para (aluno, competência), não duplica (retorna None)."""
    existente = db.scalars(
        _ativos(Titulo).where(
            Titulo.aluno_id == aluno_id, Titulo.competencia == competencia
        )
    ).first()
    if existente is not None:
        return None
    return criar_titulo(
        db,
        principal,
        TituloCreate(
            aluno_id=aluno_id,
            competencia=competencia,
            vencimento=vencimento,
            descricao="Mensalidade (gerada na matrícula)",
            itens=[TituloItemCreate(descricao="MENSALIDADE", valor=valor)],
        ),
    )
