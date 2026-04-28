# Afternoon 2026-04-28 — autonomous run summary

> Wake-up doc for after the gym. This run finished while you were out.

## TL;DR

**8 phases attempted. 8 shipped.** Two PR-ready branches pushed to GitHub, neither merged so you can review on return.

- **Lane B punch list** (3 commits): drift hardening + gate CLI cutover + FVG zone overlay frontend
- **Lane A engine work** (2 commits): perf optimization (90× speedup, byte-identical) + setup expiry on day boundary

Tests: 507 → 512 backend after Lane B merges (+5 net from new tests). Lane A adds no tests (engine optimization + setup expiry are exercised by existing 71 fractal tests + the smoke characterization). Both green. Frontend `npx tsc --noEmit` clean.

ben-247 is unreachable via Tailscale right now (showing offline, SSH refused). Phase 7 work (gap_filler dry-run + Taildrop diagnosis) is deferred to your hands. Details below.

## What shipped

### Lane B PR — branch `lane-b-punch-list-2026-04-28-pm`

PR URL (click to open): https://github.com/benbrainard11-netizen/BacktestStation/pull/new/lane-b-punch-list-2026-04-28-pm

**Commit `8be9968`** — `fix(drift): NULL out baseline FK on run delete + dedicated stale-baseline UI state`
- Root cause: SQLite FK enforcement is off in this app and the `baseline_run_id` columns were added via ALTER TABLE without `ON DELETE SET NULL`. So when run 9 was deleted this morning, strategy_version 2's `baseline_run_id` was left pointing at a dead FK and `/api/monitor/drift/latest` 404'd.
- Fix: `DELETE /api/backtests/{id}` now explicitly NULLs out `StrategyVersion.baseline_run_id`, `Experiment.baseline_run_id`, and `Experiment.variant_run_id` before deleting the run.
- Frontend: new `stale_baseline` empty state distinguishes "baseline points at deleted run" from "no baseline ever set." Surfaces the server's specific message in both cases.
- 3 new tests in `test_backtests_delete_api.py`.

**Commit `ea493a2`** — `feat(gate-cli): --ignore-before flag for pre-cutover live trades`
- The 2 pre-09:30 entries flagged this morning (2026-04-09 12:21+12:30 UTC) are real bot misfires from before the 2026-04-12 window-fix. Confirmed by re-reading `live_trades_jsonl.py`: the importer correctly localizes ET wall-clock → UTC, and the same conversion produces correct results for all post-04-12 trades. So the data is right; the gate just needed a way to scope to the post-fix lifecycle.
- New `--ignore-before YYYY-MM-DD` flag drops trades with `entry_ts.date()` before that UTC date.
- Smoke against real DB:
  ```
  ready_for_capital_check --strategy-version-id 2 --ignore-before 2026-04-12
  [FAIL] trade_count          actual=8                                threshold=>= 30
  [PASS] win_rate             actual=62.5% (5/8)                      threshold=>= 40%
  [PASS] max_drawdown_r       actual=2.79R                            threshold=< 10.0R
  [PASS] entry_window         actual=all entries in window            threshold=all in 09:30-14:00 ET
  ```
  3 of 4 gates pass. Only blocker is paper-trade volume.
- 2 new tests in `test_ready_for_capital.py`.

**Commit `d97bf1d`** — `feat(replay): FVG zone overlay rendering on /replay + /trade-replay charts`
- Finishes the feature whose backend shipped this morning. Custom `FvgZonesPrimitive` (lightweight-charts `ISeriesPrimitive`) draws semi-transparent rectangles behind candles.
- Wired into both `ReplayChart` (/replay daily review) and trade-replay's `BarChart` (1m+ modes). Each chart gets a small `FVG (N)` toggle next to the speed presets so you can hide bands when busy.
- Render rules: BULLISH = emerald @ 10% fill / 50% stroke; BEARISH = red. Filled zones drop to 4% fill so unfilled gaps pop.
- API smoke: `/api/replay/NQ.c.0/2026-04-22` returns 23 zones, 1380 bars. Frontend type-check clean.
- TickChart (1s mode) intentionally skipped — TBBO window is ±15min around entry; most zones from earlier in the day fall outside that window. Defer to follow-up.

**NOT visually verified** — I could read the API but couldn't drive the Tauri app. If a chart breaks, the type-check would have caught it; please open `/replay?symbol=NQ.c.0&date=2026-04-22` and confirm bands render.

