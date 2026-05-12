import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

const mockResponse = (status: number, data: unknown): Promise<Response> =>
  Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  } as Response);

describe("KanbanBoard", () => {
  let boardState: BoardData;
  const fetchMock = vi.fn();

  beforeEach(() => {
    boardState = structuredClone(initialData);
    fetchMock.mockReset();
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.endsWith("/api/board") && method === "GET") {
        return mockResponse(200, boardState);
      }
      if (url.endsWith("/api/board") && method === "PUT") {
        boardState = JSON.parse(String(init?.body)) as BoardData;
        return mockResponse(200, boardState);
      }
      return mockResponse(500, { detail: "Unhandled test request" });
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders fetched board data", async () => {
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({ method: "GET", credentials: "include" })
    );
  });

  it("saves board changes after card add and delete", async () => {
    const user = userEvent.setup();
    render(<KanbanBoard />);

    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });

    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await user.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await user.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await user.type(detailsInput, "Notes");

    await user.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await user.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/board",
        expect.objectContaining({ method: "PUT", credentials: "include" })
      );
    });
  });

  it("shows load error and supports retry", async () => {
    fetchMock.mockReset();
    fetchMock
      .mockImplementationOnce(() => mockResponse(500, { detail: "boom" }))
      .mockImplementation(() => mockResponse(200, boardState));

    const user = userEvent.setup();
    render(<KanbanBoard />);

    await waitFor(() => {
      expect(screen.getByText(/unable to load board/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });
  });
});
