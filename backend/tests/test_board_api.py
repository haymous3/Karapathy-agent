from app.seed_data import DEFAULT_BOARD_DATA


def login(client) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_board_routes_require_auth(client) -> None:
    get_response = client.get("/api/board")
    put_response = client.put(
        "/api/board",
        json={
            "columns": [{"id": "col-1", "title": "One", "cardIds": []}],
            "cards": {},
        },
    )

    assert get_response.status_code == 401
    assert put_response.status_code == 401


def test_get_board_returns_seeded_default_board(client) -> None:
    login(client)

    response = client.get("/api/board")

    assert response.status_code == 200
    assert response.json() == DEFAULT_BOARD_DATA


def test_put_board_updates_board_and_preserves_order(client) -> None:
    login(client)
    payload = {
        "columns": [
            {"id": "col-alpha", "title": "Alpha", "cardIds": ["card-b", "card-a"]},
            {"id": "col-beta", "title": "Beta", "cardIds": []},
        ],
        "cards": {
            "card-a": {"id": "card-a", "title": "A", "details": "first"},
            "card-b": {"id": "card-b", "title": "B", "details": "second"},
        },
    }

    put_response = client.put("/api/board", json=payload)
    get_response = client.get("/api/board")

    assert put_response.status_code == 200
    assert put_response.json() == payload
    assert get_response.status_code == 200
    assert get_response.json() == payload


def test_put_board_rejects_invalid_card_assignment(client) -> None:
    login(client)
    payload = {
        "columns": [{"id": "col-1", "title": "One", "cardIds": ["card-x"]}],
        "cards": {
            "card-y": {"id": "card-y", "title": "Y", "details": "not referenced"},
        },
    }

    response = client.put("/api/board", json=payload)

    assert response.status_code == 400
