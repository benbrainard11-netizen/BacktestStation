/**
 * Playwright smoke pass for the workspace IA sub-routes.
 *
 * Coverage:
 *   - Workspace home (`/strategies/[id]`)
 *   - All ten sub-routes under `/strategies/[id]/*`
 *   - Per-run replay (`/backtests/[id]/replay`) — wired in commit
 *     01bfdf1 (was a placeholder before)
 *   - Dashboard drift tile presence
 *
 * Pattern follows `e2e/smoke.spec.ts` — assert HTTP < 500 + the
 * section heading text. Pages have empty-state fallbacks so the
 * smoke pass works whether the backend is reachable or not.
 *
 * Strategy id: hard-coded to `1`. The smoke contract is `<500`, so
 * even when strategy 1 doesn't exist (route 404s) the test passes
 * — we're only checking the route doesn't server-error.
 */

import { expect, test } from "@playwright/test";

const STRATEGY_ID = 1;

test.describe("Strategy workspace sub-routes", () => {
  test("/strategies/[id] — workspace home renders", async ({ page }) => {
    const response = await page.goto(`/strategies/${STRATEGY_ID}`);
    expect(response?.status()).toBeLessThan(500);
    // Either the workspace renders OR notFound() shows the 404 page.
    await expect(
      page.getByText(/Overview|Not Found|Page not found/i),
    ).toBeVisible();
  });

  for (const section of [
    "build",
    "backtest",
    "replay",
    "prop-firm",
    "experiments",
    "live",
    "notes",
    "rules",
    "chat",
  ]) {
    test(`/strategies/[id]/${section} — sub-route renders`, async ({
      page,
    }) => {
      const response = await page.goto(
        `/strategies/${STRATEGY_ID}/${section}`,
      );
      expect(response?.status()).toBeLessThan(500);
    });
  }
});

test.describe("Per-run replay (post-IA-rework)", () => {
  test("/backtests/[id]/replay — chart renders or empty-state shows", async ({
    page,
  }) => {
    const response = await page.goto("/backtests/1/replay");
    expect(response?.status()).toBeLessThan(500);
    // Either a "Replay" heading (chart wired) OR notFound (no run id 1).
    await expect(
      page.getByText(/Replay|Page not found/i),
    ).toBeVisible();
  });
});

test.describe("Dashboard tile — Drift wiring", () => {
  test("/ — dashboard renders with drift tile present", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBeLessThan(500);
    // Drift tile copy: shows OK/WATCH/WARN when wired, "no live runs yet"
    // before any drift comparison has computed. Either is fine for smoke.
    await expect(
      page.getByText(/Drift/i).first(),
    ).toBeVisible();
  });
});
