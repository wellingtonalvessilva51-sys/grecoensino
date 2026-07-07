"""Serviço do Financeiro: título consolidado (titulo 1→N titulo_item).

Auditoria obrigatória (§9): criação de título grava em auditoria_log. ACL de
leitura reusa `pessoas.ids_visiveis` (qualquer responsável vinculado vê os
títulos do dependente; secretaria/financeiro/admin veem tudo).

Nota LGPD (§9): valores só são gravados na trilha de auditoria (registro
controlado) — nunca em log/stdout em texto claro.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core import audit
from src.core.exceptions import AppError
from src.modules.financeiro.models import Titulo, TituloItem
from src.modules.financeiro.schemas import TituloCreate, TituloItemRead, TituloRead
from src.modules.pessoas import service as pessoas

ZERO = Decimal("0.00")


def _ativos(model):
    return select(model).where(model.deleted_at.is_(None))


def _obter(db: Session, model, id_: uuid.UUID):
    return db.scalars(_ativos(model).where(model.id == id_)).first()


def _itens(db: Session, titulo_id: uuid.UUID) -> list[TituloItem]:
    stmt = _ativos(TituloItem).where(TituloItem.titulo_id == titulo_id)
    return list(db.scalars(stmt.order_by(TituloItem.descricao)).all())


# --- Leitura / montagem -----------------------------------------------------
def montar_read(db: Session, titulo: Titulo, total_pago: Decimal = ZERO) -> TituloRead:
    valor_total = Decimal(titulo.valor_total)
    return TituloRead(
        id=titulo.id,
        aluno_id=titulo.aluno_id,
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
