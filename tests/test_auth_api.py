from fastapi.testclient import TestClient

REG = {"email": "Ana@Example.com", "password": "correct-horse-1", "display_name": "Ana"}


def _register(client: TestClient) -> dict:
    resp = client.post("/api/v1/auth/register", json=REG)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_register_login_me(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": REG["password"]}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "ana@example.com"
    assert me.json()["locale"] == "en"


def test_duplicate_email_rejected(client: TestClient) -> None:
    _register(client)
    resp = client.post("/api/v1/auth/register", json=REG)
    assert resp.status_code == 409
    assert resp.json()["code"] == "error.email_taken"


def test_wrong_password(client: TestClient) -> None:
    _register(client)
    resp = client.post("/api/v1/auth/login", json={"email": REG["email"], "password": "nope"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "error.invalid_credentials"


def test_short_password_rejected(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/register", json={**REG, "password": "short"})
    assert resp.status_code == 422


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


def test_refresh_rotates_and_detects_reuse(client: TestClient) -> None:
    first = _register(client)
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200
    # Replaying the old token is treated as theft: it fails and revokes the new one too.
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401
    after = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
    )
    assert after.status_code == 401


def test_access_token_cannot_be_used_as_refresh(client: TestClient) -> None:
    tokens = _register(client)
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert resp.status_code == 401


def test_logout_revokes_refresh(client: TestClient) -> None:
    tokens = _register(client)
    assert (
        client.post(
            "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 204
    )
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401
