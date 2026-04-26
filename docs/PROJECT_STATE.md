# Project State — 2026-04-25

> **What this doc is.** A single, scannable snapshot of "what's where, what's working, what's broken" across BacktestStation. Updated as a checkpoint, not on every commit. When in doubt, the code wins — but this saves you 30 minutes of re-discovery before you start.

> **Audience.** Ben (CEO/idea person, AI-driven build), Husky (collaborator), and any future agent picking up the project cold. If you're a new collaborator, jump to **§ Onboarding a new collaborator** at the bottom.

---

## Shipped + working

### Backend

- **Backtest engine** (`backend/app/backtest/engine.py`)
  - Pure: takes Strategy + bars + RunConfig, returns BacktestResult.
  - Bracket-order broker with conservative ambiguous-fill resolution (stop wins).
  - Determinism enforced by tests (`test_backtest_engine.py`, `test_backtest_runner.py`).
  - Multi-instrument support via `Context.aux: dict[str, Bar | None]`.
- **Strategies**
  - `MovingAverageCrossover` (example, lives in `app/strategies/examples/`).
  - `FractalAMD` (`app/strategies/fractal_amd/`) — full port of the live bot's logic, ~490 lines. Detects HTF stage signals, builds LTF FVG-bearing setups, transitions WATCHING→TOUCHED→FILLED, emits BracketOrders. **Currently emits 0 trades — see "in progress" below.**
- **Forward Drift Monitor v1 (backend, 2026-04-25)** (`app/services/drift_comparison.py`)
  - Win-rate drift + entry-time chi-square against a designated baseline run.
  - `GET /api/monitor/drift/{strategy_version_id}`
  - `PATCH /api/strategy-versions/{id}/baseline`
  - 18 dedicated tests; thresholds tunable as module constants.
- **Prop-firm simulator backend** (`app/services/prop_firm.py`, `app/services/monte_carlo.py`)
  - Monte Carlo sampling: trade_bootstrap / day_bootstrap / regime_bootstrap.
  - Persists results in `prop_firm_simulations` table; aggregated payloads cached.
- **Data warehouse + ingest pipeline** (`app/ingest/` + `app/data/`)
  - Pinned schemas (`SCHEMA_SPEC.md`), Hive partitioning, kv-metadata lineage.
  - Live TBBO ingester running on ben-247.
  - Historical puller, parquet mirror, legacy importers, bulk free pull, cost estimator, warehouse sync. (See "Orphan modules" for the per-script story.)
- **Schema-first API** (`app/schemas/`, `shared/openapi.json`, `frontend/lib/api/generated.ts`)
  - Pydantic schemas are the source of truth; TS types regenerated via `bash scripts/generate-types.sh`.
- **Schema migration discipline** (`app/db/session.py:_run_data_migrations`)
  - Idempotent ALTERs run on every app start. New columns added without losing local SQLite metadata.

### Frontend

- **`/strategies` pipeline board + dossier**
- **Run a Backtest** UI shipped (`/backtests/run`), wired end-to-end to the engine via `POST /api/backtests/run`.
- **Backtest dossier** (`/backtests/[id]`): trades, equity curve, metrics, config snapshot, autopsy, prop-firm sim launcher.
- **Imported runs**: import + visualize CSV/JSON result bundles.
- **Live monitor page** (`/monitor`): ingester health + live status from the bot.

### Tests + CI

- 367 backend tests green at the time of this writing (`pytest backend/`).
- Lookahead harness (`test_lookahead.py`), determinism check, MBP-1 stop-vs-target race test all green.
- Pre-commit hooks: ruff + black (Python), prettier (TS).

---

## In progress

### Task #71 — Fractal AMD strategy port emits 0 trades

The port detects HTF stage signals and builds LTF FVG-bearing setups, but no setup ever flips to FILLED. As of the **2026-04-25 diagnostic run** (smoke window 2026-04-22, single day):

- 49 setups detected
- 12 final-status `TOUCHED` (touched outside the entry window or position-blocked)
- 37 final-status `WATCHING` (never touched)
- 103 validation rejections, dominant reasons:
  - `same_bar_as_touch` (73× — strategy validates on the touch bar itself, before the next-bar entry semantics kick in)
  - `touch_too_old` (30× — by the time validation runs, the touch is older than `entry_max_bars_after_touch=3` minutes)

**Strong hypothesis (unconfirmed):** the bar-after-touch gate is interacting badly with the order-emission flow. The same bar that just executed `check_touch` immediately falls through to `_try_emit_entry`, where `bars_since_touch < 1` rejects it. The next bar's `_try_emit_entry` runs with `bars_since_touch == 1` — that path should succeed. Most rejections happen in subsequent bars when something else (risk gate, dedup) blocks the trade.

