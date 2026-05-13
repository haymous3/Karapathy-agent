import type { BoardData } from "@/lib/kanban";

const BOARD_ENDPOINT = "/api/board";
const CHAT_ENDPOINT = "/api/ai/chat";

const parseError = async (response: Response): Promise<string> => {
  try {
    const data = (await response.json()) as { detail?: string };
    return data.detail ?? `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
};

export const fetchBoard = async (): Promise<BoardData> => {
  const response = await fetch(BOARD_ENDPOINT, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as BoardData;
};

export const saveBoard = async (board: BoardData): Promise<BoardData> => {
  const response = await fetch(BOARD_ENDPOINT, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(board),
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as BoardData;
};

export type ChatRole = "user" | "assistant";

export type ChatHistoryMessage = {
  role: ChatRole;
  content: string;
};

export type ChatResponse = {
  assistantMessage: string;
  board: BoardData;
  boardUpdated: boolean;
};

export const sendChatMessage = async (
  message: string,
  history: ChatHistoryMessage[]
): Promise<ChatResponse> => {
  const response = await fetch(CHAT_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as ChatResponse;
};
