from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest
from openai import OpenAIError

from app.ai import (
    AIServiceError,
    OpenRouterService,
    OpenRouterSettings,
    PROBE_PROMPT,
)


class FakeChatClient:
    def __init__(self, *, reply: str | None = "4", error: Exception | None = None) -> None:
        self._reply = reply
        self._error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, *, model: str, messages: list[dict[str, str]]) -> SimpleNamespace:
        self.calls.append({"model": model, "messages": messages})
        if self._error is not None:
            raise self._error
        message = SimpleNamespace(content=self._reply)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


@pytest.fixture
def settings() -> OpenRouterSettings:
    return OpenRouterSettings(
        api_key="test-key",
        base_url="https://openrouter.test/api/v1",
        model="openai/gpt-oss-120b",
        timeout_seconds=5.0,
    )


def test_settings_from_env_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(AIServiceError):
        OpenRouterSettings.from_env()


def test_settings_from_env_uses_defaults_when_only_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-from-env")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_TIMEOUT_SECONDS", raising=False)

    loaded = OpenRouterSettings.from_env()

    assert loaded.api_key == "key-from-env"
    assert loaded.base_url == "https://openrouter.ai/api/v1"
    assert loaded.model == "openai/gpt-oss-120b"
    assert loaded.timeout_seconds == 30.0


def test_ping_returns_stripped_reply(settings: OpenRouterSettings) -> None:
    fake = FakeChatClient(reply="  4  ")
    service = OpenRouterService(settings=settings, chat_client=fake)

    reply = service.ping()

    assert reply == "4"
    assert fake.calls == [
        {
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "user", "content": PROBE_PROMPT}],
        }
    ]


def test_ping_wraps_openai_error(settings: OpenRouterSettings) -> None:
    fake = FakeChatClient(error=OpenAIError("boom"))
    service = OpenRouterService(settings=settings, chat_client=fake)

    with pytest.raises(AIServiceError):
        service.ping()


def test_ping_rejects_null_content(settings: OpenRouterSettings) -> None:
    fake = FakeChatClient(reply=None)
    service = OpenRouterService(settings=settings, chat_client=fake)

    with pytest.raises(AIServiceError):
        service.ping()


class EmptyChoicesChatClient:
    def create(self, *, model: str, messages: list[dict[str, str]]) -> SimpleNamespace:
        return SimpleNamespace(choices=[])


def test_ping_rejects_response_without_choices(settings: OpenRouterSettings) -> None:
    service = OpenRouterService(settings=settings, chat_client=EmptyChoicesChatClient())

    with pytest.raises(AIServiceError):
        service.ping()


@pytest.mark.skipif(
    os.getenv("PM_RUN_LIVE_AI_TESTS") != "1",
    reason="Set PM_RUN_LIVE_AI_TESTS=1 to enable the live OpenRouter smoke test.",
)
def test_ping_live_smoke() -> None:
    service = OpenRouterService()
    reply = service.ping()
    assert reply
    assert "4" in reply
