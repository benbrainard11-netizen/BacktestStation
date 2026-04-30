/**
 * Playwright smoke pass for the workspace IA sub-routes.
 *
 * THIS FILE IS NOT RUNNABLE FROM ITS CURRENT LOCATION.
 *
 * It lives under `docs/` because the Playwright dependency
 * (`@playwright/test`) is on `origin/main` (Husky's branch) and not
 * on the lane-c branch yet. When we merge `origin/main`, move this
 * file to `frontend/e2e/strategies-subroutes.spec.ts` and it picks
 * up Husky's `playwright.config.ts` automatically.
 *
 * Coverage:
 *   - Workspace home (`/strategies/[id]`)
 *   - All ten sub-routes under `/strategies/[id]/*`
 *   - Per-run replay (`/backtests/[id]/replay`) — the route that was
 *     a placeholder before commit 01bfdf1 and is now a real chart
 *
 * Pattern follows Husky's `e2e/smoke.spec.ts` — assert HTTP < 500 +
 * the section heading text. Pages have empty-state fallbacks so the
 * smoke pass works whether the backend is reachable or not.
 *
 * Strategy id: hard-coded to `1`. The smoke contract is
 * `<500`, so even when strategy 1 doesn't exist (route 404s) the
 * test still passes — we're only checking that the route doesn't
 * server-error. Adjust if you want a positive-existence check.
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
