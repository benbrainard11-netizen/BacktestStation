# Merge notes — `lane-c-trusted-port-2026-04-28-pm` ↔ `origin/main`

Generated 2026-04-30 during overnight prep.

## Status

**Branches have diverged.** Both branches add commits since `ab6ac1b`:

- `lane-c-trusted-port-2026-04-28-pm` (mine): 12 commits — workspace IA pivot, replay/drift wiring, 5 backend hardening PRs.
- `origin/main` (Husky): 6 commits — mock removal, prop-sim wiring, dashboard featured-run, Playwright, backend-down fallback, pnpm.

Trial merge attempted at `git merge --no-commit --no-ff origin/main`. Two real conflicts, then aborted to leave the working tree clean.

## Conflicts (must resolve before merging)

### 1. `frontend/app/page.tsx` — dashboard design conflict

This is the **big one**. The two branches express two different products on the home page.

**My branch (`HEAD`):** `Dashboard` — Next.js server component. Portfolio overview:
- KPI tiles row: Live strategies / Today P&L / Runs this week / Drift status
- "Live strategies" panel — one card per strategy with `status === "live" || "forward_test"`
- "Recent activity" panel — feed of latest backtest runs across all strategies
- No client-side state; one batched server fetch on each request.

**Husky's `origin/main`:** `CommandCenter` — client component. Strategy-scoped:
- `<SystemOverview />` strip on top (always visible: live status, P&L, strategy/run/note counts)
- `useCurrentStrategy()` hook — reads/persists "currently selected strategy" id
- If no strategy selected → "Pick a strategy to start" empty state
- If selected → equity curve + monthly heatmap + sparkline + heartbeat **for that one strategy**

These are structurally different products. **Ben's instruction (2026-04-30 evening): "Husky's whole job was the design, all of his design stuff is to stay."** That points to taking Husky's design as the winner here.

But Ben's prior wording ("front page is just like all basic monitoring or general stuff") matched mine. He's aware of the tension and asked to think on it before deciding.

**Resolution path (assuming Husky's design wins):**
- Take Husky's `CommandCenter` body wholesale.
- The Drift tile concept I added (wired to `/api/monitor/drift/latest`) belongs in the SystemOverview strip OR added to Husky's stat tiles row.
- Delete `frontend/components/dashboard/LiveStrategyCard.tsx` and `frontend/components/dashboard/RecentActivityFeed.tsx` (mine, no other callers).
- The `summarizeDrift` helper I added at the bottom of `app/page.tsx` should move into `SystemOverview.tsx`.

### 2. `frontend/app/strategies/page.tsx` — small, mostly compatible

**My branch:** Cleaner — `StrategyCardGrid` only, no sort/filter chrome. Fetches without a backend-down fallback (`apiGet<Strategy[]>("/api/strategies")` would 500 on offline).

**Husky's:** Adds `Btn`/`Panel`/`StatTile` imports for an `ACTIVE_STAGES` summary, AND adds the backend-down fallback `.catch(() => [])`.

**Resolution:** keep my cleaner card-grid layout (per the IA pivot), adopt Husky's `.catch(() => [])` fallback pattern. Drop his stage-summary tiles since the workspace IA puts that info elsewhere.

## Non-conflicting changes from Husky (all clean adds)

These auto-merged successfully and add value:

- **`frontend/components/SystemOverview.tsx`** — new component, top-strip with live status. **Should live regardless of dashboard decision.**
- **`frontend/components/backtests/BacktestsScopeShell.tsx`** — new
- **`frontend/components/prop-simulator/compare/CompareWorkspace.tsx`** — new (compare wired to real backend)
- **`frontend/components/prop-simulator/new/NewSimulationForm.tsx`** — new (wizard wired to real backend)
- **`frontend/components/prop-simulator/NotImplemented.tsx`** — new
- **`frontend/e2e/smoke.spec.ts`** + **`frontend/playwright.config.ts`** — Playwright e2e suite
- **`frontend/pnpm-lock.yaml`** — added (note: `package-lock.json` also still present; one needs to go)

## Deletions from Husky (all confirmed dead post-his-work, no callers expected)

- `frontend/components/prop-simulator/MockDataBanner.tsx`
- `frontend/components/prop-simulator/SimulationCoreVisual.tsx`
- `frontend/components/prop-simulator/dashboard/{DemoFirmsWarning, FirmRuleStatusPanel, InteractiveCoreStats, QuickStatsRow, RecentRunsPanel, SetupHighlightPanel, SimulationCorePanel}.tsx`
- `frontend/components/prop-simulator/new/{NewSimulationWorkflow, StepReviewRun}.tsx`
- `frontend/components/prop-simulator/scope/MockWatermark.tsx`
- `frontend/components/prop-simulator/shared/RowSparkline.tsx`
- `frontend/lib/backtests/confidence-heuristic.ts`
- `frontend/lib/prop-simulator/mocks/{firms, index, run-detail, runs, views}.ts`
- `frontend/lib/prop-simulator/sparkline.ts`

**Verified safe**: nothing on my branch imports from any of these paths.

## Modified files Husky touched (will merge cleanly)

- `frontend/app/{backtests/[id], backtests, journal}/page.tsx`
- `frontend/app/prop-simulator/{compare, firms, layout, new, page, runs/[id]/scope}/page.tsx`
- `frontend/components/backtests/BacktestConfidencePanel.tsx`
- `frontend/components/layout/ContextBar.tsx`
- `frontend/components/prop-simulator/runs/SimulationRunsTable.tsx`
- `frontend/components/prop-simulator/scope/Colophon.tsx`
- `frontend/app/globals.css`
- `frontend/package.json`
- `frontend/tailwind.config.ts`
- `.gitignore`

## Open Ben decisions

1. **Dashboard design** — confirm Husky's `CommandCenter` wins, or keep mine (or hybrid).
2. **Lockfile** — keep one of `package-lock.json` / `pnpm-lock.yaml`, delete the other.

## Recommended merge command sequence (when Ben confirms)

```bash
# Resolve dashboard per Ben's call
git merge origin/main
# Manually edit frontend/app/page.tsx + frontend/app/strategies/page.tsx
git add frontend/app/page.tsx frontend/app/strategies/page.tsx
# Pick a lockfile
git rm frontend/{package-lock.json|pnpm-lock.yaml}    # whichever loses
git commit -m "merge: integrate Husky's design + frontend hardening"
git push
```

## Backend impact

None. My 12 commits and Husky's 6 commits don't touch the same backend files. PR 4's prop-firm response shape changes (multi-strategy pool labels, "Mixed pool") are forward-compatible with Husky's frontend prop-sim wiring (he reads `bt.strategy_name` per-pool-row, which my fix correctly populates).