**Trusted CSV source unrecoverable**, so we can't byte-equal to the trusted backtest. Live trades from the running bot (8 in `BacktestRun(source="live")` row 3) are now the comparison oracle.

**Tools to use next session:**
- `backend/debug_fractal_setup_lifecycle.py` — dumps per-setup CSV with rejection reasons.
- `backend/debug_fractal_compare_to_live.py` — pairs each live trade with the closest port setup.
- `backend/debug_fractal_zero_trades.py` — original characterization script.
- `backend/tests/test_signal_helpers_isolated.py` (20 tests) — isolation check for primitives.

### Prop-simulator UI completion (Husky's domain)

- Backend done; `/prop-firm/runs/[id]` dossier wired.
- Firm-presets page + side-by-side compare are partially mocked — Husky's pending work, do not stomp.

### Forward Drift Monitor v2 (frontend panels)

- Backend shipped 2026-04-25 (chunk A above).
- Frontend panels deferred — too much UI risk overnight, and Husky's frontend work is in flight.
- When ready: add WR + entry-hour panels to `/monitor` per the design in `docs/FORWARD_DRIFT_DESIGN.md`.

### Live ingester health

Running on ben-247 against `BS_DATA_ROOT=D:\data`. Heartbeat written to `data/heartbeat/live_ingester.json`; surfaced via `GET /api/monitor/ingester`. Status as of 2026-04-24: ticks flowing; reconnect_count growth has not been audited recently.

---

## Orphan modules

Tools shipped to disk but not called from app code paths. Each is a CLI; document is the front door.

| Module | What it does | When to use |
|---|---|---|
| `app.ingest.cost_estimator` | Wraps `databento.metadata.get_cost`. Reports USD cost of a proposed pull. `--universe` mode shows a structured matrix across asset categories. | Before any historical pull bigger than a single day, run this to confirm the request is `$0` (free under the $180/mo plan) or budgeted. |
| `app.ingest.bulk_free_pull` | Walks the asset universe in monthly chunks for the schemas covered free by Databento Standard. Default: ohlcv-1m, ohlcv-1s, tbbo. | Re-run to backfill the free-tier universe after a gap or schema addition. **Default `--max-symbols-per-call` is 999 — do NOT lower** (one DBN per (schema,date) means batches overwrite each other; see module docstring). |
| `app.ingest.warehouse_sync` | Cross-platform partition copy (uses shutil; no rsync). Walks `(schema × symbol × date)` Hive paths and copies subset from a remote root to a local root. | Husky-style subset replication over Tailscale SMB. Pass `--remote-root Z:/data --local-root D:/data` plus the symbols/dates you want. |
| `app.ingest.legacy_ohlcv_import` | Imports DBN-zst ohlcv-1m files from prior tooling into Hive partitions. | One-off; used for the initial 11y NQ/ES/YM 1m bars import. Re-run only if a new dump arrives. |
| `app.ingest.legacy_tbbo_import` | Imports per-contract TBBO parquet from prior tooling into continuous-symbol partitions. | Same: one-off; ran for the 309 days of NQ TBBO archive. |
| `app.ingest.historical` | Monthly historical puller with `--schema` flag (mbp-1, tbbo, ohlcv-*). Idempotent on per-day DBN files. | The primary backfill tool. Run on the 1st of each month via Task Scheduler; or `--month YYYY-MM` to fill specific gaps. |
| `app.ingest.parquet_mirror` | Converts raw DBN files to Hive-partitioned parquet that the engine + frontend can read. | After any historical/bulk pull that produced new DBN. Idempotent. |
| `backend/debug_fractal_zero_trades.py` | One-shot characterization run on a fixed week with hardcoded paths to legacy data dir. | Replicating the historical "0 trades" reproduction; mostly superseded by setup_lifecycle script for new debug work. |
| `backend/debug_fractal_setup_lifecycle.py` | Runs the engine with a tracing subclass; dumps per-setup CSV + per-rejection CSV. | First tool to reach for when the port emits unexpected trade counts. |
| `backend/debug_fractal_compare_to_live.py` | Side-by-side: live trades from `BacktestRun(source="live")` vs port setups. | Use after lifecycle dump to compare each live trade to what the port would have done. |

---

## Data warehouse map (`D:\data` on ben-main; `BS_DATA_ROOT`)

```
D:/data/
├── raw/
│   ├── live/                  GLBX.MDP3-tbbo-{YYYY-MM-DD}.dbn        (live ingester)
│   └── historical/            GLBX.MDP3-{schema}-{YYYY-MM-DD}.dbn    (historical pulls)
├── processed/
│   ├── tbbo/symbol={X}/date={Y}/part-000.parquet
│   ├── mbp-1/symbol={X}/date={Y}/part-000.parquet
│   └── bars/timeframe=1m/symbol={X}/date={Y}/part-000.parquet
├── manifests/                 per-file kv-metadata + integrity hashes
├── heartbeat/live_ingester.json
└── logs/
```

