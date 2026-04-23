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

Setup instructions land in Phase 0 (monorepo scaffold). Not ready yet.
