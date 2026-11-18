"""FastAPI application factory.

Run locally:  uvicorn winetracker.api.main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from winetracker import __version__
from winetracker.api.routers import auth
from winetracker.config import Settings, get_settings
from winetracker.db import get_engine
from winetracker.services.errors import DomainError

log = logging.getLogger("winetracker.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="WineTracker API",
        version=__version__,
        docs_url="/docs" if settings.env != "production" else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "Accept-Language"],
    )

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"code": exc.code, "detail": str(exc)})

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        """Liveness + DB readiness, used by the AWS load balancer health check."""
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "version": __version__}

    app.include_router(auth.router, prefix="/api/v1")
    return app


app = create_app()
