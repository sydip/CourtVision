from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return f"postgresql+psycopg://{database_url.removeprefix('postgresql://')}"
    return database_url


def create_database_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    resolved_url = normalize_database_url(database_url or settings.database_url)
    connect_args: dict[str, object] = {}
    if resolved_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(resolved_url, connect_args=connect_args, pool_pre_ping=True)


_engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=create_database_engine(database_url),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db_session() -> Generator[Session, None, None]:
    SessionLocal.configure(bind=get_engine())
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope(session_factory: sessionmaker[Session] = SessionLocal) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
