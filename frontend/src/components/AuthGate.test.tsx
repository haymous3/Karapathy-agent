import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AuthGate } from "@/components/AuthGate";
import { initialData } from "@/lib/kanban";

const mockResponse = (status: number, data: unknown): Promise<Response> => {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  } as Response);
};

describe("AuthGate", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows sign in form when user is unauthenticated", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/auth/me")) {
        return mockResponse(401, { detail: "Authentication required" });
      }
      return mockResponse(500, { detail: "Unhandled request in test" });
    });

    render(<AuthGate />);

    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: /sign in/i,
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("allows login and logout with backend auth endpoints", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.endsWith("/api/auth/me")) {
        return mockResponse(401, { detail: "Authentication required" });
      }
      if (url.endsWith("/api/auth/login") && method === "POST") {
        return mockResponse(200, { authenticated: true, username: "user" });
      }
      if (url.endsWith("/api/board") && method === "GET") {
        return mockResponse(200, initialData);
      }
      if (url.endsWith("/api/auth/logout") && method === "POST") {
        return mockResponse(200, { authenticated: false });
      }
      return mockResponse(500, { detail: "Unhandled request in test" });
    });

    const user = userEvent.setup();
    render(<AuthGate />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /log out/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /log out/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    });
  });
});
