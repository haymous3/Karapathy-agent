"use client";

import { FormEvent, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthMeResponse = {
  authenticated: true;
  username: string;
};

type LoginResponse = {
  authenticated: true;
  username: string;
};

const initialCredentials = {
  username: "user",
  password: "password",
};

export const AuthGate = () => {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [username, setUsername] = useState("");
  const [credentials, setCredentials] = useState(initialCredentials);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    void checkSession();
  }, []);

  const checkSession = async () => {
    try {
      const response = await fetch("/api/auth/me", { credentials: "include" });
      if (!response.ok) {
        setStatus("unauthenticated");
        return;
      }

      const data = (await response.json()) as AuthMeResponse;
      setUsername(data.username);
      setStatus("authenticated");
    } catch {
      setError("Unable to reach server. Check if the backend is running.");
      setStatus("unauthenticated");
    }
  };

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        setError("Invalid username or password.");
        setStatus("unauthenticated");
        return;
      }

      const data = (await response.json()) as LoginResponse;
      setUsername(data.username);
      setStatus("authenticated");
    } catch {
      setError("Login failed. Try again.");
      setStatus("unauthenticated");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setError("");
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Keep logout flow simple for MVP: clear local auth state even on network errors.
    } finally {
      setUsername("");
      setStatus("unauthenticated");
    }
  };

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="rounded-2xl border border-(--stroke) bg-white px-6 py-5 shadow-(--shadow)">
          <p className="text-(--gray-text) text-sm font-medium">Checking session...</p>
        </div>
      </main>
    );
  }

  if (status === "authenticated") {
    return (
      <div className="relative">
        <div className="pointer-events-none fixed right-5 top-5 z-50 rounded-2xl border border-(--stroke) bg-white/85 px-4 py-3 shadow-(--shadow) backdrop-blur">
          <div className="pointer-events-auto flex items-center gap-3">
            <p className="text-(--gray-text) text-xs font-semibold uppercase tracking-[0.15em]">
              Signed in as {username}
            </p>
            <button
              type="button"
              onClick={handleLogout}
              className="bg-(--secondary-purple) rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
            >
              Log out
            </button>
          </div>
        </div>
        <KanbanBoard />
      </div>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <section className="w-full max-w-md rounded-3xl border border-(--stroke) bg-white p-8 shadow-(--shadow)">
        <p className="text-(--gray-text) text-xs font-semibold uppercase tracking-[0.35em]">PM MVP</p>
        <h1 className="text-foreground mt-3 font-display text-3xl font-semibold">Sign in</h1>
        <p className="text-(--gray-text) mt-2 text-sm">
          Use the demo credentials to access the Kanban board.
        </p>
        <p className="bg-background text-(--gray-text) mt-2 rounded-lg px-3 py-2 text-xs">
          Username: <strong>user</strong> | Password: <strong>password</strong>
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleLogin}>
          <label className="text-foreground flex flex-col gap-1.5 text-sm font-medium">
            Username
            <input
              value={credentials.username}
              onChange={(event) =>
                setCredentials((prev) => ({
                  ...prev,
                  username: event.target.value,
                }))
              }
              autoComplete="username"
              className="rounded-xl border border-(--stroke) px-3 py-2 text-sm outline-none transition focus:border-(--primary-blue)"
            />
          </label>

          <label className="text-foreground flex flex-col gap-1.5 text-sm font-medium">
            Password
            <input
              type="password"
              value={credentials.password}
              onChange={(event) =>
                setCredentials((prev) => ({
                  ...prev,
                  password: event.target.value,
                }))
              }
              autoComplete="current-password"
              className="rounded-xl border border-(--stroke) px-3 py-2 text-sm outline-none transition focus:border-(--primary-blue)"
            />
          </label>

          {error ? (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="bg-(--secondary-purple) w-full rounded-full px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
};
