# Project State — 2026-04-27

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

- 434 backend tests green at the time of this writing (`pytest backend/`).
- Lookahead harness (`test_lookahead.py`), determinism check, MBP-1 stop-vs-target race test all green.
- Pre-commit hooks: ruff + black (Python), prettier (TS).

---

## In progress

### Task #71 — Fractal AMD strategy port emits 0 trades — **RESOLVED 2026-04-26 (with follow-up)**

Two bugs were entangled here; both fixed in `fix/fractal-amd-port-zero-trades` (merged to main 2026-04-26).

**Bug 1 (data):** `live_trades_jsonl` was treating `entry_time` / `exit_time` as wall-clock UTC. The live bot writes wall-clock **ET**. Verified by aligning live entry prices against historical bars: a 09:31:00 / 26868.75 BEARISH record matches the **13:31 UTC** bar's open exactly (= 09:31 EDT). DB times for `BacktestRun(source="live")` were 4 hours off from any port setup, so port-vs-live pairing always missed.

Fix: `parse_record` / `read_jsonl` / `import_jsonl` gain a `tz` parameter (default ET) and localize-then-convert. New CLI flag `--time-zone` for forward compatibility. Live JSONL re-imported.

**Bug 2 (strategy — the real "0 trades" bug):** `_validate_and_build_intent` returned `None` for both *transient* ("wait one bar") and *terminal* (risk fail / dedup collision / touch too old) failures. The caller treated every `None` as terminal and reset the setup to WATCHING. So a setup TOUCHED on bar T got reset on bar T itself (failed `bars_since_touch < 1`), and bar T+1 had no TOUCHED setup left to fire.

Fix: `_validate_and_build_intent` now returns `ValidationResult` tagged with `action ∈ {"fire", "wait", "reject"}`. Only `"reject"` resets the setup; `"wait"` leaves it TOUCHED for the next bar.

**Diagnostic confirmation (live trade window 2026-04-22..04-24):**

| Stage | Port trades | Live trades reached FILLED in port |
|---|---|---|
| Before either fix | 0 / 188 setups | 0 of 6 |
| After ET importer + transient-vs-terminal fix | 4 / 46 setups | 2 of 6 |
| After diagnostic matching upgrade + CLI inclusive-end fix | **6 / 66 setups** | **5 of 6** (1 has port touch but no fire) |

The remaining unmatched live trade (2026-04-24 13:31 short, entry 27196.83): port detected a same-direction session-tf zone at 27266-27285, touched at 13:11 UTC (pre-RTH), terminally rejected as `touch_too_old` by the time entry window opened at 13:30. Live's bot fired on a different / lower zone the port doesn't surface — a genuine signal-detection difference, not the orchestration / data bugs we'd been chasing.

**Task #80 outcome (closed 2026-04-26):**
- Real fixes: importer ET conversion (commit `2a831e1`-precursor), transient/terminal validation split (`2a831e1`), tiered diagnostic matching (`2d2904a`), inclusive `--end` semantics on the debug CLIs (`5a73f7d`).
- Pinned upstream reference: `docs/FRACTAL_AMD_PORT_REFERENCE.md` carries the FractalAMD- baseline SHA and an evaluated-changes table for every commit since.
- Open: 1 live trade still doesn't fire in port (touch outside window). Not a show-stopper; tracked as "signal-detection nuance" rather than a port bug.

**Tools** (use these whenever the port diverges from live again):
- `backend/debug_fractal_setup_lifecycle.py`
- `backend/debug_fractal_compare_to_live.py`
- `backend/debug_fractal_zero_trades.py` (original characterization)
- `backend/tests/test_signal_helpers_isolated.py` (20 tests; primitives isolation check)

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
│   ├── live/                  GLBX.MDP3-tbbo-{YYYY-MM-DD}.dbn               (live ingester)
│   ├── historical/
│   │   ├── GLBX.MDP3-{schema}-{YYYY-MM-DD}.dbn                              (legacy multi-symbol — pre 2026-04-27)
│   │   └── GLBX.MDP3-{schema}-{YYYY-MM-DD}-{SYMBOL}.dbn                     (per-symbol — current)
│   └── databento/             # parquet mirror of raw/ DBN files
│       ├── tbbo/symbol={X}/date={Y}/part-000.parquet
│       └── mbp-1/symbol={X}/date={Y}/part-000.parquet
├── processed/
│   └── bars/timeframe=1m/symbol={X}/date={Y}/part-000.parquet
├── manifests/                 per-file kv-metadata + integrity hashes
├── heartbeat/live_ingester.json
└── logs/
```

What's actually in the warehouse as of **2026-04-27 evening** (audited end-to-end on ben-247 after the full March MBP-1 backfill):

- **TBBO (live, raw DBN)** — 4 daily files in `raw/live/`, only 2026-04-27 has market data (~592k MBP1Msg / 46 MB). The 4/24–4/26 files are weekend / ingester-respawn-boundary empty (control messages only).
- **TBBO (live, parquet)** — 4 partitions at `raw/databento/tbbo/` for 2026-04-27 (NQM6, ESM6, YMM6, RTYM6).
- **MBP-1 (historical, raw DBN)** — 63 files / 13.2 GB at `raw/historical/`. All 27 March 2026 trading days. Two filename layouts:
  - 15 legacy multi-symbol files (03-01..05, 08..12, 15..19) from the first puller pass
  - 48 per-symbol files (03-06, 13, 20, 22..27, 29..31) from the second pass after the puller fix
- **MBP-1 (historical, parquet)** — 108 partitions at `raw/databento/mbp-1/` (27 dates × 4 symbols).
- **1m bars (derived)** — 112 partitions at `processed/bars/timeframe=1m/` (108 mbp-1-derived + 4 tbbo-derived).
- **Manifests** — 28 in `manifests/ingest_runs/` (27 mbp-1 + 1 tbbo). One per (date, schema).
- **OHLCV-1m, OHLCV-1s** — none yet (separate pulls, not scheduled).

> **Doc lifecycle note (2026-04-27):** prior versions of this section claimed "12 months TBBO across the full 28-symbol universe" was already in the warehouse. That was never true — the live ingester only came online 2026-04-24 and the parquet pipeline produced its first partitions on 2026-04-27. When a future audit shows different contents, **edit this section to match the audit**, not to project forward. The Live-pipeline panel on `/monitor` is the live-truth view; this doc is a periodic snapshot.

**Pipeline status (2026-04-27 evening):** end-to-end working. Earlier in the day:

- The historical puller hit a Databento 503 cascade on 14 of 31 March days (full-day × 4-symbol payloads were too large). Fixed in PR #9 (`fix/historical-puller-per-symbol-with-retry`): per-symbol pulls + retry-with-backoff. Re-pull with the fix succeeded with 0 errors.
- The per-symbol naming convention is new (current naming: `{DATASET}-{SCHEMA}-{DATE}-{SYMBOL}.dbn`). `parquet_mirror.py:_DBN_RE` updated to accept both legacy and per-symbol filenames; the existing group-by-record-symbol code path partitions correctly in both cases.
- The `BacktestStationParquetMirror` scheduled task has `ExecutionTimeLimit = 30 min` baked in by `install_scheduled_tasks.ps1`. That cap kills any catchup-mode mirror run mid-flight (today's full warehouse catchup needed ~45 min). PR #10 (`fix/mirror-task-execution-time-limit`) bumps it to 4h. **Until that PR ships and the install script is re-run on ben-247**, large catchups must be done by launching `python -m app.ingest.parquet_mirror` directly (no scheduler = no time limit).

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
