# Frontend Agent Guide

## Purpose

`pm/frontend` contains the Next.js Kanban UI. Right now it is a frontend-only demo with local in-memory state. Upcoming parts will connect it to the FastAPI backend and AI chat API while preserving current UX quality.

## Current Stack

- Next.js 16 (App Router) + React 19 + TypeScript
- Tailwind CSS 4 for styling
- `@dnd-kit` for drag and drop
- Vitest + Testing Library for unit/component tests
- Playwright for e2e tests

## Current Architecture

- Entry route:
  - `src/app/page.tsx` renders `AuthGate` (login gate + session check)
- Global layout/theme:
  - `src/app/layout.tsx`, `src/app/globals.css`
- Auth and session-aware UI:
  - `src/components/AuthGate.tsx`
- Board state and logic:
  - `src/components/KanbanBoard.tsx` owns board state and handlers, mounts the AI sidebar below the grid
  - board loads/saves through backend API with minimal loading/error/saving UI
  - `src/lib/api.ts` contains API helpers (`fetchBoard`, `saveBoard`, `sendChatMessage`)
  - `src/lib/kanban.ts` defines data model (`BoardData`, `Column`, `Card`) and move utilities
- Column/Card UI:
  - `src/components/KanbanColumn.tsx`
  - `src/components/KanbanCard.tsx`
  - `src/components/NewCardForm.tsx`
  - `src/components/KanbanCardPreview.tsx`
- AI chat sidebar:
  - `src/components/AISidebar.tsx` renders the chat list, composer, and applies AI-proposed board updates via the `onBoardReplaced` callback (no extra `GET /api/board` needed)
  - Chat history is stateless: last 16 turns are sent with each request
  - Rendered below the kanban grid (full-width, glass card aesthetic). Side-by-side fixed/sticky layouts were tried but broke dnd-kit drag-and-drop pointer detection.

## Test Commands

Run from `pm/frontend`:

```bash
npm install
npm run lint
npm run test:unit
npm run test:e2e
```

Optional all-in-one:

```bash
npm run test:all
```

Container-served e2e smoke (no local Next dev server):

```bash
PLAYWRIGHT_EXTERNAL_URL=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:8001 npx playwright test tests/kanban.spec.ts --grep "loads the kanban board"
```

PowerShell equivalent:

```powershell
$env:PLAYWRIGHT_EXTERNAL_URL="1"
$env:PLAYWRIGHT_BASE_URL="http://127.0.0.1:8001"
npx playwright test tests/kanban.spec.ts --grep "loads the kanban board"
```

## Frontend Change Rules

- Keep UX simple and readable; do not add speculative features.
- Preserve existing visual palette and design language from root `pm/AGENTS.md`.
- Prefer small, composable components over large monoliths.
- Keep board domain model aligned with backend API contract once integration starts.
- For API integration, separate fetch/client helpers from presentation components.
- For auth gating, keep login flow explicit and easy to test.

## Definition of Done for Frontend Tasks

- Lint passes.
- Relevant unit/component tests pass.
- Relevant e2e paths pass or are updated with clear rationale.
- Any user-visible behavior change is documented in `pm/docs/PLAN.md` delivery report.