What's actually in the warehouse as of 2026-04-25:

- **OHLCV-1m**: 11 years of NQ.c.0, ES.c.0, YM.c.0 + 8 years for the rest of the universe (25 non-equity-index symbols). ~3,400 days × 28 symbols.
- **OHLCV-1s**: 8 years for NQ.c.0 + ES.c.0 + YM.c.0 only.
- **TBBO**: 12 months for the full 28-symbol universe (rolling — Databento free tier is `last 12 months` for L1 schemas).
- **Live TBBO**: continuously appended day by day as ben-247 ingests.

Full schema definitions: see [`SCHEMA_SPEC.md`](SCHEMA_SPEC.md). Additions bump `SCHEMA_VERSION` in `backend/app/data/schema.py`.

---

## How a typical research session uses the warehouse

1. Pick a strategy hypothesis. Edit / create one in `app/strategies/`. Strategy is dumb — bars + Context in, OrderIntent out.
2. Run a backtest from the UI (`/backtests/run`) or the CLI (`python -m app.backtest.runner ...`). Output writes to `data/backtests/strategy={name}/run={ts}_{id}/` and a row lands in `meta.sqlite`.
3. Inspect from `/backtests/{id}`: trades, equity, metrics, autopsy.
4. Optionally launch a Monte Carlo prop-firm sim from the dossier.
5. If running live, designate a baseline (`PATCH /api/strategy-versions/{id}/baseline`) and watch `GET /api/monitor/drift/{id}` for divergence.

Imported live trades land via `app.ingest.live_trades_jsonl` — they show up as `BacktestRun(source="live")` and feed the drift monitor.

---

## Onboarding a new collaborator (Husky setup)

1. Clone the repo to a local path.
2. Install backend deps:
   ```bash
   cd backend
   python -m venv .venv
   .venv/Scripts/pip install -e ".[dev]"
   ```
3. Install frontend deps:
   ```bash
   cd frontend
   npm install
   ```
4. **Pick a `BS_DATA_ROOT`.** The data warehouse is large (~hundreds of GB). Three options:
   - **Run the full pipeline locally**: pull and mirror via `app.ingest.bulk_free_pull` + `app.ingest.parquet_mirror`. Requires `DATABENTO_API_KEY` env var. Free under the Standard plan.
   - **Subset-sync from Ben's main PC**: enable Tailscale, SMB-share `D:\data` from ben-main, then run `python -m app.ingest.warehouse_sync --symbols NQ.c.0,ES.c.0,YM.c.0 --start 2024-01-01 --end 2026-12-31 --schemas bars-1m --remote-root Z:/data --local-root D:/data`. Pulls only the partitions you actually want.
   - **Direct read over Tailscale**: set `BS_DATA_ROOT=Z:/data` (the mounted share). No copy at all; reads go over the network. Great for occasional use, slow if you're hammering it.
5. Run the dev servers:
   ```bash
   # backend (terminal 1)
   cd backend && .venv/Scripts/uvicorn app.main:app --reload --port 8000
   # frontend (terminal 2)
   cd frontend && npm run dev
   ```
6. Visit `http://localhost:3000`.

Test it works:
```bash
cd backend && .venv/Scripts/pytest -q
```

If the suite passes (367 currently), your environment is wired up. If it doesn't, the first failure usually points at either Python version (need 3.12+) or a missing data dependency.

---

## Cross-references

- [`AGENTS.md`](../AGENTS.md) — agent operating rules (load-bearing).
- [`CLAUDE.md`](../CLAUDE.md) — non-negotiable code rules + lifecycle. Read before touching the engine.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — long-form architecture; some sections superseded by phased build, see header note.
- [`docs/SCHEMA_SPEC.md`](SCHEMA_SPEC.md) — pinned warehouse schemas. Edit this FIRST when adding a new schema.
- [`docs/BACKTEST_ENGINE.md`](BACKTEST_ENGINE.md) — engine internals + how to write a strategy.
- [`docs/FORWARD_DRIFT_DESIGN.md`](FORWARD_DRIFT_DESIGN.md) — design notes that fed the drift monitor v1.
- [`docs/PHASE_1_SCOPE.md`](PHASE_1_SCOPE.md) — Phase 1 done-criteria.
- [`docs/RUNBOOK_SUNDAY_OPEN.md`](RUNBOOK_SUNDAY_OPEN.md) — going-live checklist.
