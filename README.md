# BacktestStation

A local-first research & control center for futures trading strategies.

Import your existing backtest and live-trading result files, inspect them through a dark quant dashboard, replay individual trades, and monitor a live strategy instance. A full Databento-fed event-driven backtest engine comes later — Phase 1 is built around the results you already have.

**Status:** pre-MVP. Phase 1 in progress — see [`docs/PHASE_1_SCOPE.md`](docs/PHASE_1_SCOPE.md).

## Stack

- **Backend:** FastAPI (Python 3.12), Polars, DuckDB, SQLAlchemy + SQLite
- **Engine:** pure Python, event-driven, no I/O dependencies
- **Frontend:** Next.js + TypeScript + Tailwind + shadcn/ui
- **Charts:** TradingView Lightweight Charts (replay), Recharts (analytics)
- **Data:** Databento DBN (raw) → Parquet (derived)

## Repo layout

Monorepo. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full plan.

```
backend/    FastAPI + engine + ingestion
frontend/   Next.js app
shared/     Generated OpenAPI schema
data/       Local market data (gitignored)
docs/       Architecture, decisions
```

## For collaborators

1. Read [`AGENTS.md`](AGENTS.md) and [`docs/PHASE_1_SCOPE.md`](docs/PHASE_1_SCOPE.md) first — these define what we're building right now.
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) is the long-term plan. Note the override banner at the top: the engine-first ordering it describes is deferred.
3. [`CLAUDE.md`](CLAUDE.md) — the rules AI agents follow. Humans should follow the same ones.
4. One feature per branch, one PR per branch. Small PRs.
5. If a file passes 300 lines, split it.

## Getting started

Two terminals. Backend on :8000, frontend on :3000 (proxies `/api/*` to backend).

### Backend

macOS / Linux:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell):

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks the activation script, run once per user:
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

Health check: `curl http://localhost:8000/api/health` → `{"status":"ok","version":"0.1.0"}`.

Tests: `pytest`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The sidebar routes to every placeholder page.

Typecheck + lint: `npm run typecheck` and `npm run lint`.

## Current status

Phase 0 complete: monorepo scaffold, health endpoint, dark UI shell, empty pages.

**Next up: Phase 1 — Imported Results Command Center.** Build the importer + DB + read endpoints + dashboards so existing backtest/live result files (CSV/JSON) flow into the dashboard. See [`docs/PHASE_1_SCOPE.md`](docs/PHASE_1_SCOPE.md) for the full scope and done-criteria.
