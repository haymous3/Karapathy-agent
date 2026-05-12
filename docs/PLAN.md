# PM MVP Execution Plan

## Confirmed Decisions

- Persist Kanban in normalized SQLite tables.
- Use backend-validated login with HTTP-only cookie sessions.
- Use OpenRouter model `openai/gpt-oss-120b`.
- Treat `pm/` as project root for all work.

## Stage-Gate Execution Protocol (User Controlled)

- Work is executed one part at a time (Part 1 -> Part 10).
- At the end of each part, stop and provide a delivery report before any next-step implementation.
- Do not proceed to the next part unless the user explicitly says to continue.

### Delivery Report Required After Each Part

- Scope completed and checklist status.
- Files created/updated.
- Tests run and results (unit/integration/e2e as relevant).
- Review notes (risks, regressions checked, open issues).
- Documentation updates.
- Recommendation for the next part.

## Part 1 - Planning and Working Docs

### Checklist

- [x] Expand this file with detailed substeps for Parts 2-10.
- [x] Add tests and success criteria for every part.
- [x] Create or refresh `pm/frontend/AGENTS.md` with frontend architecture, key modules, and test commands.
- [x] Create or refresh `pm/backend/AGENTS.md` with backend architecture, API boundaries, data layer, and test commands.
- [x] Create or refresh `pm/scripts/AGENTS.md` with script ownership and usage.

### Tests

- [x] Documentation review for internal consistency and sequencing.

### Success Criteria

- Plan is detailed, actionable, and approved by user.
- AGENTS docs for frontend/backend/scripts are clear and current.

Part 1 implementation status: completed by agent, pending user approval.

## Part 2 - Scaffolding (Docker + FastAPI + Scripts)

### Checklist

- [x] Scaffold FastAPI backend in `pm/backend`.
- [x] Add Python dependency management using `uv`.
- [x] Add `pm/Dockerfile` to run backend in container.
- [x] Add start/stop scripts for Windows/macOS/Linux in `pm/scripts`.
- [x] Serve example static HTML at `/` and API hello endpoint.

### Tests

- [x] Container boots successfully.
- [x] `GET /health` returns 200.
- [x] `GET /api/hello` returns expected JSON.

### Success Criteria

- One documented workflow starts and stops the app locally.
- Backend static + API routes are both working.

Part 2 implementation status: completed by agent, pending user approval.

## Part 3 - Frontend Static Build Served at `/`

### Checklist

- [x] Configure `pm/frontend/next.config.ts` for static export.
- [x] Build frontend static output in Docker flow.
- [x] Serve static frontend from FastAPI at `/`.
- [x] Preserve backend API namespace (`/api/*`).

### Tests

- [x] Frontend unit tests pass.
- [x] Frontend e2e smoke passes against served app.
- [x] Backend API routes remain reachable.

### Success Criteria

- Existing Kanban UI loads from FastAPI-hosted static site at `/`.

Part 3 implementation status: completed by agent, pending user approval.

## Part 4 - Dummy Sign In/Out (Cookie Session)

### Checklist

- [x] Add auth endpoints (`/api/auth/login`, `/api/auth/logout`, `/api/auth/me`).
- [x] Validate hardcoded credentials (`user`, `password`) on backend.
- [x] Set and clear HTTP-only session cookie.
- [x] Add frontend login gate and logout flow.

### Tests

- [x] Backend auth success/failure tests.
- [x] Protected-route unauthorized tests.
- [x] Frontend login/logout tests and e2e flow.

### Success Criteria

- Unauthenticated users cannot access protected board flows.
- Authenticated users can log in, use board, and log out.

Part 4 implementation status: completed by agent, pending user approval.

## Part 5 - Database Modeling and Documentation

### Checklist

- [x] Write schema proposal doc in `pm/docs`.
- [x] Define normalized tables (`users`, `boards`, `columns`, `cards`, ordering metadata, optional chat history).
- [x] Define indexes, constraints, and create-if-missing approach.
- [x] Define mapping between frontend board JSON shape and relational schema.
- [x] Get user sign-off before implementing DB CRUD layer.

### Tests

- [x] Validate schema DDL by creating empty SQLite DB.
- [x] Validate round-trip mapping spec with example payload.

### Success Criteria

- Approved schema doc supports implementation without redesign.

Part 5 implementation status: completed by agent, pending user sign-off.

## Part 6 - Backend Kanban CRUD + DB Auto-Creation

### Checklist

- [x] Implement startup DB initialization.
- [x] Add authenticated Kanban read/write endpoints.
- [x] Implement repository/service mapping relational data to board shape.
- [x] Seed default board for first-time user.

### Tests

- [x] Backend unit tests for repository/service logic.
- [x] API tests for CRUD and per-user isolation.

### Success Criteria

- Board data persists across restart.
- User data is isolated correctly.

Part 6 implementation status: completed by agent, pending user approval.

## Part 7 - Frontend + Backend Integration

### Checklist

- [ ] Replace in-memory-only board lifecycle with API-backed load/save.
- [ ] Add frontend API client helpers.
- [ ] Add loading/error states for fetch/mutation.

### Tests

- [ ] Frontend unit/integration tests with mocked API responses.
- [ ] E2E persistence test across refresh.

### Success Criteria

- Board changes persist and reload reliably from backend.

## Part 8 - OpenRouter Connectivity

### Checklist

- [ ] Add backend OpenRouter client using `OPENROUTER_API_KEY`.
- [ ] Set model to `openai/gpt-oss-120b`.
- [ ] Add simple AI connectivity path (`2+2` probe).

### Tests

- [ ] Integration test with mocked provider response.
- [ ] Optional guarded live smoke test.

### Success Criteria

- Backend can call OpenRouter successfully.

## Part 9 - Structured AI Outputs with Optional Kanban Update

### Checklist

- [ ] Send board JSON + conversation history + user prompt to AI route.
- [ ] Define strict response schema (`assistantMessage`, optional board update payload).
- [ ] Validate response server-side before applying updates.
- [ ] Apply accepted updates transactionally and return updated board.

### Tests

- [ ] Schema validation tests for valid/invalid AI payloads.
- [ ] Integration tests for message-only and message+board-update cases.

### Success Criteria

- AI responses are parseable, safe, and deterministic in API contract.

## Part 10 - AI Sidebar UI and Auto-Refresh

### Checklist

- [ ] Build sidebar chat UI in frontend.
- [ ] Submit chat messages to backend AI endpoint.
- [ ] Apply board updates returned by AI and refresh board state automatically.
- [ ] Add clear loading/error states.

### Tests

- [ ] Frontend tests for chat rendering/submission.
- [ ] E2E flow where AI response updates the board.

### Success Criteria

- User can chat with AI and see board updates reflected in UI automatically.

## Cross-Cutting Quality Gates

- [ ] Keep implementation simple; avoid over-engineering.
- [ ] Follow coding standards in `pm/AGENTS.md`.
- [ ] Run relevant lint/unit/integration/e2e tests before closing each part.
- [ ] Keep docs in `pm/docs` and all AGENTS files updated when behavior changes.
- [ ] Aim for about 80% test coverage only when sensible; prioritize valuable tests over coverage chasing. It is acceptable to be below 80% if additional tests would be low value.