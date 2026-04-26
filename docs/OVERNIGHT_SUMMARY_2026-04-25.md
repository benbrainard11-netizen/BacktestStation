# Overnight summary — 2026-04-25 → 2026-04-26

> Ben slept; this doc is the wake-up. Three independent chunks landed on `main`. Nothing destructive happened — `D:\data` is unchanged.

## TL;DR

- **3 feature commits + 3 merge commits + 1 follow-up fix on `main`**.
- **+58 tests** added (385 passing, was 328 before this session's start counting from the prior summary).
- **Forward Drift Monitor v1 backend shipped** — set a baseline + hit the API.
- **Fractal AMD diagnostic tooling shipped** — debug CSVs already producing useful state for task #71.
- **`docs/PROJECT_STATE.md`** is the new "where is everything" reference for you + Husky.

## Commits on `main`

```
7b7808c merge: docs/project-state-and-test-coverage
16b607a docs(state): single project-state checkpoint + tests for orphan ingest helpers
3a8d931 merge: feat/fractal-amd-diagnostics
7d51164 feat(fractal_amd): diagnostic + trace tooling
0de73a9 merge: feat/drift-monitor-backend
bd42c85 feat(drift): Forward Drift Monitor v1 backend
2bb388d fix(parquet_mirror): default trade_count + vwap when missing
```

## What's new

### Backend

- **`app/services/drift_comparison.py`** — Forward Drift Monitor v1 service. Two signals:
  - **Win-rate drift** (rolling N-trade WR; thresholds 7pp WATCH / 15pp WARN).
  - **Entry-time drift** (chi-square on hour-of-day distributions; p<0.01 WARN, 0.01–0.05 WATCH).
- **`StrategyVersion.baseline_run_id`** column added (idempotent migration in `_run_data_migrations`). Two SQLAlchemy `foreign_keys=` hints disambiguate the now-bidirectional FK between `strategy_versions` and `backtest_runs`.
- **scipy** added as a backend dependency.

### API endpoints (new)

- **`GET /api/monitor/drift/{strategy_version_id}`** — returns `DriftComparisonRead` with one `DriftResultRead` per signal. 404 when the version has no baseline assigned. Otherwise always responds; "no live run yet" is reported as WARN results, not a 404.
- **`PATCH /api/strategy-versions/{id}/baseline`** — body `{"run_id": int | null}`. Rejects `source="live"` runs with 422. `null` clears the baseline.

### Diagnostic CLIs

- **`backend/debug_fractal_setup_lifecycle.py`** — runs the engine with a tracing subclass; writes `setup_lifecycle_*.csv` (one row per setup with rejection-reason history) and `setup_rejections_*.csv` (one row per validation rejection). Smoke run on **2026-04-22** already generated CSVs at `backend/tests/_artifacts/setup_lifecycle_2026-04-22_2026-04-23.csv` and `setup_rejections_2026-04-22_2026-04-23.csv`.
- **`backend/debug_fractal_compare_to_live.py`** — pairs each live trade (from `BacktestRun(source="live")`) with the closest port setup, dumps a side-by-side CSV.

### Tests (+58 net)

- `tests/test_drift_comparison.py` — 18 tests covering both signals, the composite resolver, and both new endpoints via `TestClient`.
- `tests/test_signal_helpers_isolated.py` — 20 tests for `check_touch`, `resample_bars`, `detect_fvgs`, `find_nearest_unfilled_fvg`, `is_in_entry_window`. Fills the gaps in the existing `test_fractal_amd_signals.py`.
- `tests/test_warehouse_sync.py` — 11 tests for partition-path math, idempotency, rebuild override, dry-run, error paths.
- `tests/test_cost_estimator.py` — 7 tests pinning the universe shape, continuous-symbol notation, dataset constant, and CLI arg plumbing. No real API calls.

### Docs

- **`docs/PROJECT_STATE.md`** — new. Single "where is everything" snapshot covering shipped components, in-progress work, the orphan ingest CLIs (cost_estimator / bulk_free_pull / warehouse_sync / legacy importers / Fractal AMD debug scripts), the data-warehouse map, and an **onboarding section aimed at Husky** with three setup options (full pull / Tailscale subset sync / direct Tailscale read).
- This doc.

## Diagnostic finding from the smoke run

Running `debug_fractal_setup_lifecycle.py --start 2026-04-22 --end 2026-04-23` produced:

- 49 setups detected
- 12 final-status `TOUCHED` (touched outside entry window or position-blocked)
- 37 final-status `WATCHING` (never touched)
- 103 validation rejections, dominant gates:
  - **`same_bar_as_touch` (73×)** — strategy validates on the same bar that flipped the setup to TOUCHED. Per `strategy.py:285-286`, `bars_since_touch < 1` returns None ("don't fire on touch bar itself"). That's *expected* on the touch bar — the issue is *the next bar* should succeed.
  - **`touch_too_old` (30×)** — by the time validation finally runs, more than `entry_max_bars_after_touch=3` minutes have passed.

**Working hypothesis (not confirmed):** the setup gets reset to WATCHING after each failed validation, then re-touched many bars later, then again rejected as `touch_too_old` before the next-bar gate has a chance. There's also a subtler interaction with `_try_emit_entry`'s "most recently touched first" sort that could be eating the right setup. The compare-to-live CSV will tell us where the divergence actually is.

This is **the right tool to bring into the next debug session**, not something to fix tonight.

## Things that might want your attention

- **No baseline is set on any `StrategyVersion` yet.** The drift monitor endpoint returns 404 until you `PATCH /api/strategy-versions/{id}/baseline {"run_id": <imported-or-engine-run-id>}`. Pick a baseline once you've decided which run represents Fractal AMD's "expected" behavior. The trusted-CSV import is gone, so a fresh imported or engine run is the way.
- **scipy was added as a dep.** If you ever rebuild the backend venv from scratch, `pip install -e ".[dev]"` will pick it up. No action needed today.
- **Drift thresholds are module constants** (`WR_WARN_DEVIATION_PP=15.0`, `WR_WATCH_DEVIATION_PP=7.0`, `ENTRY_CHISQUARE_WARN_P=0.01`, `ENTRY_CHISQUARE_WATCH_P=0.05`). Tune in `app/services/drift_comparison.py` once you have a baseline + a few live trades.
- **Frontend drift panels are deferred.** The design in `docs/FORWARD_DRIFT_DESIGN.md` shows the intended layout; pair on it with Husky once his polish work merges.
- **Origin remote is not pushed to.** Five new commits sit on local `main` (counting the parquet_mirror fix as a sixth). Push when you're ready: `git push origin main`. I left this for you on purpose — a sleepy push to a shared branch can ruin a morning.

## On task #71

The Fractal AMD port debug. Concrete next session:

1. `cd backend && .venv/Scripts/python.exe debug_fractal_setup_lifecycle.py --start 2026-04-14 --end 2026-04-22` (covers more days, including dates with live trades).
2. Open `setup_lifecycle_*.csv` — sort by `final_status` and `n_validation_attempts`. The setups with many rejections clustered at `same_bar_as_touch` followed by `touch_too_old` are the smoking gun.
3. Once a baseline is set: `python debug_fractal_compare_to_live.py --strategy-version-id <id> --start <first-live-trade-date> --end <last>`. The output CSV pairs each live trade with the closest port setup; the `port_setup_final_status` and `port_setup_rejection_reasons` columns tell you exactly which gate the port stops at vs each live trade.
4. Then — and only then — touch `strategy.py`. The pure helpers test green (20 isolated tests), so the bug is in `_scan_for_setups` / `_try_emit_entry` orchestration, not the math.

## What this run intentionally did NOT do

- **No frontend changes.** Husky's polish work is in flight; overnight UI risk + conflict risk wasn't worth it.
- **No strategy code edits.** Port debug needs a careful pair-debug session; the diagnostic CSVs are the hand-off, not a fix.
- **No prop-simulator UI changes.** Husky's territory.
- **No drift-monitor cron job.** v1 is compute-on-demand. Cron is a follow-up once the panels exist.
- **No `D:\data` operations.** Warehouse untouched.
