import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="PM MVP Backend", version="0.1.0")
FRONTEND_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
FRONTEND_INDEX_FILE = FRONTEND_STATIC_DIR / "index.html"
VALID_USERNAME = "user"
VALID_PASSWORD = "password"
SESSION_AUTH_KEY = "authenticated"
SESSION_USER_KEY = "username"

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-me-for-production"),
    session_cookie="pm_session",
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 12,
)

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


def require_authenticated_username(request: Request) -> str:
    if not request.session.get(SESSION_AUTH_KEY):
        raise HTTPException(status_code=401, detail="Authentication required")
    username = request.session.get(SESSION_USER_KEY)
    if username != VALID_USERNAME:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Invalid session")
    return username


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


if FRONTEND_INDEX_FILE.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_STATIC_DIR, html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return FALLBACK_HTML
