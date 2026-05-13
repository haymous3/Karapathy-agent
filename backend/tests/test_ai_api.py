from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.ai import AIServiceError, OpenRouterService, OpenRouterSettings
from app.main import create_app


class StubChatClient:
    def __init__(self, *, reply: str = "4") -> None:
        self._reply = reply

    def create(self, *, model: str, messages: list[dict[str, str]]) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._reply))]
        )


def _settings() -> OpenRouterSettings:
    return OpenRouterSettings(
        api_key="test-key",
        base_url="https://openrouter.test/api/v1",
        model="openai/gpt-oss-120b",
        timeout_seconds=5.0,
    )


def _build_test_client(tmp_path: Path, *, reply: str = "4") -> TestClient:
    def factory() -> OpenRouterService:
        return OpenRouterService(
            settings=_settings(),
            chat_client=StubChatClient(reply=reply),
        )

    app = create_app(db_path=tmp_path / "test.sqlite3", ai_service_factory=factory)
    return TestClient(app)


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_ai_ping_requires_auth(tmp_path: Path) -> None:
    client = _build_test_client(tmp_path)
    response = client.post("/api/ai/ping")
    assert response.status_code == 401


def test_ai_ping_returns_model_reply(tmp_path: Path) -> None:
    client = _build_test_client(tmp_path, reply="4")
    _login(client)

    response = client.post("/api/ai/ping")

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body == {"ok": True, "model": "openai/gpt-oss-120b", "reply": "4"}


def test_ai_ping_surfaces_service_errors_as_502(tmp_path: Path) -> None:
    def factory() -> OpenRouterService:
        raise AIServiceError("provider unreachable")

    app = create_app(db_path=tmp_path / "test.sqlite3", ai_service_factory=factory)
    client = TestClient(app)
    _login(client)

    response = client.post("/api/ai/ping")

    assert response.status_code == 502
    assert response.json() == {"detail": "provider unreachable"}


@pytest.mark.skipif(
    os.getenv("PM_RUN_LIVE_AI_TESTS") != "1",
    reason="Set PM_RUN_LIVE_AI_TESTS=1 to enable the live AI endpoint smoke test.",
)
def test_ai_ping_live_smoke(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "test.sqlite3")
    client = TestClient(app)
    _login(client)

    response = client.post("/api/ai/ping")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "4" in body["reply"]
