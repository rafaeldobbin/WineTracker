"""Thin HTTP client the Dash UI uses to talk to the API (the same API a mobile app uses)."""

from __future__ import annotations

import contextlib
from typing import Any

import httpx
from flask import session

from winetracker.config import get_settings
from winetracker.web import session as web_session


class ApiError(Exception):
    def __init__(self, code: str, status: int, fields: list[str] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.fields = fields or []


def _client() -> httpx.Client:
    return httpx.Client(base_url=get_settings().api_base_url, timeout=10.0)


def _raise_for(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code == 422:
        fields = [str(e["loc"][-1]) for e in body.get("detail", []) if e.get("loc")]
        raise ApiError("error.validation", 422, fields)
    raise ApiError(body.get("code", "error.generic"), resp.status_code)


def _request(method: str, path: str, *, auth: bool = False, **kwargs: Any) -> httpx.Response:
    try:
        with _client() as client:
            headers = kwargs.pop("headers", {})
            if auth:
                headers["Authorization"] = f"Bearer {session.get('access_token', '')}"
            resp = client.request(method, path, headers=headers, **kwargs)
            if auth and resp.status_code == 401 and session.get("refresh_token"):
                refreshed = client.post(
                    "/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]}
                )
                if not refreshed.is_success:
                    web_session.clear()
                    raise ApiError("error.invalid_credentials", 401)
                web_session.store_tokens(refreshed.json())
                headers["Authorization"] = f"Bearer {session['access_token']}"
                resp = client.request(method, path, headers=headers, **kwargs)
    except httpx.TransportError as exc:
        raise ApiError("error.unavailable", 503) from exc
    _raise_for(resp)
    return resp


def login(email: str, password: str) -> None:
    tokens = _request(
        "POST", "/api/v1/auth/login", json={"email": email, "password": password}
    ).json()
    web_session.store_tokens(tokens)
    web_session.store_tokens(tokens, me())


def register(email: str, password: str, display_name: str, locale: str) -> None:
    tokens = _request(
        "POST",
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "locale": locale,
        },
    ).json()
    web_session.store_tokens(tokens)
    web_session.store_tokens(tokens, me())


def me() -> dict[str, Any]:
    return _request("GET", "/api/v1/auth/me", auth=True).json()


def logout() -> None:
    token = session.get("refresh_token")
    if token:
        with contextlib.suppress(ApiError):  # Signing out locally must always succeed.
            _request("POST", "/api/v1/auth/logout", json={"refresh_token": token})
    web_session.clear()
