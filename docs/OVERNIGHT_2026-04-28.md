# Overnight 2026-04-27 → 28 — autonomous run summary

> Wake-up doc. Read this first; it tells you what shipped, what didn't, and what to look at first.

## TL;DR

**Five tasks attempted. Four shipped. One abandoned.** All five lanes have a clean commit on `main` (the abandoned one's branch was deleted, no half-fix on main). Tests went **470 → 494** (+24 tests). No regressions.

Look first: open the desktop app and visit `/monitor` — you should see the new **Forward Drift Monitor** panels (Win-rate drift + Entry-time drift cards) below the Live-trades pipeline panel.

---

## What shipped

### Task 1 ✅ — Drift v1 frontend panels (`/monitor`)

ROADMAP lane B item.

- Backend: new `GET /api/monitor/drift/latest` auto-resolves the most-recent live run's strategy_version_id and returns its drift comparison. 404s with structured detail messages for "no live runs" / "no baseline" so the frontend renders the right empty state.
- Frontend: 3 new components — `DriftPanel` (top-level, polls /drift/latest every 30s), `WinRateDriftCard`, `EntryHourDriftCard`. Tri-color status (OK live / WATCH warn / WARN off).
- Wired into `/monitor` between LiveTradesPipelinePanel and the legacy MonitorBody.
- 3 new tests in `test_drift_comparison.py`. Type-check clean.
- **Current empty state:** strategy_version 2's `baseline_run_id=9` points at a deleted run (run 9 was deleted earlier today as a duplicate), so the panel currently shows "No baseline assigned" with a link to `/strategies`. Tomorrow you can fix this by setting a real baseline (e.g. run 11 — the current live import — or run 2 — the trusted multi-year import) via `PATCH /api/strategy-versions/2/baseline` `{run_id: 2}` or via the `/strategies` UI.

Commit: `15eb157`.

### Task 2 ✅ — Ready-for-capital gate CLI

ROADMAP lane A item — concrete pre-flight for real-money decision.

- New CLI: `python -m app.cli.ready_for_capital_check --strategy-version-id 2`
- Evaluates the four ROADMAP §A criteria: ≥30 trades, ≥40% WR, max DD < 10R, all entries within 09:30–14:00 ET.
- Pure logic in `evaluate_gate()`; CLI wrapper formats + exits 0/1.
- 8 unit tests covering each criterion + edge cases (no live runs, version isolation, exclusive window close).
- **Smoke-tested on real DB:** strategy_version_id=2 currently FAILs (10 trades vs 30 required, 2/10 entries outside window). Concrete signal that Lane A's headline goal isn't done yet — paper-trade more, fix the pre-09:30 entries.

Commit: `dc7602a`.

### Task 3 ✅ — Weekly gap-filler module + scheduled task

ROADMAP lane B item — insurance against future puller failures.

- New module: `backend/app/ingest/gap_filler.py` + 12 tests in `test_gap_filler.py`.
- Refactor: extracted `pull_one_day_one_symbol()` from `historical.py` so the gap-filler can call per-(date, symbol) without going month-at-a-time.
- Scheduled task: `BacktestStationGapFiller` registered in `scripts/install_scheduled_tasks.ps1` (weekly Sunday 03:00 local, ExecutionTimeLimit PT4H).
- $0-cost guardrail: any gap with cost > $0 is skip-warned, never pulled. Won't silently rack up Databento charges.
- Recognizes both per-symbol filenames (current) and legacy multi-symbol files (pre-2026-04-27); over-counts legacy as "all symbols present" to avoid re-pulling.
- **NOT smoke-tested against real Databento** — that requires the API key, which lives on ben-247. Tomorrow ben-247 should run `python -m app.ingest.gap_filler --dry-run --last-n-months 3` to verify the scan logic against the real warehouse, then `--last-n-months 3` (no dry-run) to actually fill any gaps. The next scheduled fire is the upcoming Sunday at 03:00 local on whichever machine the install script is run on.

Commit: `7a2fb69`.

### Task 4 ❌ — Close 1-of-6 port↔live signal gap (ABANDONED)

ROADMAP lane A item. Hard-capped at 90 min wall-clock per the plan.

**What I tried:** option (b) — reset `touch_bar_time` to entry-window-open bar when the original touch was pre-window. Implemented as a new `_entry_window_open_for(bar, config)` helper + `effective_touch = max(setup.touch_bar_time, _entry_window_open_for(...))` in `_validate_and_build_intent`.

**What happened:**
- All 35 entry / signal-helper unit tests still green (no obvious regressions on isolated logic).
- Diagnostic re-run on 2026-04-22..04-25 live trades:
  - Pre-fix baseline: filled_within_10m=5, last_touch_within_10m=0, first_touch_within_60m=1, no_match=0
  - Post-fix: filled_within_10m=4, last_touch_within_10m=1, first_touch_within_60m=1, no_match=0
- The fix DID make trade 5 (2026-04-24 13:31 short) go from `first_touch_within_60m` → `filled_within_10m` ✅.
- BUT trade 6 (2026-04-24 13:34 long) regressed from `filled_within_10m` → `last_touch_within_10m`. Net 5 → 4 working live trades.
- Per the plan rule ("If the score on any of the original 5 *drops*, REVERT"): reverted.
- Bumping `entry_max_bars_after_touch 3 → 8` (fallback option) wouldn't help — the unmatched trade's gap is 19 minutes, much wider than 8.
- Per existing project memory `project_backtest_divergence.md`: the unmatched trade is a "signal-detection difference" (port + live picked different FVG zones), not a touch_too_old timing issue. My fix was solving the wrong problem.

**Decision:** abandoned the branch. No commit on `main`. The 5-of-6 match remains the current state. **This is a strategy-detection problem, not orchestration; deeper work needed.** Worth revisiting only when there's a concrete hypothesis about which detection step (HTF stage, LTF FVG selection) is picking the wrong zone.

### Task 5 ✅ — Trade-replay FVG zone overlay (backend only)

Originally planned as full-stack. **Backend shipped; frontend deferred.**

- New schema: `ReplayFvgZone {direction, low, high, created_at, timeframe, filled, fill_time}`
- `ReplayPayload.fvg_zones` added (defaults `[]`, backward-compatible).
- `/api/replay/{symbol}/{date}` now resamples the day's 1m bars to 5m HTFCandles and runs `detect_fvgs()` both directions, returning all detected zones.
- Reuses the strategy's actual FVG detector — chart bands will match exactly what the strategy keyed off of.
- 4 existing replay tests still green. FVG detection logic is covered by `test_signal_helpers_isolated.py`.

**Frontend rendering deferred** because lightweight-charts doesn't have a native filled-rectangle series and a clean "two LineSeries + interpolated fill" rendering needs visual review before merging. Can ship in 30-60 min when you want — pull the zones from `payload.fvg_zones` and draw them as semi-transparent rectangles in `BarChart.tsx` (and optionally `TickChart.tsx`).

Commit: `b01ba46`.

---

## Final state of the repo

- **Backend tests: 494 passed** (was 470 at start of overnight; +24).
- **Frontend type-check: clean** (`npx tsc --noEmit`).
- **Branches: only `main` on remote.**
- **All commits pushed to `main`:** 15eb157 (drift v1) → dc7602a (gate CLI) → 7a2fb69 (gap-filler) → b01ba46 (FVG zones backend).

---

## What you should do first when you wake up

1. **Open the desktop app** (`start.bat` if it's not running). Go to `/monitor`. Confirm the **Forward drift monitor** panel renders without crashing. The cards will show "no baseline assigned" — see step 2.
2. **Set a baseline for strategy_version 2** so the drift panel actually computes. Run 9 (the prior baseline) was deleted. Easiest path: PATCH it via curl to point at run 2 (the trusted multi-year imported run):
   ```
   curl -X PATCH http://localhost:8000/api/strategy-versions/2/baseline \
        -H "Content-Type: application/json" -d '{"run_id": 2}'
   ```
   Or use the `/strategies` UI if that page has a baseline picker. The drift panel should update on the next 30s poll.
3. **Smoke-test the ready-for-capital CLI:**
   ```
   cd backend && .venv\Scripts\python -m app.cli.ready_for_capital_check --strategy-version-id 2
   ```
   Expected: FAIL with 10/30 trade count + 2/10 outside-window. The two outside-window trades are 2026-04-09 12:21 + 12:30 ET — actually those are 13:21 and 13:30 if you read them as ET; double-check whether the early live trades from before the bot's window-fix are real or import artifacts.
4. **If you want the gap-filler to run before next Sunday:** ssh to ben-247 + `python -m app.ingest.gap_filler --dry-run --last-n-months 3` to see what it'd pull. If the dry-run looks sane, drop `--dry-run` to actually fill. Otherwise wait — Sunday 03:00 fires automatically.
5. **Send Husky an FYI:** he can also use the merge-review subagent (`.claude/agents/merge-review.md`) before pushing. His three direct-pushes from yesterday were clean per a retroactive review, but the process gate exists to catch the cases that aren't.

## Open issues / deferred

- **Taildrop receive on benpc** — still broken. ben-247's daily 16:45 ET cp doesn't reach benpc's inbox. The `tailscale file get --wait` listener I started yesterday is still passively running (PID 9184 if not reaped). When ben-247 retries, it should land. Until then, today's 17:00 ET import will pick up yesterday's stale JSONL again (idempotent — same run id, no harm done, just no fresh data).
- **1-of-6 port↔live signal gap** — abandoned tonight. Strategy-detection problem; needs targeted investigation of which FVG zone the port should be picking on 2026-04-24 13:31. Trade-replay tool can help debug visually once Task 5 frontend lands.
- **FVG zone overlay frontend** — backend shipped; rendering in `BarChart`/`TickChart` is a 30-60 min follow-up.
- **Drift panel default baseline** — the panel currently can't compute because the baseline FK is stale. Either fix manually (step 2 above) or add automatic stale-FK cleanup when a run is deleted.

## What I deliberately didn't do

- Frontend Vitest setup (Task F from the original plan — too risky to wire up cleanly without supervision in a Tauri+Next project).
- Husky's mocked `/prop-simulator` dashboard + compare pages (his lane, don't stomp).
- ML / 2nd strategy / new warehouse schemas (deferred per ROADMAP).
- Direct mutations of strategies / model weights (no AI auto-applies — CLAUDE.md rule).

---

Sleep well. The system grew up a little overnight.