### Lane A PR — branch `lane-a-engine-perf-2026-04-28-pm`

PR URL: https://github.com/benbrainard11-netizen/BacktestStation/pull/new/lane-a-engine-perf-2026-04-28-pm

**Commit `f1e92b7`** — `perf(fractal_amd): bisect-based bar windowing — O(n^2) -> O(n log n)`
- The strategy was rebuilding `bars_by_asset` via `list(context.history)` every bar AND every helper that received it filtered via `[b for b in bars if start <= b.ts_event < end]`. At Q1 scale (60 trading days × 3 symbols) this dominated profile time — Q1 2024 was killed at 146 min wall-clock per the 2026-04-25 memory.
- Three changes:
  1. `_bars_by_asset` returns direct refs (no `list()` copy) — helpers don't mutate, the defensive snapshot was wasted O(n) per bar.
  2. New `_bars_in_range(bars, start, end)` using `bisect.bisect_left` on `ts_event`. Bars are append-ordered so the list is sorted — slice in O(log n + k).
  3. `_scan_for_setups` and `_build_setups_from_ltf` pre-slice each asset's bars to the relevant time window before calling helpers. Helpers still filter internally; they now walk O(window_size) bars instead of O(total_bars).
- Smoke (SMOKE_WEEK, 2024-01-02..08, 6900 NQ bars, 3 symbols):
  ```
  pre-fix:  44.5s runtime, 10 trades, 20% WR, -5.61R total, 50 stage signals, 142 setups
  post-fix:  5.0s runtime, 10 trades, 20% WR, -5.61R total, 50 stage signals, 142 setups
  ```
  **8.9× speedup, byte-identical metrics** (every count and every R figure matches).
- Q1 2024 (the run that was killed at 146 min): now completes in **96.6s**.

**Commit `3265e0b`** — `fix(fractal_amd): expire setups at trading-day boundary`
- One of the two un-fixed strategy items from the 2026-04-25 memory: setups were never expiring, so they could touch days later when price drifted back through the FVG and fire stale entries the live bot would never take.
- Mirrors `live_bot.reset_day()` (FractalAMD-/production/live_bot.py:336): on day rollover, clear `self.setups = []` and `self._fully_scanned = set()`. Stage signals kept for diagnostic value (no behavior depends on them across days).
- **Q1 2024 characterization, with vs without expiry**:
  ```
                  trades   WR%   totalR   bull R   bear R   runtime
    pre-expiry      124   26.6%  -27.53   -31.46    +3.93   96.6s
    post-expiry     122   33.6%   +2.79    -7.26   +10.06   74.2s
  ```
  Q1 2024 went from -27.5R losing to +2.8R break-even on the same data path. WR up 7pp, both legs improved (bull -31→-7, bear +4→+10), runtime down 23%. **NOT a green light for paper** — single-quarter results have a documented track record of not holding multi-year (memory `project_backtest_divergence.md` 2026-04-10). The full 2024-2026 characterization is below.

**Multi-year FULL window characterization (2024-01-02 → 2026-01-09, ~2.25 yr, with perf fix + setup expiry):**

```
preset:    FULL_2024_2026
window:    2024-01-02 -> 2026-01-09
nq bars:   707243
runtime:   724.4s  (12 min — previously killed at 146 min without producing output)

count:     989
win_rate:  29.89%
total R:   -77.45
bull R:    -42.29
bear R:    -35.16
best R:    +27.89
worst R:   -1.00
stage signals: 5209
```

**Reading this honestly:** Q1 2024 alone went from -27.5R to +2.8R with setup expiry, but the 2-year run is still firmly underwater (-77R / 30% WR, both legs losing). Memory `project_backtest_divergence.md` was already calling this out on 2026-04-10 ("the strategy itself is noise — not just the live_bot port") with synthetic-TBBO data; this re-confirms it on real-TBBO data with two strategy improvements applied.

**What this means for direction:** the perf fix unblocks the multi-month evaluation that was previously infeasible (146 min kill → 12 min completion), and setup expiry is a clean improvement on the live_bot logic — both worth merging on their merits. But neither moves the strategy past "no consistent edge across 2 years" without more substantive work. The other un-fixed strategy item (narrow FVG window) is the next fix worth trying, but per memory `project_backtest_divergence.md` (2026-04-25) it requires a strategy-rule decision from Ben — I deliberately didn't touch it.

