# Frontend testing — not yet wired

The frontend has zero test infrastructure. Backend is solid (136 tests). This is the known debt.

## When this matters

Right now: low impact. The backend contract is well-tested, typecheck catches most TS errors, and the dossier is still small enough to verify by clicking through.

Will bite later when:
- The dossier grows more client-heavy panels (forward monitor, prompt generator v2, risk profile)
- A schema change silently breaks a panel that `tsc` didn't catch (e.g., runtime shape mismatch)
- Husky + Ben are working on different panels simultaneously and something subtle regresses

## Recommended minimum — one Playwright smoke test

~30 min of setup, not 15. Breaks down:

1. `npm install -D @playwright/test` (~1 min)
2. `npx playwright install chromium` (2-5 min — downloads browser binary)
3. `frontend/playwright.config.ts` with `webServer` auto-starting `next dev` and the backend (5 min)
4. `frontend/e2e/dossier.spec.ts` — one test that:
   - Loads `/strategies`, asserts page renders
   - Clicks "+ new strategy", fills form, submits
   - Lands on `/strategies/<id>`, asserts stage chip, NotesPanel, ExperimentsPanel, PromptGeneratorPanel, versions list all render
   - (Optional) creates a note, asserts it appears
5. Run locally: `npx playwright test` (first run: 1-2 min)
6. Update CI: GitHub Actions runs it on PR (if/when CI exists)

## Alternatives (lighter than Playwright)

- **Vitest + Testing Library + jsdom** — renders components in node with mocked fetches. Catches shape/type issues. Doesn't actually verify user flows. ~15 min setup.
- **MSW for API mocking** — pairs with above for realistic fetch behavior.

## What to NOT bother with

Unit tests of pure helper functions (formatters, cn, etc.) — typecheck + obvious call sites catch enough. Rule of thumb: only test what calls a network or touches state.

---

When you're ready to wire this, delete this file.
