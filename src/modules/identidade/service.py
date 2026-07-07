"""Serviço da Identidade: usuários, papéis, autenticação e sessões (refresh)."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.security import (
    gerar_refresh_token,
    hash_refresh,
    hash_senha,
    verificar_senha,
)
from src.modules.identidade.models import (
    CATALOGO_PAPEIS,
    Papel,
    Sessao,
    Usuario,
    UsuarioPapel,
)
from src.modules.identidade.schemas import UsuarioCreate


def _aware(dt: datetime) -> datetime:
    """Normaliza datetime para UTC-aware (SQLite devolve naive)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# --- Papéis -----------------------------------------------------------------
def garantir_papeis_catalogo(db: Session) -> None:
    """Idempotente: garante os 7 papéis do catálogo. Papel é global (sem tenant)."""
    existentes = {p.codigo for p in db.scalars(select(Papel)).all()}
    novos = [
        Papel(id=uuid.UUID(pid), codigo=codigo, nome=nome)
        for pid, codigo, nome in CATALOGO_PAPEIS
        if codigo not in existentes
    ]
    if novos:
        db.add_all(novos)
        db.commit()


def codigos_papeis(db: Session, usuario_id: uuid.UUID) -> list[str]:
    stmt = (
        select(Papel.codigo)
        .join(UsuarioPapel, UsuarioPapel.papel_id == Papel.id)
        .where(UsuarioPapel.usuario_id == usuario_id)
    )
    return list(db.scalars(stmt).all())


# --- Usuários ---------------------------------------------------------------
def criar_usuario(db: Session, dados: UsuarioCreate) -> Usuario:
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email.lower(),
        senha_hash=hash_senha(dados.senha),
        ativo=True,
    )
    db.add(usuario)
    db.flush()  # obtém o id; o tenant_id é carimbado no before_flush do guard

    papeis = db.scalars(select(Papel).where(Papel.codigo.in_(dados.papeis))).all()
    for papel in papeis:
        db.add(UsuarioPapel(usuario_id=usuario.id, papel_id=papel.id))

    db.commit()
    db.refresh(usuario)
    return usuario


def buscar_usuario_por_id(db: Session, usuario_id: uuid.UUID) -> Usuario | None:
    stmt = select(Usuario).where(
        Usuario.id == usuario_id,
        Usuario.ativo.is_(True),
        Usuario.deleted_at.is_(None),
    )
    return db.scalars(stmt).first()


def buscar_usuario_por_email(db: Session, email: str) -> Usuario | None:
    stmt = select(Usuario).where(
        Usuario.email == email.lower(),
        Usuario.deleted_at.is_(None),
    )
    return db.scalars(stmt).first()


def autenticar(db: Session, email: str, senha: str) -> Usuario | None:
    usuario = buscar_usuario_por_email(db, email)
    if usuario is None or not usuario.ativo:
        return None
    if not verificar_senha(senha, usuario.senha_hash):
        return None
    return usuario


# --- Sessões / refresh ------------------------------------------------------
def criar_sessao(db: Session, usuario_id: uuid.UUID) -> str:
    token, token_hash = gerar_refresh_token()
    expira = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_expire_days
    )
    db.add(Sessao(usuario_id=usuario_id, refresh_hash=token_hash, expira_em=expira))
    db.commit()
    return token


def _sessao_valida(db: Session, refresh_token: str) -> Sessao | None:
    stmt = select(Sessao).where(
        Sessao.refresh_hash == hash_refresh(refresh_token),
        Sessao.revogada_em.is_(None),
    )
    sessao = db.scalars(stmt).first()
    if sessao is None:
        return None
    if _aware(sessao.expira_em) <= datetime.now(timezone.utc):
        return None
    return sessao


def rotacionar_sessao(
    db: Session, refresh_token: str
) -> tuple[Usuario, str] | None:
    """Revoga a sessão do refresh e emite uma nova (rotação). None se inválido."""
    sessao = _sessao_valida(db, refresh_token)
    if sessao is None:
        return None
    usuario = buscar_usuario_por_id(db, sessao.usuario_id)
    if usuario is None:
        return None
    sessao.revogada_em = datetime.now(timezone.utc)
    novo_token = criar_sessao(db, usuario.id)  # faz commit (inclui a revogação)
    return usuario, novo_token


def revogar_sessao(db: Session, refresh_token: str) -> None:
    stmt = select(Sessao).where(
        Sessao.refresh_hash == hash_refresh(refresh_token),
        Sessao.revogada_em.is_(None),
    )
    sessao = db.scalars(stmt).first()
    if sessao is not None:
        sessao.revogada_em = datetime.now(timezone.utc)
        db.commit()


def revogar_todas(db: Session, usuario_id: uuid.UUID) -> None:
    stmt = select(Sessao).where(
        Sessao.usuario_id == usuario_id,
        Sessao.revogada_em.is_(None),
    )
    agora = datetime.now(timezone.utc)
    for sessao in db.scalars(stmt).all():
        sessao.revogada_em = agora
    db.commit()
