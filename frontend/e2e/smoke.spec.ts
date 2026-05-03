import { expect, test } from "@playwright/test";

/**
 * Primary route smoke pass.
 *
 * Boots the dev server, opens every primary route, asserts the page returns
 * < 500 and the expected page header renders. Doesn't touch backend-mutating
 * actions, so it's safe to run against a live DB. Pages have empty-state
 * fallbacks for API failure, so the smoke pass works whether the backend is
 * reachable or not.
 */

const ROUTES: { path: string; heading: string }[] = [
  { path: "/", heading: "Today at a glance." },
  { path: "/monitor", heading: "Monitor" },
  { path: "/notes", heading: "Notes" },
  { path: "/data-health", heading: "Data Health" },
  { path: "/settings", heading: "Settings" },

  { path: "/import", heading: "Import a backtest" },
  { path: "/experiments", heading: "Experiments" },
  { path: "/knowledge", heading: "Knowledge Cards" },
  { path: "/research", heading: "Research" },
  { path: "/prompts", heading: "AI Prompts" },

  { path: "/backtests", heading: "Backtests" },
  { path: "/replay", heading: "1m Replay" },
  { path: "/trade-replay", heading: "Tick Replay" },
  { path: "/compare", heading: "Compare runs" },

  { path: "/strategies", heading: "Strategy Catalog" },
  { path: "/risk-profiles", heading: "Risk Profiles" },
  { path: "/strategies/builder", heading: "Strategy Builder" },

  { path: "/prop-firm", heading: "Prop Firm Simulator" },
  { path: "/prop-firm/runs", heading: "Simulation Runs" },
  { path: "/prop-firm/firms", heading: "Firm Rules" },
  { path: "/prop-firm/new", heading: "New simulation" },
];

test.describe("Primary route smoke pass", () => {
  for (const { path, heading } of ROUTES) {
    test(`${path} renders ${JSON.stringify(heading)}`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response?.status() ?? 0).toBeLessThan(500);
      await expect(
        page.getByRole("heading", { level: 1, name: heading }),
      ).toBeVisible();
    });
  }
});

test.describe("Command palette", () => {
  test("Cmd/Ctrl+K opens, typing filters, Enter navigates", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { level: 1, name: "Today at a glance." }),
    ).toBeVisible();

    // Focus the body so the keydown reaches the window-level listener — by
    // default Playwright leaves focus on the URL bar after page.goto.
    await page.locator("body").click({ position: { x: 5, y: 5 } });
    await page.keyboard.press("Control+k");

    const dialog = page.getByRole("dialog", { name: /command palette/i });
    await expect(dialog).toBeVisible();

    const input = dialog.getByLabel(/search commands/i);
    await input.fill("monitor");

    await page.keyboard.press("Enter");

    await expect(page).toHaveURL(/\/monitor$/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Monitor" }),
    ).toBeVisible();
  });

  test("subnav search pill opens the palette", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Search.*jump.*run/i }).click();
    await expect(
      page.getByRole("dialog", { name: /command palette/i }),
    ).toBeVisible();
  });

  test("Escape closes the palette", async ({ page }) => {
    await page.goto("/");
    await page.locator("body").click({ position: { x: 5, y: 5 } });
    await page.keyboard.press("Control+k");
    const dialog = page.getByRole("dialog", { name: /command palette/i });
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });

  test("arrow keys walk the active option", async ({ page }) => {
    await page.goto("/");
    await page.locator("body").click({ position: { x: 5, y: 5 } });
    await page.keyboard.press("Control+k");
    const dialog = page.getByRole("dialog", { name: /command palette/i });
    await expect(dialog).toBeVisible();

    // Type something narrow enough to give a stable, predictable list.
    const input = dialog.getByLabel(/search commands/i);
    await input.fill("re");

    const options = dialog.getByRole("option");
    await expect(options.first()).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("ArrowDown");
    await expect(options.nth(1)).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("ArrowUp");
    await expect(options.first()).toHaveAttribute("aria-selected", "true");
  });
});

test.describe("Backtests deep link", () => {
  test("/backtests?new=1 auto-opens the Run-backtest modal", async ({
    page,
  }) => {
    await page.goto("/backtests?new=1");
    await expect(
      page.getByRole("heading", { level: 1, name: "Backtests" }),
    ).toBeVisible();
    // The modal header has a unique mono eyebrow "engine · synchronous"
    // that doesn't appear elsewhere in the app.
    await expect(page.getByText(/engine\s*·\s*synchronous/i)).toBeVisible();
    // After opening, the page should strip the param.
    await expect(page).toHaveURL(/\/backtests$/);
  });
});
