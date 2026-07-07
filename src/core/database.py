"""Engine, SessionLocal e a dependência get_db."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Dependência do FastAPI: abre uma sessão por request e fecha ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
