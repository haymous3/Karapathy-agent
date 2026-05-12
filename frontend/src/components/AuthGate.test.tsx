import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AuthGate } from "@/components/AuthGate";

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
    fetchMock.mockImplementationOnce(() =>
      mockResponse(401, { detail: "Authentication required" })
    );

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
    fetchMock
      .mockImplementationOnce(() =>
        mockResponse(401, { detail: "Authentication required" })
      )
      .mockImplementationOnce(() => mockResponse(200, { authenticated: true, username: "user" }))
      .mockImplementationOnce(() => mockResponse(200, { authenticated: false }));

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
