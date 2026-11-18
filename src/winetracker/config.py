"""Application settings, loaded from environment variables (prefix ``WT_``) or ``.env``."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WT_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./winetracker-dev.sqlite3"
    db_echo: bool = False

    jwt_secret: SecretStr = SecretStr("dev-only-insecure-secret-change-me-0123456789")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    api_base_url: str = "http://127.0.0.1:8000"
    # Signs the web UI's HttpOnly session cookie (which holds the API tokens).
    web_session_secret: SecretStr = SecretStr("dev-only-insecure-web-secret-change-me-0123")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:8050"])

    default_locale: Literal["en", "pt-BR"] = "en"

    def validate_for_production(self) -> None:
        if self.env != "production":
            return
        for name in ("jwt_secret", "web_session_secret"):
            secret = getattr(self, name).get_secret_value()
            if secret.startswith("dev-only") or len(secret) < 32:
                raise RuntimeError(f"WT_{name.upper()} must be a strong secret in production")
        if self.database_url.startswith("sqlite"):
            raise RuntimeError("WT_DATABASE_URL must point to MySQL in production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_for_production()
    return settings
