import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AISidebar } from "@/components/AISidebar";
import { initialData, type BoardData } from "@/lib/kanban";

const mockResponse = (status: number, data: unknown): Promise<Response> =>
  Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  } as Response);

describe("AISidebar", () => {
  const fetchMock = vi.fn();
  const onBoardReplaced = vi.fn<(board: BoardData) => void>();

  beforeEach(() => {
    fetchMock.mockReset();
    onBoardReplaced.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders suggested prompts before the user sends anything", () => {
    render(<AISidebar onBoardReplaced={onBoardReplaced} />);
    expect(screen.getByText(/try a prompt/i)).toBeInTheDocument();
    expect(screen.getByText(/summarize what is in progress/i)).toBeInTheDocument();
  });

  it("sends the message and renders the assistant reply", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.endsWith("/api/ai/chat") && method === "POST") {
        const body = JSON.parse(String(init?.body)) as {
          message: string;
          history: { role: string; content: string }[];
        };
        expect(body.message).toBe("Hello AI");
        expect(body.history).toEqual([]);
        return mockResponse(200, {
          assistantMessage: "Hi there",
          board: initialData,
          boardUpdated: false,
        });
      }
      return mockResponse(500, { detail: "Unhandled request" });
    });

    const user = userEvent.setup();
    render(<AISidebar onBoardReplaced={onBoardReplaced} />);

    const textarea = screen.getByLabelText(/message the ai assistant/i);
    await user.type(textarea, "Hello AI");
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    await waitFor(() => {
      expect(screen.getByTestId("ai-message-assistant")).toHaveTextContent(
        "Hi there"
      );
    });
    expect(screen.getByTestId("ai-message-user")).toHaveTextContent("Hello AI");
    expect(onBoardReplaced).not.toHaveBeenCalled();
    expect(screen.queryByText(/board updated/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/try a prompt/i)).not.toBeInTheDocument();
  });

  it("applies a board update and shows the board updated badge", async () => {
    const updatedBoard: BoardData = structuredClone(initialData);
    updatedBoard.columns[0].cardIds.push("card-new");
    updatedBoard.cards["card-new"] = {
      id: "card-new",
      title: "New task",
      details: "Added by AI",
    };

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/ai/chat")) {
        return mockResponse(200, {
          assistantMessage: "Added the new card.",
          board: updatedBoard,
          boardUpdated: true,
        });
      }
      return mockResponse(500, { detail: "Unhandled request" });
    });

    const user = userEvent.setup();
    render(<AISidebar onBoardReplaced={onBoardReplaced} />);

    await user.type(
      screen.getByLabelText(/message the ai assistant/i),
      "Add a new card"
    );
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    await waitFor(() => {
      expect(onBoardReplaced).toHaveBeenCalledWith(updatedBoard);
    });
    expect(screen.getByText(/board updated/i)).toBeInTheDocument();
  });

  it("submits on Enter and adds newline on Shift+Enter", async () => {
    fetchMock.mockImplementation(() =>
      mockResponse(200, {
        assistantMessage: "ack",
        board: initialData,
        boardUpdated: false,
      })
    );

    const user = userEvent.setup();
    render(<AISidebar onBoardReplaced={onBoardReplaced} />);

    const textarea = screen.getByLabelText(
      /message the ai assistant/i
    ) as HTMLTextAreaElement;
    await user.type(textarea, "line one{Shift>}{Enter}{/Shift}line two");
    expect(textarea.value).toBe("line one\nline two");

    await user.type(textarea, "{Enter}");

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/ai/chat",
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  it("shows an error message when the request fails", async () => {
    fetchMock.mockImplementation(() =>
      mockResponse(502, { detail: "AI service unavailable" })
    );

    const user = userEvent.setup();
    render(<AISidebar onBoardReplaced={onBoardReplaced} />);

    await user.type(
      screen.getByLabelText(/message the ai assistant/i),
      "Hello"
    );
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /ai service unavailable/i
      );
    });
  });

  it("sends a suggested prompt when one is clicked", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/ai/chat")) {
        const body = JSON.parse(String(init?.body)) as { message: string };
        expect(body.message).toBe("Summarize what is in progress.");
        return mockResponse(200, {
          assistantMessage: "Three cards in progress.",
          board: initialData,
          boardUpdated: false,
        });
      }
      return mockResponse(500, { detail: "Unhandled request" });
    });

    const user = userEvent.setup();
    render(<AISidebar onBoardReplaced={onBoardReplaced} />);

    await user.click(
      screen.getByRole("button", { name: /summarize what is in progress/i })
    );

    await waitFor(() => {
      const list = screen.getByTestId("ai-message-list");
      expect(
        within(list).getByText("Three cards in progress.")
      ).toBeInTheDocument();
    });
  });

  it("sends prior turns as history on the next message", async () => {
    fetchMock
      .mockImplementationOnce(() =>
        mockResponse(200, {
          assistantMessage: "First reply",
          board: initialData,
          boardUpdated: false,
        })
      )
      .mockImplementationOnce((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        expect(url).toMatch(/\/api\/ai\/chat$/);
        const body = JSON.parse(String(init?.body)) as {
          message: string;
          history: { role: string; content: string }[];
        };
        expect(body.message).toBe("Second question");
        expect(body.history).toEqual([
          { role: "user", content: "First question" },
          { role: "assistant", content: "First reply" },
        ]);
        return mockResponse(200, {
          assistantMessage: "Second reply",
          board: initialData,
          boardUpdated: false,
        });
      });

    const user = userEvent.setup();
    render(<AISidebar onBoardReplaced={onBoardReplaced} />);

    const textarea = screen.getByLabelText(/message the ai assistant/i);
    await user.type(textarea, "First question");
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() => expect(screen.getByText("First reply")).toBeInTheDocument());

    await user.type(textarea, "Second question");
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() => expect(screen.getByText("Second reply")).toBeInTheDocument());

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
