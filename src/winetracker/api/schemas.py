"""Request/response contracts. Kept separate from ORM models on purpose."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from winetracker.domain.enums import Locale


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    locale: Locale = Locale.EN


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    locale: Locale
    avatar_url: str | None = None


class ErrorOut(BaseModel):
    code: str
    detail: str
