"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { AISidebar } from "@/components/AISidebar";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, moveCard, type BoardData, type Card } from "@/lib/kanban";
import { fetchBoard, saveBoard } from "@/lib/api";

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const saveTokenRef = useRef(0);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const loadBoard = useCallback(async () => {
    setIsLoading(true);
    setLoadError("");
    try {
      const loadedBoard = await fetchBoard();
      setBoard(loadedBoard);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load board.";
      setLoadError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const persistBoard = useCallback(async (nextBoard: BoardData) => {
    const token = ++saveTokenRef.current;
    setIsSaving(true);
    setSaveError("");
    try {
      const savedBoard = await saveBoard(nextBoard);
      if (token !== saveTokenRef.current) {
        return;
      }
      setBoard(savedBoard);
    } catch (error) {
      if (token !== saveTokenRef.current) {
        return;
      }
      const message = error instanceof Error ? error.message : "Unable to save board.";
      setSaveError(message);
    } finally {
      if (token === saveTokenRef.current) {
        setIsSaving(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

  const applyBoardUpdate = useCallback(
    (updater: (current: BoardData) => BoardData) => {
      setBoard((previous) => {
        if (!previous) {
          return previous;
        }
        const nextBoard = updater(previous);
        void persistBoard(nextBoard);
        return nextBoard;
      });
    },
    [persistBoard]
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    applyBoardUpdate((previous) => ({
      ...previous,
      columns: moveCard(previous.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    applyBoardUpdate((previous) => ({
      ...previous,
      columns: previous.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    applyBoardUpdate((previous) => ({
      ...previous,
      cards: {
        ...previous.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: previous.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    applyBoardUpdate((previous) => {
      return {
        ...previous,
        cards: Object.fromEntries(
          Object.entries(previous.cards).filter(([id]) => id !== cardId)
        ),
        columns: previous.columns.map((column) =>
          column.id === columnId
            ? {
                ...column,
                cardIds: column.cardIds.filter((id) => id !== cardId),
              }
            : column
        ),
      };
    });
  };

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="rounded-2xl border border-(--stroke) bg-white px-6 py-5 shadow-(--shadow)">
          <p className="text-(--gray-text) text-sm font-medium">Loading board...</p>
        </div>
      </main>
    );
  }

  if (!board) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <section className="w-full max-w-md rounded-2xl border border-red-200 bg-red-50 px-6 py-5">
          <p className="text-sm font-semibold text-red-800">Unable to load board.</p>
          <p className="mt-1 text-sm text-red-700">{loadError || "Unknown error."}</p>
          <button
            type="button"
            onClick={() => void loadBoard()}
            className="mt-4 rounded-full bg-(--secondary-purple) px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white"
          >
            Retry
          </button>
        </section>
      </main>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;
  const savingStatusText = isSaving ? "Saving..." : "All changes saved";

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-[0.2em] text-(--gray-text)">
                {savingStatusText}
              </p>
              {saveError ? (
                <p className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  Save failed: {saveError}
                </p>
              ) : null}
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              // Guard against invalid payloads by skipping missing card records.
              // This should not happen with backend validation, but keeps UI resilient.
              // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds
                  .map((cardId) => board.cards[cardId])
                  .filter((card): card is Card => Boolean(card))}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>

      <AISidebar onBoardReplaced={(nextBoard) => setBoard(nextBoard)} />
    </div>
  );
};
