import { expect, test, type Page, type Route } from "@playwright/test";

const loginAsDefaultUser = async (page: Page) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
};

test("AI sidebar sends a chat message and renders the assistant reply", async ({
  page,
}) => {
  await page.route("**/api/ai/chat", async (route: Route) => {
    const request = route.request();
    const body = request.postDataJSON() as { message: string };
    expect(body.message).toBe("Just say hi.");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assistantMessage: "Hi there, ready when you are.",
        board: await page
          .request.get("/api/board")
          .then((response) => response.json()),
        boardUpdated: false,
      }),
    });
  });

  await loginAsDefaultUser(page);

  const sidebar = page.getByTestId("ai-sidebar");
  await expect(sidebar).toBeVisible();

  await sidebar
    .getByLabel(/message the ai assistant/i)
    .fill("Just say hi.");
  await sidebar.getByRole("button", { name: /^send$/i }).click();

  await expect(
    sidebar.getByText(/hi there, ready when you are\./i)
  ).toBeVisible();
});

test("AI sidebar applies a board update returned by the AI", async ({ page }) => {
  await loginAsDefaultUser(page);

  const currentBoard = await page.request.get("/api/board").then((response) => response.json());
  const uniqueTitle = `AI-${Date.now()}`;
  const newCardId = `card-ai-${Date.now()}`;
  const updatedBoard = {
    columns: currentBoard.columns.map((column: { id: string; cardIds: string[] }) =>
      column.id === currentBoard.columns[0].id
        ? { ...column, cardIds: [...column.cardIds, newCardId] }
        : column
    ),
    cards: {
      ...currentBoard.cards,
      [newCardId]: {
        id: newCardId,
        title: uniqueTitle,
        details: "Added by the AI assistant.",
      },
    },
  };

  await page.route("**/api/ai/chat", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assistantMessage: `Added '${uniqueTitle}' to the first column.`,
        board: updatedBoard,
        boardUpdated: true,
      }),
    });
  });

  const sidebar = page.getByTestId("ai-sidebar");
  await sidebar
    .getByLabel(/message the ai assistant/i)
    .fill(`Add a card titled '${uniqueTitle}'.`);
  await sidebar.getByRole("button", { name: /^send$/i }).click();

  await expect(sidebar.getByText(/board updated/i)).toBeVisible();

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await expect(firstColumn.getByText(uniqueTitle)).toBeVisible();
});

test("AI sidebar shows an error when the AI endpoint fails", async ({ page }) => {
  await page.route("**/api/ai/chat", async (route: Route) => {
    await route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({ detail: "AI provider unreachable" }),
    });
  });

  await loginAsDefaultUser(page);

  const sidebar = page.getByTestId("ai-sidebar");
  await sidebar.getByLabel(/message the ai assistant/i).fill("Hello?");
  await sidebar.getByRole("button", { name: /^send$/i }).click();

  await expect(sidebar.getByRole("alert")).toContainText(
    /ai provider unreachable/i
  );
});
