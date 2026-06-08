# BacktestStation

A local-first quant **research lab + backtesting toolbox** for personal futures trading: a deterministic backtest engine, a Databento data warehouse, order-flow / feature detectors, tick-replay + Monte-Carlo + prop-firm sims, and a Cloudflare-R2 data share. **Backend + tools only** — run from the CLI / Python. There's a small read-only status page; there is no web app.

> **Read [`REPO_GUIDE.md`](REPO_GUIDE.md) first** — it maps how this repo fits with the per-strategy live repos and the InsyncAPP platform.

## Where to look
- **Repo map / how the repos connect** — [`REPO_GUIDE.md`](REPO_GUIDE.md)
- **What we're building** — [`docs/ROADMAP.md`](docs/ROADMAP.md)
- **What's running today** — [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
- **System design** — [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Engineering rules (non-negotiable)** — [`CLAUDE.md`](CLAUDE.md)
- **AI agent ground rules** — [`AGENTS.md`](AGENTS.md)
- **Machine roles + data ownership** — [`docs/LOCAL_INFRASTRUCTURE.md`](docs/LOCAL_INFRASTRUCTURE.md)
- **Warehouse schema** — [`docs/SCHEMA_SPEC.md`](docs/SCHEMA_SPEC.md)

## Stack
- **Backend:** FastAPI (Python 3.12) — serves only a read-only status page. SQLAlchemy + SQLite (`meta.sqlite`), pyarrow, Pandas.
- **Engine:** pure Python, deterministic, lookahead-tested, honest MBP-1 stop-vs-target fills.
- **Data:** Databento (MBO / MBP-1 / TBBO / OHLCV) → DBN (raw, append-only) → Hive-partitioned Parquet on `D:\data`. Cloudflare R2 mirror for cross-machine reads (`client/bsdata`).
- **Network:** Tailscale connects ben-247 (data/server) ↔ benpc (research/training).

## Repo layout
```
backend/app/        the lab — backtest engine, ingest (Databento + R2), data reader,
                    features, research detectors/outcomes, strategies, sims
                    (monte_carlo / prop_firm / drift), db (meta.sqlite), cli,
                    main.py (read-only status page)
backend/tests/      engine determinism, lookahead, MBP-1 race, detectors, sims
backend/scripts/    data/ops helpers (warehouse build, backfills)
experiments/        research lines — see experiments/_INDEX.md (RV, Mira, sizing, …)
market_state/       the broad market-state model (active research project)
live_engine/        the Mira live bot — SEPARATE git repo, nested here
client/bsdata/      external R2 warehouse reader (pip-installable)
docs/               canonical docs (ARCHITECTURE, ROADMAP, PROJECT_STATE, SCHEMA_SPEC, …)
data/               gitignored — meta.sqlite + staging (RAW market data lives on D:\data)
```
There is **no `frontend/` and no HTTP CRUD API** — the repo went backend-only on 2026-06-08. Tools run via CLI / Python.

## Branch policy
- `main` — canonical, what runs in dev and on ben-247.
- Personal / working branches per person (`ben/…`, `caseybranch`, …) for research; merge to `main` when shared-worthy.
- One feature per branch, small PRs. Run the [`merge-review`](.claude/agents/merge-review.md) subagent before merging to `main`. If a file passes 300 lines, split it.

## Getting started
```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q                                    # green except known pre-existing failures (see PROJECT_STATE)
python -m uvicorn app.main:app --port 8000   # status page at http://127.0.0.1:8000
```
`start.bat` (repo root) does the venv-activate + uvicorn launch in one step. Run the tools (backtest runner, sims, ingest CLIs) as Python modules — see `docs/` + `REPO_GUIDE.md`.

## For collaborators
1. Read [`REPO_GUIDE.md`](REPO_GUIDE.md) + [`docs/ROADMAP.md`](docs/ROADMAP.md).
2. Read [`docs/LOCAL_INFRASTRUCTURE.md`](docs/LOCAL_INFRASTRUCTURE.md) — machine roles + the **append-only raw-data** rule.
3. Read [`CLAUDE.md`](CLAUDE.md) — engineering rules (humans + AI agents).
4. Work on your own branch; one feature per branch; `merge-review` before merging to `main`.
