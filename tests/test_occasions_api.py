"""Occasions: opening bottles, ratings, people, and keeping the cellar consistent."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

V1 = "/api/v1"
TODAY = date.today().isoformat()


def _user(client: TestClient, email: str = "ana@example.com") -> dict:
    resp = client.post(
        f"{V1}/auth/register",
        json={"email": email, "password": "correct-horse-1", "display_name": "Ana"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _wine(
    client: TestClient,
    auth: dict,
    quantity: int = 0,
    rating: float | None = 8.5,
    nickname: str = "Crasto Superior",
    vintage: int | None = 2019,
) -> dict:
    body: dict = {"wine": {"nickname": nickname, "wine_type": "red", "general_rating": rating}}
    if quantity:
        body["bottles"] = {"quantity": quantity, "vintage": vintage}
    resp = client.post(f"{V1}/wines", json=body, headers=auth)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _occasion(**over: object) -> dict:
    return {
        "occurred_on": TODAY,
        "meal_time": "dinner",
        "place_type": "my_house",
        "city": "Porto",
        "country_code": "PT",
        "people": ["Mom", "João"],
        **over,
    }


def _bottle_status(client: TestClient, auth: dict, bottle_id: int) -> str:
    return client.get(f"{V1}/bottles/{bottle_id}", headers=auth).json()["status"]


def test_open_bottle_from_cellar_and_rate_it(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth, quantity=2)
    bottle = wine["bottles"][0]["id"]
    resp = client.post(
        f"{V1}/occasions",
        json=_occasion(
            wines=[
                {
                    "wine_id": wine["id"],
                    "bottle_id": bottle,
                    "rating": 7.5,
                    "tasting_notes": "A bit closed.",
                }
            ]
        ),
        headers=auth,
    )
    assert resp.status_code == 201, resp.text
    occ = resp.json()
    assert occ["people"] == ["João", "Mom"]
    row = occ["wines"][0]
    assert row["vintage"] == 2019  # taken from the bottle
    assert row["rating"] == 7.5 and row["general_rating"] == 8.5
    assert _bottle_status(client, auth, bottle) == "consumed"
    # Cellar now has one bottle left.
    cellar = client.get(f"{V1}/wines", headers=auth).json()
    assert cellar[0]["bottles_in_cellar"] == 1
    # The wine's tasting history shows the experience.
    tastings = client.get(f"{V1}/wines/{wine['id']}/tastings", headers=auth).json()
    assert tastings[0]["rating"] == 7.5 and tastings[0]["from_cellar"] is True


def test_wine_drunk_elsewhere_has_no_bottle(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth)  # no bottles
    resp = client.post(
        f"{V1}/occasions",
        json=_occasion(
            place_type="restaurant",
            place_name="Antiqvvm",
            wines=[{"wine_id": wine["id"], "vintage": 2017, "rating": 9}],
        ),
        headers=auth,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["wines"][0]["bottle_id"] is None
    assert resp.json()["wines"][0]["vintage"] == 2017


def test_bottle_cannot_be_opened_twice(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth, quantity=1)
    bottle = wine["bottles"][0]["id"]
    body = _occasion(wines=[{"wine_id": wine["id"], "bottle_id": bottle}])
    assert client.post(f"{V1}/occasions", json=body, headers=auth).status_code == 201
    again = client.post(f"{V1}/occasions", json=body, headers=auth)
    assert again.status_code == 409
    assert again.json()["code"] == "error.bottle_not_available"
    twice_in_one = _occasion(wines=[{"wine_id": wine["id"], "bottle_id": bottle}] * 2)
    assert client.post(f"{V1}/occasions", json=twice_in_one, headers=auth).status_code == 422


def test_editing_occasion_returns_dropped_bottles(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth, quantity=2)
    b1, b2 = (b["id"] for b in wine["bottles"])
    occ = client.post(
        f"{V1}/occasions",
        json=_occasion(wines=[{"wine_id": wine["id"], "bottle_id": b1}]),
        headers=auth,
    ).json()
    # Keep the same bottle (allowed even though it's already opened) and change the rating.
    same = client.put(
        f"{V1}/occasions/{occ['id']}",
        json=_occasion(wines=[{"wine_id": wine["id"], "bottle_id": b1, "rating": 6}]),
        headers=auth,
    )
    assert same.status_code == 200, same.text
    assert same.json()["wines"][0]["rating"] == 6
    # Swap to the other bottle: b1 goes back to the cellar, b2 is opened.
    swapped = client.put(
        f"{V1}/occasions/{occ['id']}",
        json=_occasion(wines=[{"wine_id": wine["id"], "bottle_id": b2}]),
        headers=auth,
    )
    assert swapped.status_code == 200, swapped.text
    assert _bottle_status(client, auth, b1) == "in_cellar"
    assert _bottle_status(client, auth, b2) == "consumed"


def test_deleting_occasion_returns_bottles(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth, quantity=1)
    b = wine["bottles"][0]["id"]
    occ = client.post(
        f"{V1}/occasions",
        json=_occasion(wines=[{"wine_id": wine["id"], "bottle_id": b}]),
        headers=auth,
    ).json()
    assert client.delete(f"{V1}/occasions/{occ['id']}", headers=auth).status_code == 204
    assert _bottle_status(client, auth, b) == "in_cellar"


def test_opened_bottle_protects_history(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth, quantity=1)
    b = wine["bottles"][0]["id"]
    client.post(
        f"{V1}/occasions",
        json=_occasion(wines=[{"wine_id": wine["id"], "bottle_id": b}]),
        headers=auth,
    )
    assert client.delete(f"{V1}/bottles/{b}", headers=auth).status_code == 409
    assert client.delete(f"{V1}/wines/{wine['id']}", headers=auth).status_code == 409
    edit = client.put(f"{V1}/bottles/{b}", json={"status": "in_cellar"}, headers=auth)
    assert edit.status_code == 409


def test_contacts_are_reused(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth)
    for people in (["Mom", "João"], ["mom", "Bia"]):
        client.post(
            f"{V1}/occasions",
            json=_occasion(people=people, wines=[{"wine_id": wine["id"]}]),
            headers=auth,
        )
    names = [c["name"] for c in client.get(f"{V1}/contacts", headers=auth).json()]
    assert names == ["Bia", "João", "Mom"]


def test_occasions_are_private(client: TestClient) -> None:
    ana = _user(client)
    bob = _user(client, "bob@example.com")
    ana_wine = _wine(client, ana, quantity=1)
    bob_wine = _wine(client, bob)
    occ = client.post(
        f"{V1}/occasions", json=_occasion(wines=[{"wine_id": ana_wine["id"]}]), headers=ana
    ).json()
    assert client.get(f"{V1}/occasions", headers=bob).json() == []
    assert client.get(f"{V1}/occasions/{occ['id']}", headers=bob).status_code == 404
    assert client.delete(f"{V1}/occasions/{occ['id']}", headers=bob).status_code == 404
    assert client.get(f"{V1}/wines/{ana_wine['id']}/tastings", headers=bob).status_code == 404
    assert client.get(f"{V1}/contacts", headers=bob).json() == []
    # Bob can't record an occasion with Ana's wine or open Ana's bottle.
    steal = _occasion(
        wines=[{"wine_id": bob_wine["id"], "bottle_id": ana_wine["bottles"][0]["id"]}]
    )
    assert client.post(f"{V1}/occasions", json=steal, headers=bob).status_code == 404
    use = _occasion(wines=[{"wine_id": ana_wine["id"]}])
    assert client.post(f"{V1}/occasions", json=use, headers=bob).status_code == 404


def test_bottle_must_belong_to_the_wine(client: TestClient) -> None:
    auth = _user(client)
    a = _wine(client, auth, quantity=1, nickname="A")
    b = _wine(client, auth, nickname="B")
    body = _occasion(wines=[{"wine_id": b["id"], "bottle_id": a["bottles"][0]["id"]}])
    resp = client.post(f"{V1}/occasions", json=body, headers=auth)
    assert resp.status_code == 422 and resp.json()["code"] == "error.bottle_wine_mismatch"


def test_validation(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth)
    w = [{"wine_id": wine["id"]}]
    future = (date.today() + timedelta(days=1)).isoformat()

    def status(**over: object) -> int:
        return client.post(f"{V1}/occasions", json=_occasion(**over), headers=auth).status_code

    assert status(wines=[]) == 422  # at least one wine
    assert status(wines=w, occurred_on=future) == 422
    assert status(wines=w, meal_time="midnight") == 422
    assert status(wines=w, people=["Mom", "mom"]) == 422
    assert status(wines=[{"wine_id": wine["id"], "rating": 7.2}]) == 422
    assert status(wines=w) == 201


def test_list_newest_first(client: TestClient) -> None:
    auth = _user(client)
    wine = _wine(client, auth)
    w = [{"wine_id": wine["id"]}]
    for d in ("2026-01-02", "2026-03-04", "2025-12-31"):
        client.post(f"{V1}/occasions", json=_occasion(occurred_on=d, wines=w), headers=auth)
    dates = [o["occurred_on"] for o in client.get(f"{V1}/occasions", headers=auth).json()]
    assert dates == ["2026-03-04", "2026-01-02", "2025-12-31"]
