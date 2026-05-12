# Part 5: SQLite Schema Proposal (Normalized)

## Goal

Define a normalized SQLite schema that supports:

- one user per login identity (MVP credential is still hardcoded at runtime)
- exactly one board per user for MVP
- ordered columns and ordered cards
- mapping to frontend `BoardData` from `frontend/src/lib/kanban.ts`
- optional chat history persistence for Parts 9-10

This proposal is designed to be implemented in Part 6 without redesign.

## Schema Files

- SQL DDL: `docs/kanban_schema.sql`

## Proposed Tables

### `users`

- `id` integer PK
- `username` unique, not null
- `created_at`

Why: future multi-user support with simple lookup.

### `boards`

- `id` integer PK
- `user_id` unique FK -> `users.id`
- `name`
- `created_at`, `updated_at`

Why: enforces one board per user in MVP via `UNIQUE(user_id)`.

### `board_columns`

- `id` integer PK
- `board_id` FK -> `boards.id`
- `external_id` text (frontend-facing stable id, e.g. `col-backlog`)
- `title`
- `position` integer for deterministic ordering
- timestamps
- unique constraints:
  - `(board_id, external_id)`
  - `(board_id, position)`

Why: normalized column records with reliable order and board-level uniqueness.

### `cards`

- `id` integer PK
- `board_id` FK -> `boards.id`
- `column_id` FK -> `board_columns.id`
- `external_id` text (frontend-facing id, e.g. `card-1`)
- `title`, `details`
- `position` integer for order inside column
- timestamps
- unique constraints:
  - `(board_id, external_id)`
  - `(column_id, position)`

Why: cards are normalized and linked to both board and current column; order is explicit.

### `chat_messages` (optional but included now)

- `id` integer PK
- `board_id` FK -> `boards.id`
- `role` constrained to `system|user|assistant`
- `content`
- `created_at`

Why: lightweight persistence for conversation context in later AI parts.

## Indexes

From `docs/kanban_schema.sql`:

- `idx_board_columns_board_id`
- `idx_cards_board_id`
- `idx_cards_column_id`
- `idx_chat_messages_board_id_id`

These support common board-load and message history queries.

## Create-if-missing Strategy (for Part 6)

On backend startup:

1. Ensure DB directory exists (`backend/data/`).
2. Open SQLite connection to `backend/data/pm_mvp.sqlite3`.
3. Enable FK enforcement: `PRAGMA foreign_keys = ON`.
4. Execute schema script `docs/kanban_schema.sql` (all `CREATE ... IF NOT EXISTS`).
5. Ensure MVP user row exists for username `user`.
6. Ensure one board exists for that user.
7. If no columns/cards exist for the board, seed from `initialData`.

This keeps startup idempotent and safe on repeated runs.

## Mapping: Relational <-> Frontend `BoardData`

Frontend type target:

```ts
type BoardData = {
  columns: { id: string; title: string; cardIds: string[] }[];
  cards: Record<string, { id: string; title: string; details: string }>;
};
```

### Load DB -> `BoardData`

1. Query columns for board ordered by `position ASC`.
2. Query cards for board ordered by `(column position, card position)`.
3. Build:
   - `columns[*].id = board_columns.external_id`
   - `columns[*].cardIds[] = cards.external_id` in card position order
   - `cards[external_id] = { id: external_id, title, details }`

### Save `BoardData` -> DB

Run in one transaction:

1. Upsert columns by `(board_id, external_id)` with title + position from array order.
2. Delete board columns no longer present (cascade removes orphan cards).
3. Resolve `column_id` map from column `external_id`.
4. Upsert cards by `(board_id, external_id)` with `column_id`, title, details, and position from `cardIds` order.
5. Delete cards no longer present in payload.
6. Update `boards.updated_at`.

## Round-Trip Example

Input frontend payload (shape):

```json
{
  "columns": [
    { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"] },
    { "id": "col-done", "title": "Done", "cardIds": ["card-2"] }
  ],
  "cards": {
    "card-1": { "id": "card-1", "title": "A", "details": "A details" },
    "card-2": { "id": "card-2", "title": "B", "details": "B details" }
  }
}
```

After saving to relational rows and reloading via the load algorithm above, the reconstructed payload should preserve:

- same column order
- same card order in each column
- same card ids/title/details

## Validation Performed in Part 5

1. DDL validation: create an empty SQLite DB and apply `docs/kanban_schema.sql`.
2. Round-trip validation: insert sample board/columns/cards, then reconstruct `BoardData` and verify order/content.

Validation commands and outcomes are reported in the Part 5 delivery report.
