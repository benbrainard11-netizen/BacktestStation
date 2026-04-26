# Fractal AMD port — upstream reference

> **Why this doc exists.** The Fractal AMD strategy in `backend/app/strategies/fractal_amd/` is a port of `FractalAMD-/production/live_bot.py`. That repo evolves independently. Without a pinned baseline + an evaluated-changes table, every "is the port stale?" investigation re-runs the same 20 minutes of git archaeology. This doc is the archaeology, frozen.

## Pinned baseline

| Field | Value |
|---|---|
| Upstream repo | `FractalAMD-` (sibling repo, e.g. `C:\Users\benbr\FractalAMD-`) |
| Baseline file | `production/live_bot.py` |
| Baseline SHA | `3d08e2b5108c276f268d7e0b8dce85eacf231f1a` |
| Baseline commit | "Align live engine with trusted strategy" |
| Baseline date | 2026-04-12 23:01 |

The same SHA is referenced in the docstrings of:
- `backend/app/strategies/fractal_amd/strategy.py`
- `backend/app/strategies/fractal_amd/signals.py`

Update both when re-pinning.

## Upstream commits since baseline (evaluated 2026-04-26)

The following commits touched `production/live_bot.py` between baseline and `d8b760f` (HEAD as of 2026-04-26).

| SHA | Date | Subject (short) | Status in port |
|---|---|---|---|
| `c1b1090` | 2026-04-13 | Add MIN_RISK filter + dynamic dollar-based position sizing | **Partially in port.** `min_risk_pts=8.0` is in `config.py`. Dollar-based NQ→MNQ auto-downshift is **live-execution only** — backtest uses fixed `qty=1` from `RunConfig`, sizing decisions are out of scope here. |
| `ed9e39f` | 2026-04-16 | Timezone fix for ET logging | **Not relevant — logging only.** Port already uses `ZoneInfo("America/New_York")` for entry-window math. |
| `8aa579f` | 2026-04-16 | Midnight reset loop fix | **Not relevant — live-execution only.** Port resets per-day state via `_maybe_roll_day` keyed off bar timestamps. |
| `21b9d86` | 2026-04-16 | Daily reset synchronization | **Not relevant — live-execution only** (same as `8aa579f`). |
| `35209c3` | 2026-04-22 | Discard back-month tick contracts (NQ/ES/YM front+1) | **Not relevant.** Port reads pre-cleaned warehouse parquet for the continuous symbols (`NQ.c.0`, `ES.c.0`, `YM.c.0`). Back-month rolling is a tick-stream concern. |
| `f966c82` | 2026-04-22 | Operational hardening | **Not relevant — live-execution only** (reconnect / supervisor work). |
| `f6dd739` | 2026-04-22 | Tighten price scaling, state persistence, reject handling | **Not relevant.** Port reads scaled doubles from parquet; no nanos / no broker reject path. State persistence is a live-restart concern. |
| `bdb1ab9` | 2026-04-23 | Optional `BLOCK_OVERLAP` guard | **Deferred.** Default off in live, and the port already serializes via `if context.position is not None: return []`, so the practical surface is small. Backport only if the diagnostic surfaces back-to-back opposite-direction port trades that live didn't take. Tracked in PROJECT_STATE task #80. |
| `d8b760f` | 2026-04-25 | Emit setup_context + session_label + exit_time | **Importer-side, in.** v2 schema is already handled by `app/ingest/live_trades_jsonl.py:parse_record` (exit_ts + session_label + tz-aware exit_time). |

## Re-pinning process

1. `cd ../FractalAMD- && git pull origin main`.
2. `git log --oneline production/live_bot.py | head -20` — find the new HEAD SHA.
3. `git log --oneline 3d08e2b..HEAD -- production/live_bot.py` to enumerate commits since the current baseline.
4. For each commit, `git show <sha> -- production/live_bot.py` and decide: backtest-relevant logic, live-execution only, or schema change to JSONL?
5. Update this doc's table with each commit annotated.
6. If any commits are backtest-relevant, port them in their own commit on a feature branch. Update the docstring SHAs in `strategy.py` + `signals.py` once the port has caught up.
7. Update `docs/PROJECT_STATE.md` task #80 (or its successor) if material changes occur.

## Cross-references

- Port code: `backend/app/strategies/fractal_amd/`
- Port tests: `backend/tests/test_fractal_amd_*.py`
- Importer (handles JSONL schema drift): `backend/app/ingest/live_trades_jsonl.py`
- Diagnostic CLIs: `backend/debug_fractal_setup_lifecycle.py`, `backend/debug_fractal_compare_to_live.py`
- State doc: `docs/PROJECT_STATE.md`
- Strategy guide: `docs/BACKTEST_ENGINE.md`
