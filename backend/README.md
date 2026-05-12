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
