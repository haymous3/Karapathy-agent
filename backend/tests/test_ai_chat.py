from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.ai import (
    AIServiceError,
    ChatResult,
    OpenRouterService,
    OpenRouterSettings,
)
from app.main import create_app
from app.seed_data import DEFAULT_BOARD_DATA


class RecordingChatClient:
    """Stub chat client that records calls and returns a canned JSON content string."""

    def __init__(self, *, content: str) -> None:
        self._content = content
        self.calls: list[dict[str, Any]] = []

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> SimpleNamespace:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "response_format": response_format,
            }
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


def _settings() -> OpenRouterSettings:
    return OpenRouterSettings(
        api_key="test-key",
        base_url="https://openrouter.test/api/v1",
        model="openai/gpt-oss-120b",
        timeout_seconds=5.0,
    )


def _build_client_with_canned_chat_response(
    tmp_path: Path,
    *,
    content: str,
) -> tuple[TestClient, RecordingChatClient]:
    chat_client = RecordingChatClient(content=content)

    def factory() -> OpenRouterService:
        return OpenRouterService(settings=_settings(), chat_client=chat_client)

    app = create_app(db_path=tmp_path / "test.sqlite3", ai_service_factory=factory)
    return TestClient(app), chat_client


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_ai_chat_requires_auth(tmp_path: Path) -> None:
    client, _ = _build_client_with_canned_chat_response(
        tmp_path,
        content=json.dumps({"assistantMessage": "Hi", "boardUpdate": None}),
    )
    response = client.post("/api/ai/chat", json={"message": "hello"})
    assert response.status_code == 401


def test_ai_chat_message_only_response_returns_current_board(tmp_path: Path) -> None:
    client, chat_client = _build_client_with_canned_chat_response(
        tmp_path,
        content=json.dumps({"assistantMessage": "Hi there!", "boardUpdate": None}),
    )
    _login(client)

    response = client.post(
        "/api/ai/chat",
        json={
            "message": "Hi",
            "history": [
                {"role": "user", "content": "earlier user"},
                {"role": "assistant", "content": "earlier assistant"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistantMessage"] == "Hi there!"
    assert body["boardUpdated"] is False
    assert body["board"] == DEFAULT_BOARD_DATA

    call = chat_client.calls[0]
    assert call["model"] == "openai/gpt-oss-120b"
    assert call["response_format"]["type"] == "json_schema"
    assert call["response_format"]["json_schema"]["name"] == "pm_chat_response"
    roles = [m["role"] for m in call["messages"]]
    assert roles[:2] == ["system", "system"]
    assert "Current board JSON" in call["messages"][1]["content"]
    assert roles[2:] == ["user", "assistant", "user"]
    assert call["messages"][-1]["content"] == "Hi"


def test_ai_chat_applies_valid_board_update_and_persists(tmp_path: Path) -> None:
    updated_board: dict[str, Any] = deepcopy(DEFAULT_BOARD_DATA)
    updated_board["columns"][0]["cardIds"].append("card-new")
    updated_board["cards"]["card-new"] = {
        "id": "card-new",
        "title": "Brand new task",
        "details": "Spec it out",
    }

    client, _ = _build_client_with_canned_chat_response(
        tmp_path,
        content=json.dumps(
            {
                "assistantMessage": "Added the new card to Backlog.",
                "boardUpdate": updated_board,
            }
        ),
    )
    _login(client)

    response = client.post(
        "/api/ai/chat",
        json={"message": "Add a card titled 'Brand new task'."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistantMessage"] == "Added the new card to Backlog."
    assert body["boardUpdated"] is True
    assert body["board"] == updated_board

    follow_up = client.get("/api/board")
    assert follow_up.status_code == 200
    assert follow_up.json() == updated_board


def test_ai_chat_invalid_board_update_soft_fails(tmp_path: Path) -> None:
    bad_update = {
        "columns": [
            {"id": "col-1", "title": "Only", "cardIds": ["card-missing"]},
        ],
        "cards": {},
    }

    client, _ = _build_client_with_canned_chat_response(
        tmp_path,
        content=json.dumps(
            {
                "assistantMessage": "Tried to add a card.",
                "boardUpdate": bad_update,
            }
        ),
    )
    _login(client)

    response = client.post("/api/ai/chat", json={"message": "Do a thing"})

    assert response.status_code == 200
    body = response.json()
    assert body["boardUpdated"] is False
    assert body["board"] == DEFAULT_BOARD_DATA
    assert body["assistantMessage"].startswith("Tried to add a card.")
    assert "invalid" in body["assistantMessage"].lower()


def test_ai_chat_returns_502_on_non_json_content(tmp_path: Path) -> None:
    client, _ = _build_client_with_canned_chat_response(
        tmp_path,
        content="this is not JSON",
    )
    _login(client)

    response = client.post("/api/ai/chat", json={"message": "hi"})
    assert response.status_code == 502


def test_ai_chat_returns_502_on_schema_violation(tmp_path: Path) -> None:
    client, _ = _build_client_with_canned_chat_response(
        tmp_path,
        content=json.dumps({"assistantMessage": "Hi"}),
    )
    _login(client)

    response = client.post("/api/ai/chat", json={"message": "hi"})
    assert response.status_code == 502


def test_ai_chat_rejects_empty_message(tmp_path: Path) -> None:
    client, _ = _build_client_with_canned_chat_response(
        tmp_path,
        content=json.dumps({"assistantMessage": "Hi", "boardUpdate": None}),
    )
    _login(client)

    response = client.post("/api/ai/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_service_returns_parsed_board_update() -> None:
    update = {
        "columns": [{"id": "c1", "title": "Only", "cardIds": ["k1"]}],
        "cards": {"k1": {"id": "k1", "title": "T", "details": "D"}},
    }
    chat_client = RecordingChatClient(
        content=json.dumps({"assistantMessage": "ok", "boardUpdate": update}),
    )
    service = OpenRouterService(settings=_settings(), chat_client=chat_client)

    result: ChatResult = service.chat(message="x", history=[], board=DEFAULT_BOARD_DATA)

    assert result.assistant_message == "ok"
    assert result.board_update == update


def test_chat_service_raises_on_malformed_json() -> None:
    chat_client = RecordingChatClient(content="not-json")
    service = OpenRouterService(settings=_settings(), chat_client=chat_client)

    with pytest.raises(AIServiceError):
        service.chat(message="x", history=[], board=DEFAULT_BOARD_DATA)


def test_chat_service_raises_on_schema_violation() -> None:
    chat_client = RecordingChatClient(
        content=json.dumps({"assistantMessage": 42, "boardUpdate": None}),
    )
    service = OpenRouterService(settings=_settings(), chat_client=chat_client)

    with pytest.raises(AIServiceError):
        service.chat(message="x", history=[], board=DEFAULT_BOARD_DATA)


@pytest.mark.skipif(
    os.getenv("PM_RUN_LIVE_AI_TESTS") != "1",
    reason="Set PM_RUN_LIVE_AI_TESTS=1 to enable the live AI chat smoke test.",
)
def test_ai_chat_live_smoke(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "test.sqlite3")
    client = TestClient(app)
    _login(client)

    response = client.post(
        "/api/ai/chat",
        json={"message": "Just say hi and don't change the board."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["boardUpdated"] is False
    assert body["assistantMessage"]
