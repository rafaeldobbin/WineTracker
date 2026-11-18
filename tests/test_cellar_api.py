"""Cellar API: wines, bottles, lookups and per-user privacy."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

V1 = "/api/v1"


def _user(client: TestClient, email: str = "ana@example.com", locale: str = "en") -> dict:
    resp = client.post(
        f"{V1}/auth/register",
        json={
            "email": email,
            "password": "correct-horse-1",
            "display_name": "Ana",
            "locale": locale,
        },
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


WINE = {
    "nickname": "Crasto Superior",
    "official_name": "Quinta do Crasto Superior",
    "wine_type": "red",
    "producer_name": "Quinta do Crasto",
    "region_name": "Douro",
    "country_code": "PT",
    "grapes": [
        {"name": "Touriga Nacional", "percentage": 60},
        {"name": "Touriga Franca", "percentage": 40},
    ],
    "general_notes": "Dark fruit, firm tannins.",
    "general_rating": 8.5,
}


def _create(client: TestClient, auth: dict, wine: dict | None = None, **bottles: object) -> dict:
    body: dict = {"wine": wine or WINE}
    if bottles:
        body["bottles"] = bottles
    resp = client.post(f"{V1}/wines", json=body, headers=auth)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_wine_with_bottles(client: TestClient) -> None:
    auth = _user(client)
    wine = _create(client, auth, quantity=6, vintage=2019, price="32.50", store_name="Garrafeira")
    assert wine["producer"] == "Quinta do Crasto"
    assert wine["region"] == "Douro" and wine["country_code"] == "PT"
    assert [g["name"] for g in wine["grapes"]] == ["Touriga Nacional", "Touriga Franca"]
    assert wine["general_rating"] == 8.5
    assert len(wine["bottles"]) == 6
    b = wine["bottles"][0]
    assert b["vintage"] == 2019 and b["store"] == "Garrafeira" and b["status"] == "in_cellar"
    assert b["currency"] == "USD"  # default from the user's language (en → USD)


def test_currency_defaults_to_brl_for_portuguese(client: TestClient) -> None:
    auth = _user(client, locale="pt-BR")
    wine = _create(client, auth, price="120.00")
    assert wine["bottles"][0]["currency"] == "BRL"


def test_lookups_reused_case_insensitively(client: TestClient) -> None:
    auth = _user(client)
    _create(client, auth)
    _create(
        client,
        auth,
        {**WINE, "nickname": "Crasto Reserva", "producer_name": "  quinta   do crasto "},
    )
    producers = client.get(f"{V1}/lookups/producers", params={"q": "crasto"}, headers=auth)
    assert [p["name"] for p in producers.json()] == ["Quinta do Crasto"]


def test_cellar_list_counts_and_filters(client: TestClient) -> None:
    auth = _user(client)
    soon = date.today().year
    _create(client, auth, quantity=2, vintage=2018, drink_until=soon)
    _create(
        client,
        auth,
        {
            **WINE,
            "nickname": "Alvarinho",
            "wine_type": "white",
            "region_name": "Vinho Verde",
            "grapes": [{"name": "Alvarinho"}],
            "producer_name": "Soalheiro",
        },
        vintage=2023,
    )
    _create(
        client,
        auth,
        {
            **WINE,
            "nickname": "Empty bottle shelf",
            "region_name": None,
            "country_code": "FR",
            "grapes": [],
        },
    )  # no bottles

    rows = client.get(f"{V1}/wines", headers=auth).json()
    assert [r["nickname"] for r in rows] == ["Alvarinho", "Crasto Superior"]
    crasto = rows[1]
    assert crasto["bottles_in_cellar"] == 2 and crasto["vintages"] == [2018]
    assert crasto["drink_soon"] is True

    def names(**params: object) -> list[str]:
        return [
            r["nickname"] for r in client.get(f"{V1}/wines", params=params, headers=auth).json()
        ]

    assert names(in_cellar_only=False) == ["Alvarinho", "Crasto Superior", "Empty bottle shelf"]
    assert names(wine_type="white") == ["Alvarinho"]
    assert names(q="soalh") == ["Alvarinho"]  # matches producer
    assert names(q="verde") == ["Alvarinho"]  # matches region
    assert names(drink_soon=True) == ["Crasto Superior"]
    assert names(country="FR", in_cellar_only=False) == ["Empty bottle shelf"]
    assert names(q="100%") == []  # wildcards are literal
    grapes = client.get(f"{V1}/lookups/grapes", headers=auth).json()
    alvarinho = next(g["id"] for g in grapes if g["name"] == "Alvarinho")
    assert names(grape_id=alvarinho) == ["Alvarinho"]


def test_users_cannot_see_or_touch_each_others_cellar(client: TestClient) -> None:
    ana = _user(client)
    bob = _user(client, "bob@example.com")
    wine = _create(client, ana, quantity=1)
    bottle_id = wine["bottles"][0]["id"]

    assert client.get(f"{V1}/wines", headers=bob).json() == []
    assert client.get(f"{V1}/wines/{wine['id']}", headers=bob).status_code == 404
    assert client.put(f"{V1}/wines/{wine['id']}", json=WINE, headers=bob).status_code == 404
    assert client.delete(f"{V1}/wines/{wine['id']}", headers=bob).status_code == 404
    assert client.post(f"{V1}/wines/{wine['id']}/bottles", json={}, headers=bob).status_code == 404
    assert client.get(f"{V1}/bottles/{bottle_id}", headers=bob).status_code == 404
    assert client.put(f"{V1}/bottles/{bottle_id}", json={}, headers=bob).status_code == 404
    assert client.delete(f"{V1}/bottles/{bottle_id}", headers=bob).status_code == 404
    # Ana's data is untouched.
    assert len(client.get(f"{V1}/wines/{wine['id']}", headers=ana).json()["bottles"]) == 1


def test_update_wine_replaces_grapes_and_rating(client: TestClient) -> None:
    auth = _user(client)
    wine = _create(client, auth)
    resp = client.put(
        f"{V1}/wines/{wine['id']}",
        json={**WINE, "grapes": [{"name": "Tinta Roriz"}], "general_rating": None},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    assert [g["name"] for g in resp.json()["grapes"]] == ["Tinta Roriz"]
    assert resp.json()["general_rating"] is None


def test_bottle_update_status_and_delete(client: TestClient) -> None:
    auth = _user(client)
    wine = _create(client, auth, quantity=2, vintage=2020)
    first, second = (b["id"] for b in wine["bottles"])

    gifted = client.put(
        f"{V1}/bottles/{first}", json={"vintage": 2020, "status": "gifted"}, headers=auth
    )
    assert gifted.status_code == 200 and gifted.json()["status"] == "gifted"
    # "consumed" only happens by opening the bottle at an occasion.
    consumed = client.put(f"{V1}/bottles/{first}", json={"status": "consumed"}, headers=auth)
    assert consumed.status_code == 422

    assert client.delete(f"{V1}/bottles/{second}", headers=auth).status_code == 204
    rows = client.get(f"{V1}/wines", headers=auth).json()
    assert rows == []  # gifted + deleted → nothing left in the cellar


def test_delete_wine_removes_its_bottles(client: TestClient) -> None:
    auth = _user(client)
    wine = _create(client, auth, quantity=3)
    assert client.delete(f"{V1}/wines/{wine['id']}", headers=auth).status_code == 204
    assert client.get(f"{V1}/wines/{wine['id']}", headers=auth).status_code == 404


def test_validation_rules(client: TestClient) -> None:
    auth = _user(client)

    def status_for(wine: dict | None = None, **bottles: object) -> int:
        body: dict = {"wine": wine or WINE}
        if bottles:
            body["bottles"] = bottles
        return client.post(f"{V1}/wines", json=body, headers=auth).status_code

    assert status_for({**WINE, "general_rating": 7.3}) == 422  # not a half step
    assert status_for({**WINE, "general_rating": 10.5}) == 422
    assert (
        status_for(
            {
                **WINE,
                "grapes": [
                    {"name": "Merlot", "percentage": 70},
                    {"name": "Malbec", "percentage": 40},
                ],
            }
        )
        == 422
    )
    assert status_for({**WINE, "grapes": [{"name": "Merlot"}, {"name": "merlot"}]}) == 422
    assert status_for({**WINE, "country_code": None}) == 422  # region needs a country
    assert status_for({**WINE, "nickname": "   "}) == 422
    assert status_for(quantity=0) == 422
    assert status_for(quantity=49) == 422
    assert status_for(drink_from=2030, drink_until=2025) == 422
    assert status_for(purchase_date="2999-01-01") == 422
    assert status_for(price="-1") == 422


def test_lookups_seed_free_regions_by_country(client: TestClient) -> None:
    auth = _user(client)
    _create(client, auth)
    regions = client.get(f"{V1}/lookups/regions", params={"country": "pt"}, headers=auth).json()
    assert {"name": "Douro", "country_code": "PT"}.items() <= regions[0].items()
    assert client.get(f"{V1}/lookups/grapes").status_code == 401  # requires sign-in
