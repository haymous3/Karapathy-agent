"""OpenRouter AI integration for the PM MVP backend.

Wraps the OpenAI Python SDK pointed at OpenRouter so the rest of the
backend has a single, mockable seam for AI calls. Provides:

- Part 8: "2+2" connectivity probe (`ping`).
- Part 9: structured chat that may propose a board update.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TIMEOUT_SECONDS = 30.0

PROBE_PROMPT = "What is 2+2? Reply with only the number."

CHAT_SYSTEM_PROMPT = """You are the AI assistant inside a Kanban project management web app.

You receive:
- the user's latest message
- recent conversation history
- the current board JSON

The board JSON has this exact shape:
{
  "columns": [
    {"id": "col-id", "title": "Column title", "cardIds": ["card-id-1", "card-id-2"]}
  ],
  "cards": {
    "card-id-1": {"id": "card-id-1", "title": "Card title", "details": "Card details"}
  }
}

Rules for any board update you propose:
- Keep the same column ids the board already has unless the user explicitly asks to add or remove a column.
- When adding a new card, invent a new unique id of the form "card-<short-slug>" that is not already used.
- Every card id that appears in any column's "cardIds" list MUST also appear as a key in "cards" with the same id, title, and details.
- Every card id that appears as a key in "cards" MUST appear in exactly one column's "cardIds" list.
- Do NOT include a board update if the user is only asking a question or chatting.

Always respond with a SHORT plain-text "assistantMessage" describing what you did or answering the user.
Only include "boardUpdate" when you are actually changing the board; otherwise set it to null.
"""

CHAT_RESPONSE_SCHEMA: dict[str, Any] = {
    "name": "pm_chat_response",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["assistantMessage", "boardUpdate"],
        "properties": {
            "assistantMessage": {"type": "string"},
            "boardUpdate": {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["columns", "cards"],
                        "properties": {
                            "columns": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["id", "title", "cardIds"],
                                    "properties": {
                                        "id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "cardIds": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                            },
                            "cards": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["id", "title", "details"],
                                    "properties": {
                                        "id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "details": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                ]
            },
        },
    },
}


class _ChatCardModel(BaseModel):
    id: str
    title: str
    details: str


class _ChatColumnModel(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class _ChatBoardUpdateModel(BaseModel):
    columns: list[_ChatColumnModel]
    cards: dict[str, _ChatCardModel]


class ChatResponseModel(BaseModel):
    model_config = {"extra": "forbid"}

    assistantMessage: str
    boardUpdate: _ChatBoardUpdateModel | None


@dataclass(frozen=True)
class ChatResult:
    assistant_message: str
    board_update: dict[str, Any] | None


class AIServiceError(RuntimeError):
    """Raised when the AI provider is misconfigured or unreachable."""


@dataclass(frozen=True)
class OpenRouterSettings:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "OpenRouterSettings":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise AIServiceError(
                "OPENROUTER_API_KEY is not set. Add it to pm/.env or the container environment."
            )
        return cls(
            api_key=api_key,
            base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
            model=os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            timeout_seconds=float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
        )


class ChatClient(Protocol):
    """Minimal protocol matching the bits of the OpenAI SDK we use.

    Defined so tests can swap in a fake without monkeypatching the SDK.
    """

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ):  # pragma: no cover - protocol
        ...


def _build_default_client(settings: OpenRouterSettings) -> ChatClient:
    client = OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
    )
    return client.chat.completions


class OpenRouterService:
    """Thin facade around the chat-completions API for OpenRouter."""

    def __init__(
        self,
        settings: OpenRouterSettings | None = None,
        chat_client: ChatClient | None = None,
    ) -> None:
        self._settings = settings or OpenRouterSettings.from_env()
        self._chat_client = chat_client or _build_default_client(self._settings)

    @property
    def model(self) -> str:
        return self._settings.model

    def ping(self) -> str:
        """Send a fixed prompt and return the model's reply text."""

        return self.complete(PROBE_PROMPT)

    def complete(self, prompt: str) -> str:
        content = self._raw_complete(
            messages=[{"role": "user", "content": prompt}],
        )
        return content.strip()

    def chat(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        board: dict[str, Any],
    ) -> ChatResult:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {
                "role": "system",
                "content": "Current board JSON:\n" + json.dumps(board, ensure_ascii=False),
            },
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        content = self._raw_complete(
            messages=messages,
            response_format={"type": "json_schema", "json_schema": CHAT_RESPONSE_SCHEMA},
        )

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIServiceError(f"AI returned non-JSON content: {exc}") from exc

        try:
            parsed = ChatResponseModel.model_validate(payload)
        except ValidationError as exc:
            raise AIServiceError(f"AI response failed schema validation: {exc}") from exc

        board_update = (
            parsed.boardUpdate.model_dump() if parsed.boardUpdate is not None else None
        )
        return ChatResult(
            assistant_message=parsed.assistantMessage.strip(),
            board_update=board_update,
        )

    def _raw_complete(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        try:
            if response_format is None:
                response = self._chat_client.create(
                    model=self._settings.model,
                    messages=messages,
                )
            else:
                response = self._chat_client.create(
                    model=self._settings.model,
                    messages=messages,
                    response_format=response_format,
                )
        except OpenAIError as exc:
            raise AIServiceError(f"OpenRouter request failed: {exc}") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError) as exc:
            raise AIServiceError("OpenRouter response missing message content") from exc

        if content is None:
            raise AIServiceError("OpenRouter response message content is null")

        return content
