"""Testes de isolamento multi-tenant (tenant confusion) — obrigatórios (§7).

Exercitam diretamente o mecanismo de reforço da camada de dados
(`tenant_guard`), usando SQLite em memória e um model descartável tenant-scoped.
"""

import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Importar registra os listeners globais do guard na Session.
import src.core.tenant_guard  # noqa: F401
from src.core.exceptions import AppError
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.shared.models import (
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class _BaseTeste(DeclarativeBase):
    """Base isolada para não poluir o metadata de produção."""


class ItemDemo(
    _BaseTeste,
    UUIDPrimaryKeyMixin,
    TenantMixin,
    TimestampMixin,
    SoftDeleteMixin,
):
    __tablename__ = "item_demo"

    descricao: Mapped[str] = mapped_column(String(100), nullable=False)


TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()


@contextmanager
def tenant(tenant_id: uuid.UUID):
    token = set_current_tenant(tenant_id)
    try:
        yield
    finally:
        reset_current_tenant(token)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    _BaseTeste.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as sessao:
        yield sessao


def test_carimba_tenant_do_contexto_no_insert(db):
    with tenant(TENANT_A):
        item = ItemDemo(descricao="a1")
        db.add(item)
        db.commit()
        db.refresh(item)
        assert item.tenant_id == TENANT_A


def test_isolamento_entre_tenants(db):
    with tenant(TENANT_A):
        db.add(ItemDemo(descricao="a1"))
        db.commit()
    with tenant(TENANT_B):
        db.add(ItemDemo(descricao="b1"))
        db.commit()

    with tenant(TENANT_A):
        descricoes = [i.descricao for i in db.scalars(select(ItemDemo)).all()]
    assert descricoes == ["a1"]  # jamais enxerga "b1"


def test_get_por_id_de_outro_tenant_retorna_none(db):
    with tenant(TENANT_B):
        item_b = ItemDemo(descricao="b1")
        db.add(item_b)
        db.commit()
        db.refresh(item_b)
        id_b = item_b.id

    db.expire_all()
    with tenant(TENANT_A):
        achado = db.scalars(select(ItemDemo).where(ItemDemo.id == id_b)).first()
    assert achado is None  # 404/None, nunca o dado do outro tenant


def test_consulta_sem_tenant_falha_fechado(db):
    with tenant(TENANT_A):
        db.add(ItemDemo(descricao="a1"))
        db.commit()

    db.expire_all()
    with pytest.raises(AppError):
        db.scalars(select(ItemDemo)).all()


def test_insert_com_tenant_divergente_e_bloqueado(db):
    with tenant(TENANT_A):
        db.add(ItemDemo(descricao="x", tenant_id=TENANT_B))
        with pytest.raises(AppError):
            db.commit()
