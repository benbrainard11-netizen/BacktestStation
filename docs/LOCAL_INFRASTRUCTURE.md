# Local Infrastructure

## Why this doc exists

BacktestStation runs across three machines. Without explicit roles, work drifts to the wrong host, raw data gets mutated, and changes from one contributor stomp another. This doc is the contract: which machine does what, who owns which data, and how the three stay in sync.

Ben + Husky onboard from this doc.

## Machine roles

### `ben-247` (insyncserver) — server, source of truth

- Always-on Windows machine on Tailscale (`100.108.159.4`).
- **Owns:**
  - Live TBBO ingester (writes `D:\data\raw\live\*.dbn`).
  - Historical pulls (writes `D:\data\raw\historical\*.dbn`) — currently scheduled monthly, day 1 at 02:00 local.
  - Parquet mirror — reads `raw/`, writes `raw/databento/*/` and `processed/bars/`.
  - The live trading bot itself (`C:\Users\benbr\FractalAMD-\production\live_bot.py`) and the daily reconcile + Taildrop tasks that ship `trades.jsonl` to benpc.
  - The `D:\data\` warehouse: raw + processed + manifests + heartbeat + logs.
- **Does NOT own:** `meta.sqlite`, frontend dev, experimental code, Tauri desktop app.

### `benpc` (Ben's main PC) — research / dev / UI

- 5080 GPU; primary driver for backtests, frontend dev, Claude Code work.
- **Owns:**
  - `meta.sqlite` (`<repo>/data/meta.sqlite`).
  - The BacktestStation desktop app (Tauri shell + Next.js + uvicorn sidecar).
  - Local research output (`<repo>/data/backtests/...`).
  - The daily live-trades importer scheduled task (15:00 MDT = 17:00 ET; reads from Taildrop inbox, writes to local `meta.sqlite`).
- Has its own historical archive on `D:\` — at the time of writing, ~333 days of NQ TBBO going back to 2025-04-01, plus other index futures. (Distinct from ben-247's `D:\data\` even though they share a drive letter.)

### `desktop-ka4enq3` (Husky's PC) — contributor

- Tailscale-connected.
- **Owns:** PRs into `BacktestStation` `main` branch, prop-firm UI work (his lane per [`ROADMAP.md`](ROADMAP.md) Current Focus tier C).
- **Reads (read-only):** `D:\data` on ben-247 via Tailscale share, OR pulls subsets via `python -m app.ingest.warehouse_sync`.
- **NEVER mutates** `raw/`, **NEVER mutates** `live/`. All changes flow via Git commits → `main` → ben-247/benpc pull when needed.

## Data ownership rules

These are hard rules, not guidelines. Violating them puts the warehouse's trustworthiness at risk.

1. **Raw data is append-only.** `D:\data\raw\` files (DBN + parquet partitions inside) are never modified after creation. New pulls write new files. If a file needs reprocessing, the parquet mirror reads it again — never the other way around.
2. **Live data is server-only.** The live ingester only runs on ben-247. Other machines may copy `raw\live\` for analysis, never write into it.
3. **`meta.sqlite` is benpc-only.** Live trades flow ben-247 → Taildrop → benpc → SQLite. Husky's machine doesn't have `meta.sqlite`; he reads via the API or via the Tauri app.
4. **Backtest results** land at `<warehouse>\backtests\strategy=<name>\run=<ts>_<id>\` on whichever machine ran them. Tagged in `meta.sqlite` with the import_source path so we can trace which machine produced them.
5. **No machine pulls write-credentialed Databento.** Only ben-247 has the live API key in env; benpc and Husky's machine read parquet, not DBN streams.

## Cross-machine workflows

### Live trades pipeline (daily 17:00 ET)

See [`project_live_trades_pipeline`](../.claude/projects/) memory for the full spec. Sequence:

1. **16:30 ET on ben-247:** `reconcile_from_rithmic.py` updates `trades.jsonl` from Rithmic fills.
2. **16:45 ET on ben-247:** `tailscale file cp trades.jsonl benpc:` ships the file.
3. **17:00 ET on benpc:** Windows scheduled task `BacktestStation - Import Live Trades` drains the Taildrop inbox + runs `python -m app.ingest.live_trades_jsonl`. Result lands as a `BacktestRun(source="live")` row.

If the chain breaks, the `/monitor` page's "Live trades pipeline" panel surfaces it (`import_log_last_status`, `inbox_jsonl_modified_at`).

### Husky's data access

Two options, pick whichever fits the work:

- **Tailscale SMB share**: mount `\\insyncserver\D$\data` as `Z:` (or wherever) on Husky's machine. Set `BS_DATA_ROOT=Z:\` in his backend env. Reads go over the network; fine for occasional analysis.
- **Local subset replication**: `python -m app.ingest.warehouse_sync --remote-root \\insyncserver\D$\data --local-root D:\data --symbols NQ.c.0,ES.c.0,YM.c.0 --start 2026-01-01 --end 2026-12-31 --schemas tbbo,bars-1m`. One-time copy of the slice he needs. Faster repeated reads.

### Husky's code workflow

Standard Git: branch off `main` → push to GitHub → invoke the merge-review agent (`.claude/agents/merge-review.md`) before merging → merge to `main`. The merge-review agent reads `ROADMAP.md` + `CLAUDE.md` and flags scope drift / engineering violations before the merge happens.

## Setup notes (Husky onboarding)

1. Install Tailscale, authenticate against the same tailnet as ben-247 + benpc.
2. Clone the repo: `git clone https://github.com/benbrainard11-netizen/BacktestStation`.
3. Backend deps: see the README quickstart — `python -m venv .venv && .venv\Scripts\python -m pip install -e ".[dev]"` from `backend/`.
4. Frontend deps: `npm install` from `frontend/`.
5. Pick a `BS_DATA_ROOT`: either mount the Tailscale share OR run `app.ingest.warehouse_sync` to pull a subset locally. See [`PROJECT_STATE.md`](PROJECT_STATE.md) "Onboarding a new collaborator" for the canonical recipe.
6. Verify by running the backend test suite: `cd backend && .venv\Scripts\python -m pytest -q`. Should be 444 passed (or whatever `PROJECT_STATE.md` says is current).
7. Read [`ROADMAP.md`](ROADMAP.md) to know what's in scope; read [`../CLAUDE.md`](../CLAUDE.md) for engineering rules.

## Deferred (do not build until needed)

These are intentionally out of scope today. Adding them prematurely is a discipline violation per ROADMAP rules.

- **Docker / containerization.** Tauri + uvicorn sidecar works for one-trader-plus-contributor. Revisit only if cross-machine deploys become painful.
- **ML model registry / experiment tracker.** Tied to the deferred ML tier in `ROADMAP.md`. Don't build the registry before the models.
- **Dedicated agent fleet** (DevOps Agent, Data Warehouse Agent, Repo Guardian, etc.). The merge-review subagent + the discipline rules in ROADMAP/CLAUDE.md cover today's real needs. Build more agents when you have a concrete pain point that one would solve.
- **Folder restructure of `D:\data\`.** Current layout (`raw/{historical,live,databento/<schema>}/`, `processed/bars/`, `manifests/`, `heartbeat/`, `logs/`) is canonical per [`SCHEMA_SPEC.md`](SCHEMA_SPEC.md). Renaming for aesthetics is wasted churn that breaks every downstream tool.
- **Server-hosted UI.** The Tauri desktop app runs on each PC; ben-247 doesn't host a web UI for benpc or Husky to log into. If that becomes a real need, it's a deliberate decision, not a side effect.

Last updated: 2026-04-27.
