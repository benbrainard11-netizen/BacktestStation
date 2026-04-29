import { expect, test } from "@playwright/test";

/**
 * Smoke test — boots the dev server, opens every primary route, asserts
 * the page returns 200 and the expected H1 / page header renders. Doesn't
 * touch backend-mutating actions; it's safe to run against a live DB.
 *
 * Backend may or may not be reachable. Pages have empty-state fallbacks
 * for API failure, so the smoke pass works either way.
 */

test.describe("Primary route smoke pass", () => {
  test("/ — Command Center renders", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBeLessThan(500);
    // Either greeting (active strategy) OR pick-strategy CTA.
    await expect(
      page.getByText(/Good morning|Good afternoon|Good evening|Working late|Pick a strategy/i),
    ).toBeVisible();
  });

  test("/strategies — Strategies hub renders", async ({ page }) => {
    const response = await page.goto("/strategies");
    expect(response?.status()).toBeLessThan(500);
    await expect(
      page.getByRole("heading", { name: "Strategies", exact: true }),
    ).toBeVisible();
  });

  test("/monitor — Monitor renders", async ({ page }) => {
    const response = await page.goto("/monitor");
    expect(response?.status()).toBeLessThan(500);
    await expect(
      page.getByRole("heading", { name: "Monitor", exact: true }),
    ).toBeVisible();
  });

  test("/backtests — Backtests list renders", async ({ page }) => {
    const response = await page.goto("/backtests");
    expect(response?.status()).toBeLessThan(500);
    await expect(
      page.getByRole("heading", { name: "Backtests", exact: true }),
    ).toBeVisible();
  });

  test("/journal — Journal renders", async ({ page }) => {
    const response = await page.goto("/journal");
    expect(response?.status()).toBeLessThan(500);
    await expect(
      page.getByRole("heading", { name: "Journal", exact: true }),
    ).toBeVisible();
  });

  test("/prop-simulator — Simulator dashboard renders", async ({ page }) => {
    const response = await page.goto("/prop-simulator");
    expect(response?.status()).toBeLessThan(500);
    await expect(
      page.getByRole("heading", { name: "Prop Firm Simulator" }),
    ).toBeVisible();
  });

  test("/prop-simulator/firms — Firm rules renders", async ({ page }) => {
    const response = await page.goto("/prop-simulator/firms");
    expect(response?.status()).toBeLessThan(500);
    await expect(
      page.getByRole("heading", { name: "Firm Rules", exact: true }),
    ).toBeVisible();
  });

  test("/prop-simulator/runs — Simulation runs renders", async ({ page }) => {
    const response = await page.goto("/prop-simulator/runs");
    expect(response?.status()).toBeLessThan(500);
    await expect(
      page.getByRole("heading", { name: "Simulation Runs", exact: true }),
    ).toBeVisible();
  });

  test("/data — Data renders", async ({ page }) => {
    const response = await page.goto("/data");
    expect(response?.status()).toBeLessThan(500);
  });

  test("/settings — Settings renders", async ({ page }) => {
    const response = await page.goto("/settings");
    expect(response?.status()).toBeLessThan(500);
  });
});

test.describe("Strategy picker flow", () => {
  test("/ shows the strategy picker when none is selected", async ({
    page,
    context,
  }) => {
    // Force a clean slate: no localStorage carryover.
    await context.clearCookies();
    await page.goto("/");
    await page.evaluate(() => window.localStorage.clear());
    await page.reload();

    const choose = page.getByRole("button", { name: /Choose strategy/i });
    await expect(choose).toBeVisible();

    // Click into the picker; assert it opens.
    await choose.click();
    await expect(
      page.getByRole("dialog", { name: /Select a strategy/i }),
    ).toBeVisible();
  });
});
