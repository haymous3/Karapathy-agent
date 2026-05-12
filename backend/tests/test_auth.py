from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app


def test_login_success_sets_session_cookie() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "user"}
    assert "pm_session=" in response.headers.get("set-cookie", "")


def test_login_failure_returns_401() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "wrong"},
    )

    assert response.status_code == 401


def test_auth_me_requires_session() -> None:
    client = TestClient(app)

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_auth_me_after_login_returns_user() -> None:
    client = TestClient(app)
    client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "user"}


def test_logout_clears_session() -> None:
    client = TestClient(app)
    client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )

    logout_response = client.post("/api/auth/logout")
    me_response = client.get("/api/auth/me")

    assert logout_response.status_code == 200
    assert logout_response.json() == {"authenticated": False}
    assert me_response.status_code == 401
