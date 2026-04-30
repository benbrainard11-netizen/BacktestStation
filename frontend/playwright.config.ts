import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for the smoke test in `e2e/`.
 *
 * The webServer block boots `pnpm dev` automatically on port 3000 if
 * nothing is already listening there. The backend is NOT auto-started —
 * the smoke test only checks that pages render against whatever real (or
 * unreachable) API the dev server proxies to. Each page has graceful
 * fallbacks for API failure, so the smoke pass works even with no backend.
 *
 * Run locally:
 *   pnpm playwright install chromium    # first time only — downloads browser
 *   pnpm playwright test
 *   pnpm playwright test --ui           # interactive runner
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "pnpm dev",
    port: 3000,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
