# BacktestStation

A local-first research & control center for futures trading strategies.

Ingest market data from Databento, register strategy versions, run deterministic event-driven backtests on MBP-1 tick data with realistic OCO bracket fills, analyze performance, replay trades on interactive charts, and monitor a live instance.

**Status:** pre-MVP. Scaffolding in progress.

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

1. Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) first — every design decision is there.
2. Read [`CLAUDE.md`](CLAUDE.md) — the rules AI agents follow. Humans should follow the same ones.
3. One feature per branch, one PR per branch. Small PRs.
4. If a file passes 300 lines, split it.
5. Engine code must stay pure — no database, no HTTP, no file I/O inside the engine package.

## Getting started

Two terminals. Backend on :8000, frontend on :3000 (proxies `/api/*` to backend).

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

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
Next up: Phase 1 — backtest engine (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §7, §12).
