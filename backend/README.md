# PM Backend

FastAPI backend scaffold for the PM MVP.

## Run locally with uv

```bash
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Endpoints

- `GET /` serves exported frontend (or fallback static hello page if export is absent)
- `GET /health` health probe
- `GET /api/hello` hello API response
- `POST /api/auth/login` login with demo credentials (`user` / `password`)
- `POST /api/auth/logout` clear session
- `GET /api/auth/me` return session user or `401`
- `GET /api/board` return authenticated user's board
- `PUT /api/board` replace authenticated user's board (validated payload)

## Database

- SQLite file default: `backend/data/pm_mvp.sqlite3`
- Runtime schema file: `backend/app/schema.sql` (kept aligned with `docs/kanban_schema.sql`)
- Startup behavior: create DB + tables if missing, ensure user board, seed default board if empty
