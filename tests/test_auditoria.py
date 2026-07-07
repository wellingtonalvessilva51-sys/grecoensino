"""Testes da trilha de auditoria (core/audit): registro, isolamento e append-only."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.core.tenant_guard  # noqa: F401  (registra os listeners do guard)
from src.core import audit
from src.core.audit import AuditoriaLog
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.shared.models import Base


@pytest.fixture()
def db_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    yield Session


def test_registrar_carimba_tenant_e_snapshots(db_factory):
    tenant = uuid.uuid4()
    entidade_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    tok = set_current_tenant(tenant)
    try:
        with db_factory() as db:
            log = audit.registrar(
                db,
                acao="atualizar",
                entidade="nota",
                entidade_id=entidade_id,
                usuario_id=usuario_id,
                dados_antes={"valor": 7.0, "periodo": 1},
                dados_depois={"valor": 8.5, "periodo": 1},
            )
            db.commit()

            assert log.tenant_id == tenant  # carimbado pelo guard
            assert log.dados_antes == {"valor": 7.0, "periodo": 1}
            assert log.dados_depois == {"valor": 8.5, "periodo": 1}
            assert log.entidade_id == entidade_id
            assert log.usuario_id == usuario_id
    finally:
        reset_current_tenant(tok)


def test_listar_filtra_por_tenant(db_factory):
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()

    tok = set_current_tenant(tenant_a)
    try:
        with db_factory() as db:
            audit.registrar(db, acao="criar", entidade="nota")
            db.commit()
    finally:
        reset_current_tenant(tok)

    tok = set_current_tenant(tenant_b)
    try:
        with db_factory() as db:
            audit.registrar(db, acao="criar", entidade="titulo")
            db.commit()
            # tenant B só enxerga a própria trilha
            trilha = audit.listar(db)
            assert len(trilha) == 1
            assert trilha[0].entidade == "titulo"
    finally:
        reset_current_tenant(tok)


def test_listar_filtra_por_entidade(db_factory):
    tenant = uuid.uuid4()
    alvo = uuid.uuid4()
    tok = set_current_tenant(tenant)
    try:
        with db_factory() as db:
            audit.registrar(db, acao="criar", entidade="nota", entidade_id=alvo)
            audit.registrar(db, acao="criar", entidade="titulo")
            db.commit()

            so_notas = audit.listar(db, entidade="nota")
            assert len(so_notas) == 1
            assert so_notas[0].entidade_id == alvo

            por_id = audit.listar(db, entidade="nota", entidade_id=alvo)
            assert len(por_id) == 1
    finally:
        reset_current_tenant(tok)


def test_append_only_sem_updated_at_nem_deleted_at():
    # Contrato append-only: o model não expõe updated_at nem deleted_at.
    colunas = set(AuditoriaLog.__table__.columns.keys())
    assert "created_at" in colunas
    assert "updated_at" not in colunas
    assert "deleted_at" not in colunas
