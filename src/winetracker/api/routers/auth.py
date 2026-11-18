from __future__ import annotations

from fastapi import APIRouter, status

from winetracker.api.deps import CurrentUser, SessionDep, SettingsDep
from winetracker.api.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from winetracker.services.auth import AuthService, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


def _out(pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, session: SessionDep, settings: SettingsDep) -> TokenResponse:
    svc = AuthService(session, settings)
    user = svc.register(body.email, body.password, body.display_name, body.locale)
    return _out(svc.issue_tokens(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: SessionDep, settings: SettingsDep) -> TokenResponse:
    svc = AuthService(session, settings)
    return _out(svc.issue_tokens(svc.authenticate(body.email, body.password)))


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, session: SessionDep, settings: SettingsDep) -> TokenResponse:
    return _out(AuthService(session, settings).refresh(body.refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, session: SessionDep, settings: SettingsDep) -> None:
    AuthService(session, settings).logout(body.refresh_token)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
