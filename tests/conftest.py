"""Test fixtures: an isolated in-memory database per test and an API client bound to it.

Integration tests against MySQL: set WT_TEST_DATABASE_URL to a disposable MySQL database.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from winetracker.config import Settings
from winetracker.db import build_engine, get_session
from winetracker.models import Base


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", jwt_secret="test-secret-" + "x" * 40)  # type: ignore[arg-type]


@pytest.fixture
def engine() -> Iterator[Engine]:
    url = os.environ.get("WT_TEST_DATABASE_URL", "sqlite://")
    if url == "sqlite://":
        from sqlalchemy import create_engine, event

        eng = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(eng, "connect")
        def _fk(conn, _):  # type: ignore[no-untyped-def]
            conn.execute("PRAGMA foreign_keys=ON")
    else:
        eng = build_engine(url)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    with factory() as s:
        yield s


@pytest.fixture
def client(engine: Engine, settings: Settings) -> Iterator[TestClient]:
    from winetracker.api.main import create_app
    from winetracker.config import get_settings

    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    def _session() -> Iterator[Session]:
        s = factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app = create_app(settings)
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c
