import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from app.ai import AIServiceError, ChatResult, OpenRouterService
from app.db import BoardRepository
from app.seed_data import DEFAULT_BOARD_DATA

VALID_USERNAME = "user"
VALID_PASSWORD = "password"
SESSION_AUTH_KEY = "authenticated"
SESSION_USER_KEY = "username"
FRONTEND_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
FRONTEND_INDEX_FILE = FRONTEND_STATIC_DIR / "index.html"
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "pm_mvp.sqlite3"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
PROJECT_ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(PROJECT_ROOT_ENV_FILE, override=False)

FALLBACK_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>PM MVP Backend</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; color: #032147; background: #f7f8fb; }
      .card { background: #ffffff; border: 1px solid rgba(3, 33, 71, 0.08); border-radius: 12px; padding: 1.25rem; max-width: 680px; }
      code { background: #eef3ff; padding: 0.1rem 0.35rem; border-radius: 6px; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>PM MVP backend is running</h1>
      <p>This static placeholder confirms FastAPI and Docker wiring for Part 2.</p>
      <p>Try <code>/health</code> and <code>/api/hello</code>.</p>
    </div>
  </body>
</html>"""


class LoginRequest(BaseModel):
    username: str
    password: str


class CardPayload(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    details: str


class ColumnPayload(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    cardIds: list[str]


class BoardPayload(BaseModel):
    columns: list[ColumnPayload]
    cards: dict[str, CardPayload]


class ChatHistoryMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatHistoryMessage] = Field(default_factory=list)


def normalize_and_validate_board(payload: BoardPayload) -> dict[str, Any]:
    board = payload.model_dump()
    columns: list[dict[str, Any]] = board["columns"]
    cards: dict[str, dict[str, str]] = board["cards"]

    if not columns:
        raise HTTPException(status_code=400, detail="Board must contain at least one column")

    seen_column_ids: set[str] = set()
    seen_card_ids: set[str] = set()
    card_ids_from_map = set(cards.keys())

    for card_id, card in cards.items():
        if card["id"] != card_id:
            raise HTTPException(
                status_code=400,
                detail=f"Card key/id mismatch for card '{card_id}'",
            )

    for column in columns:
        column_id = column["id"]
        if column_id in seen_column_ids:
            raise HTTPException(status_code=400, detail=f"Duplicate column id '{column_id}'")
        seen_column_ids.add(column_id)

        for card_id in column["cardIds"]:
            if card_id not in card_ids_from_map:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column references unknown card '{card_id}'",
                )
            if card_id in seen_card_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Card '{card_id}' appears in multiple positions",
                )
            seen_card_ids.add(card_id)

    if seen_card_ids != card_ids_from_map:
        unassigned = sorted(card_ids_from_map - seen_card_ids)
        raise HTTPException(
            status_code=400,
            detail=f"Unassigned cards in payload: {', '.join(unassigned)}",
        )

    return board


def require_authenticated_username(request: Request) -> str:
    if not request.session.get(SESSION_AUTH_KEY):
        raise HTTPException(status_code=401, detail="Authentication required")
    username = request.session.get(SESSION_USER_KEY)
    if username != VALID_USERNAME:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Invalid session")
    return username


def create_app(
    db_path: Path | str | None = None,
    ai_service_factory: Callable[[], OpenRouterService] | None = None,
) -> FastAPI:
    app = FastAPI(title="PM MVP Backend", version="0.1.0")
    resolved_db_path = Path(db_path) if db_path else Path(os.getenv("PM_DB_PATH", DEFAULT_DB_PATH))
    repository = BoardRepository(
        db_path=resolved_db_path,
        schema_path=SCHEMA_PATH,
        default_board=DEFAULT_BOARD_DATA,
    )
    repository.initialize()
    build_ai_service = ai_service_factory or OpenRouterService

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET", "change-me-for-production"),
        session_cookie="pm_session",
        same_site="lax",
        https_only=False,
        max_age=60 * 60 * 12,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/hello")
    def hello() -> dict[str, str]:
        return {"message": "hello world", "service": "pm-backend"}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest, request: Request) -> dict[str, object]:
        if payload.username != VALID_USERNAME or payload.password != VALID_PASSWORD:
            request.session.clear()
            raise HTTPException(status_code=401, detail="Invalid username or password")

        request.session.clear()
        request.session[SESSION_AUTH_KEY] = True
        request.session[SESSION_USER_KEY] = VALID_USERNAME
        return {"authenticated": True, "username": VALID_USERNAME}

    @app.post("/api/auth/logout")
    def logout(request: Request) -> dict[str, bool]:
        request.session.clear()
        return {"authenticated": False}

    @app.get("/api/auth/me")
    def auth_me(request: Request) -> dict[str, object]:
        username = require_authenticated_username(request)
        return {"authenticated": True, "username": username}

    @app.get("/api/board")
    def get_board(request: Request) -> dict[str, Any]:
        username = require_authenticated_username(request)
        return repository.get_board(username)

    @app.put("/api/board")
    def put_board(payload: BoardPayload, request: Request) -> dict[str, Any]:
        username = require_authenticated_username(request)
        normalized = normalize_and_validate_board(payload)
        return repository.save_board(username, normalized)

    @app.post("/api/ai/ping")
    def ai_ping(request: Request) -> dict[str, Any]:
        require_authenticated_username(request)
        try:
            service = build_ai_service()
            reply = service.ping()
        except AIServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"ok": True, "model": service.model, "reply": reply}

    @app.post("/api/ai/chat")
    def ai_chat(payload: ChatRequest, request: Request) -> dict[str, Any]:
        username = require_authenticated_username(request)
        current_board = repository.get_board(username)

        try:
            service = build_ai_service()
            result: ChatResult = service.chat(
                message=payload.message,
                history=[m.model_dump() for m in payload.history],
                board=current_board,
            )
        except AIServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        assistant_message = result.assistant_message
        board_updated = False
        final_board = current_board

        if result.board_update is not None:
            try:
                validated_payload = BoardPayload.model_validate(result.board_update)
                normalized = normalize_and_validate_board(validated_payload)
                final_board = repository.save_board(username, normalized)
                board_updated = True
            except (HTTPException, ValueError) as exc:
                detail = getattr(exc, "detail", str(exc))
                assistant_message = (
                    f"{assistant_message} (I tried to update the board but the change was invalid: {detail})"
                )

        return {
            "assistantMessage": assistant_message,
            "board": final_board,
            "boardUpdated": board_updated,
        }

    if FRONTEND_INDEX_FILE.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_STATIC_DIR, html=True), name="frontend")
    else:

        @app.get("/", response_class=HTMLResponse)
        def home() -> str:
            return FALLBACK_HTML

    return app


app = create_app()
