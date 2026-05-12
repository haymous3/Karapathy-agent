# Backend Agent Guide

## Purpose

`pm/backend` will host the FastAPI service for:

- authentication (dummy credentials for MVP)
- Kanban CRUD APIs
- SQLite persistence with auto-create behavior
- OpenRouter AI integration
- serving static frontend build at `/` from `backend/static` (after frontend export)

## Planned Backend Responsibilities by Part

- Part 2: FastAPI scaffold, health route, hello API route, static hello page
- Part 3: Docker multi-stage build exports Next static assets and serves them at `/` while preserving `/api/*`
- Part 4: login/logout/session endpoints with HTTP-only cookie
- Part 6: board persistence and CRUD APIs in SQLite
- Part 8: OpenRouter connectivity endpoint
- Part 9: structured AI response endpoint with optional board updates

Current auth endpoints:

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

Current board endpoints:

- `GET /api/board`
- `PUT /api/board`

## Intended Project Layout

The backend layout should stay simple and predictable. Target structure:

- `backend/app/main.py` (FastAPI app bootstrap)
- `backend/app/api/` (route modules)
- `backend/app/core/` (settings, auth/session helpers)
- `backend/app/db/` (SQLite init and data access)
- `backend/app/services/` (Kanban + AI business logic)
- `backend/tests/` (unit/integration API tests)

Adjust names if needed, but keep a clear separation between API, data, and service logic.

## Backend Engineering Rules

- Keep code straightforward and MVP-focused.
- Always validate auth before protected board operations.
- Use create-if-missing DB initialization at startup.
- Keep data mapping deterministic (DB <-> API model).
- Validate AI structured outputs before mutating board data.
- Use transactions for multi-table board updates.

## Test Expectations

Current local run command:

- `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` (from `pm/backend`)

When backend code exists, run from `pm` or backend root:

- unit tests for service/repository logic
- API integration tests for auth + board routes
- schema/init tests for DB auto-create behavior

Current schema path and DB path:

- runtime schema: `backend/app/schema.sql` (derived from `docs/kanban_schema.sql`)
- default DB: `backend/data/pm_mvp.sqlite3`

Document exact commands in this file once test tooling is scaffolded.

## Definition of Done for Backend Tasks

- New endpoints include tests for happy path and key failure paths.
- Auth and data isolation behavior are verified.
- DB initialization and migrations (if any) are reproducible.
- AI paths are validated for malformed output handling.