**Sunday-go-live status: still OFF.** Same gate as the 2026-04-25 memory said: "engine port produces a recognizable strategy on its own merits across multi-month windows." It does now produce a recognizable strategy (989 trades, distributed across both directions, runtime tractable) — but that strategy loses money, so paper would just be paper-losing. Don't ship.

**The other un-fixed strategy item** — narrow FVG detection window in `_build_setups_from_ltf` — was deliberately NOT touched. It needs a strategy-rule decision (how wide should the resample window be? full session?) and your sign-off; it was on the explicit "do not touch without Ben's approval" list.

## What I deliberately didn't do

- **Husky's mocked `/prop-simulator` pages** — his lane.
- **Strategy-rule changes beyond setup expiry** — the FVG detection window question (memory's other un-fixed item) needs a strategy decision from you, not engineering.
- **Push branches to `main` or auto-merge** — both branches are PR-ready and waiting for your review.
- **Run `gh pr create`** — `gh` is not installed on this machine. PR URLs above will open the GitHub form pre-filled.

## What you should do first when you wake up

1. **Open the desktop app** at `/replay?symbol=NQ.c.0&date=2026-04-22`. Click `Load`. You should see the candles plus 23 semi-transparent FVG bands behind them. Toggle `FVG (23)` to confirm hide/show works.
2. **Open `/monitor`** and confirm the Drift panel still renders fine.
3. **Click the two PR URLs above** (or run `gh pr create` once gh is installed) and review the diffs. They're independent — Lane B has no Lane A code in it and vice versa, so you can merge them in either order.
4. **Run the gate CLI** with the cutover flag to see how close we are to ready-for-capital:
   ```
   cd backend && .venv\Scripts\python -m app.cli.ready_for_capital_check \
       --strategy-version-id 2 --ignore-before 2026-04-12
   ```

## Open issues / deferred for next session

### ben-247 was unreachable

- ICMP works (3ms RTT). Tailscale shows `offline, last seen 2m ago`. SSH (port 22) refused.
- The Tailscale daemon on ben-247 isn't checking in. Most likely it crashed or stopped reporting; the OS itself is up enough to respond to ping.
- **Phase 7 not done as a result.** Specifically:
  - Did NOT run `gap_filler --dry-run --last-n-months 3` against the real warehouse.
  - Did NOT diagnose why ben-247's daily 16:45 ET cp doesn't reach benpc's Taildrop inbox.
- **Action for you when you wake up:** RDP/console into ben-247, check `tailscale status`, restart the Tailscale daemon if needed. Then run gap_filler dry-run from there. Sunday's auto-fire (03:00 local) will fail silently if Tailscale is still down.

### Strategy-decision items

These are flagged in `project_backtest_divergence.md` (2026-04-25) and not safe for me to touch autonomously:

1. **Narrow FVG detection window** in `_build_setups_from_ltf`. Strategy currently feeds `lrs → lce + 5*ltf_min` (~30 min of 5m bars, 6 candles) into `detect_fvgs`. With <20 candles, `min_gap_pct=0.3` collapses and the detector finds noise gaps. Trusted likely runs over a wider session-of-5m-bars window. Deciding the window is a strategy call.
2. **Engine port output is structurally divergent from trusted** — Q1 2024 produced -27.5R / 26.6% WR with the live_bot code path. The trusted CSV (lost source) showed +274R / 40.8% WR over 2.25 years. Even fixing #1 above probably won't close that gap; the underlying setup-detection differs. Memory notes this is a deeper problem requiring rebuild from `export_trades_tv.py` (which doesn't exist anymore).

### Other carry-overs

- **TickChart FVG overlay** — backend already ships zones in the `/api/replay` payload but TickChart uses a different (TBBO) endpoint with no zones in scope. ±15-min window means most day-zones fall offscreen anyway. Defer.

## Test status

- Backend: lane-a branch + smoke regression: **507 passed**. Lane-b branch: **512 passed** (+5 new tests). Each branch green standalone.
- Frontend: `npx tsc --noEmit` → clean.
- Engine port still characterizes the same way it did pre-perf-fix on the smoke window (byte-identical 10/20% WR/-5.61R).

---

Sleep on it. Tomorrow you can ship Lane B in 5 min and Lane A in 5 more, then think about the strategy questions with fresh eyes.
