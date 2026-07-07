"""Primitivas de segurança: hash de senha, JWT (access) e refresh opaco.

Só criptografia/tokens aqui (camada de framework, sem models). As dependências
de autenticação/autorização do FastAPI ficam em `src/shared/deps.py`.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from src.core.config import settings
from src.core.exceptions import AppError

ALGORITMO = "HS256"


# --- Senha (bcrypt) ---------------------------------------------------------
def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        return False


# --- Access token (JWT HS256) ----------------------------------------------
def criar_access_token(
    *, usuario_id: uuid.UUID, tenant_id: uuid.UUID, papeis: list[str]
) -> str:
    agora = datetime.now(timezone.utc)
    claims = {
        "sub": str(usuario_id),
        "tenant_id": str(tenant_id),
        "papeis": list(papeis),
        "type": "access",
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.jwt_access_expire_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITMO)


def decodificar_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITMO])
    except JWTError:
        raise AppError("token_invalido", "Token inválido ou expirado.", status_code=401)
    if claims.get("type") != "access":
        raise AppError("token_invalido", "Token inválido.", status_code=401)
    return claims


# --- Refresh token (opaco, guardado como sha256) ----------------------------
def hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def gerar_refresh_token() -> tuple[str, str]:
    """Retorna (token_em_claro, sha256_do_token). Só o hash é persistido."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh(token)
