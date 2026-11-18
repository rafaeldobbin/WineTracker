"""Database engine and session management."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from winetracker.config import get_settings


def build_engine(url: str, echo: bool = False) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, echo=echo, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    # MySQL: recycle connections before RDS/MySQL wait_timeout drops them.
    return create_engine(url, echo=echo, pool_pre_ping=True, pool_recycle=1800, pool_size=10)


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
    return build_engine(s.database_url, s.db_echo)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed on success."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
