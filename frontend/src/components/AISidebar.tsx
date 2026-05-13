"use client";

import {
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import clsx from "clsx";
import {
  sendChatMessage,
  type ChatHistoryMessage,
  type ChatRole,
} from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type DisplayMessage = {
  id: string;
  role: ChatRole;
  content: string;
};

type AISidebarProps = {
  onBoardReplaced: (board: BoardData) => void;
};

const MAX_HISTORY_MESSAGES = 16;

const createMessageId = () =>
  `msg-${Math.random().toString(36).slice(2, 8)}${Date.now().toString(36)}`;

const SUGGESTED_PROMPTS = [
  "Summarize what is in progress.",
  "Add a card titled 'Plan launch checklist' to Backlog.",
  "Move 'Design card layout' to Review.",
];

export const AISidebar = ({ onBoardReplaced }: AISidebarProps) => {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [boardUpdateNoticeId, setBoardUpdateNoticeId] = useState<string | null>(
    null
  );
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const historyForApi = useMemo<ChatHistoryMessage[]>(() => {
    return messages
      .slice(-MAX_HISTORY_MESSAGES)
      .map((message) => ({ role: message.role, content: message.content }));
  }, [messages]);

  useEffect(() => {
    if (messages.length === 0) {
      return;
    }
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [messages, isSending]);

  const submitMessage = useCallback(
    async (rawMessage: string) => {
      const trimmed = rawMessage.trim();
      if (!trimmed || isSending) {
        return;
      }

      const userMessage: DisplayMessage = {
        id: createMessageId(),
        role: "user",
        content: trimmed,
      };
      setMessages((previous) => [...previous, userMessage]);
      setDraft("");
      setError("");
      setIsSending(true);

      try {
        const response = await sendChatMessage(trimmed, historyForApi);
        const assistantMessage: DisplayMessage = {
          id: createMessageId(),
          role: "assistant",
          content: response.assistantMessage,
        };
        setMessages((previous) => [...previous, assistantMessage]);
        if (response.boardUpdated) {
          onBoardReplaced(response.board);
          setBoardUpdateNoticeId(assistantMessage.id);
        }
      } catch (caughtError) {
        const message =
          caughtError instanceof Error
            ? caughtError.message
            : "Something went wrong contacting the AI.";
        setError(message);
      } finally {
        setIsSending(false);
      }
    },
    [historyForApi, isSending, onBoardReplaced]
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submitMessage(draft);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitMessage(draft);
    }
  };

  return (
    <aside
      aria-label="AI assistant"
      data-testid="ai-sidebar"
      className="relative z-30 mx-auto flex w-full max-w-[1500px] flex-col gap-0 border-t border-[var(--stroke)] bg-white/85 shadow-[var(--shadow)] backdrop-blur"
    >
      <header className="flex flex-col gap-2 border-b border-[var(--stroke)] px-6 pb-4 pt-6">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-[var(--accent-yellow)]" />
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            AI Assistant
          </p>
        </div>
        <h2 className="font-display text-2xl font-semibold text-[var(--navy-dark)]">
          Plan with intent
        </h2>
        <p className="text-sm leading-6 text-[var(--gray-text)]">
          Ask for board changes in plain language. The assistant can add, move,
          and edit cards across columns.
        </p>
      </header>

      <div
        className="flex flex-1 flex-col gap-3 overflow-y-auto px-6 py-4"
        data-testid="ai-message-list"
      >
        {messages.length === 0 ? (
          <div className="flex flex-col gap-3 rounded-2xl border border-dashed border-[var(--stroke)] bg-[var(--surface)] px-4 py-5">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Try a prompt
            </p>
            <div className="flex flex-col gap-2">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void submitMessage(prompt)}
                  disabled={isSending}
                  className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-left text-sm text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message) => {
          const isAssistant = message.role === "assistant";
          const showBoardUpdated =
            isAssistant && boardUpdateNoticeId === message.id;
          return (
            <div
              key={message.id}
              className={clsx(
                "flex flex-col",
                isAssistant ? "items-start" : "items-end"
              )}
              data-testid={`ai-message-${message.role}`}
            >
              <div
                className={clsx(
                  "max-w-[90%] rounded-2xl border px-4 py-3 text-sm leading-6 shadow-[0_6px_18px_rgba(3,33,71,0.08)]",
                  isAssistant
                    ? "rounded-bl-sm border-[var(--stroke)] bg-gradient-to-br from-[rgba(32,157,215,0.08)] via-white to-white text-[var(--navy-dark)]"
                    : "rounded-br-sm border-transparent bg-[var(--secondary-purple)] text-white"
                )}
              >
                {message.content}
              </div>
              {showBoardUpdated ? (
                <span className="mt-1 inline-flex items-center gap-1.5 rounded-full bg-[var(--accent-yellow)]/15 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent-yellow)]" />
                  Board updated
                </span>
              ) : null}
            </div>
          );
        })}

        {isSending ? (
          <div
            className="flex items-center gap-1.5 self-start rounded-2xl rounded-bl-sm border border-[var(--stroke)] bg-white px-4 py-3"
            data-testid="ai-typing-indicator"
            aria-live="polite"
          >
            <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--primary-blue)] [animation-delay:-0.2s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--primary-blue)] [animation-delay:-0.1s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--primary-blue)]" />
          </div>
        ) : null}

        {error ? (
          <p
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {error}
          </p>
        ) : null}

        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-3 border-t border-[var(--stroke)] bg-white/70 px-6 py-4 backdrop-blur"
      >
        <label className="sr-only" htmlFor="ai-message-input">
          Message the AI assistant
        </label>
        <textarea
          id="ai-message-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask the AI to update your board..."
          rows={2}
          className="w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm leading-6 outline-none transition focus:border-[var(--primary-blue)]"
          disabled={isSending}
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Enter to send | Shift+Enter for newline
          </p>
          <button
            type="submit"
            disabled={isSending || draft.trim().length === 0}
            className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSending ? "Sending..." : "Send"}
          </button>
        </div>
      </form>
    </aside>
  );
};
