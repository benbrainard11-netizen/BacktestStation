# BacktestStation Agent Instructions

## Project Summary

BacktestStation is a local-first futures trading research/control center.

The user already has:
- A strategy that has been backtested with coding/AI before
- A strategy currently being live-tested
- Databento access
- A 24/7 PC available for live data/log collection
- Beginner-to-intermediate programming ability using AI coding agents heavily

Do not assume the user has no edge. The app is being built around an existing strategy and existing/live-tested outputs.

## Current Priority

The priority is not to build a perfect backtesting engine first.

The correct build order is:

1. Build the app framework/shell
2. Import existing backtest/live results
3. Display analytics
4. Add trade replay
5. Add live monitor
6. Build the cleaner Databento/MBP-1 event-driven backtesting engine later

This project should become useful quickly by making the existing strategy results easier to inspect, compare, replay, monitor, and improve.

If older docs describe an engine-first sequence, treat this file plus `docs/PROJECT_CONTEXT.md` and `docs/PHASE_1_SCOPE.md` as the current source of truth for Phase 1.

## Tech Stack

Preferred stack:

- Frontend: Next.js + TypeScript + Tailwind + shadcn/ui
- Backend: FastAPI + Python
- Metadata database: SQLite first
- Market/results storage: Parquet later
- Analytics: DuckDB later
- Types: Pydantic backend schemas -> OpenAPI -> generated TypeScript frontend types

## Product Modules

Core modules:

1. Command Center
2. Import Results
3. Strategy Library
4. Backtest Runs
5. Results Dashboard
6. Trade Replay
7. Live Monitor
8. Research Journal
9. Validation Lab later
10. Databento Engine later

## Phase 1 Goal

Phase 1 should build a working vertical slice around imported results.

Must support:

- Import CSV/JSON backtest outputs
- Store strategies, versions, runs, trades, equity points, metrics, config snapshots, notes
- Display imported runs
- Show equity curve
- Show drawdown curve
- Show metric cards
- Show trade table
- Open trade replay page
- Read a local live-status JSON file for monitor page

## Do Not Build Yet

Do not build these unless explicitly asked:

- Full Databento ingestion
- Full MBP-1 engine
- Live broker execution
- ML system
- SaaS auth/billing
- Public user system
- Strategy marketplace
- Mobile app
- No-code strategy builder
- Full order book simulator
- Overcomplicated plugin architecture

## Architecture Rules

- Keep backend and frontend cleanly separated.
- Backend owns data normalization and business logic.
- Frontend displays typed API data.
- Do not duplicate schemas by hand between frontend and backend.
- Prefer Pydantic schemas on backend and generated TypeScript types.
- Keep modules small.
- If a file exceeds roughly 300 lines, split it.
- If a function exceeds roughly 60 lines, split it.
- Avoid magic numbers.
- Store strategy/run assumptions explicitly.
- Every imported run should preserve its config snapshot.

## Backtesting Truth Rules

Even though the full engine is later, never fake correctness.

Every run should eventually show:

- Strategy version
- Dataset/source
- Date range
- Session
- Symbol
- Timeframe
- Risk settings
- Commission
- Slippage
- Fill assumptions
- Config snapshot
- Import source
- Created time

When the full engine is built later:

- No lookahead bias
- Explicit signal/execution separation
- Conservative fills for ambiguous stop/target cases
- Reproducibility required
- Data quality checks required

## UI Direction

The UI should feel like a serious dark quant dashboard:

- Black/white/zinc theme
- Dense but readable
- Thin borders
- Minimal shadows
- Professional finance aesthetic
- Mono font for numbers/tables
- No childish colors
- No emoji
- No excessive gradients
- No bloated components

Use accent colors sparingly:

- Green/emerald for gains
- Red/rose for losses
- Muted gray/zinc for neutral states

## AI Agent Behavior

When working in this repo:

1. Inspect before editing.
2. Explain current state before changing code.
3. Make narrow changes.
4. Do not perform broad uncontrolled refactors.
5. Do not invent fake data flows.
6. Do not build features outside the current phase.
7. Do not hide mock data as real functionality.
8. Clearly label mocked vs real behavior.
9. After changes, list files changed and how to test.
10. If unsure, ask before major architecture changes.

## Current North Star

The first real milestone:

A user can import existing backtest results, view the run dashboard, inspect trades, open replay, and compare the imported run to live-monitor status.

No new feature matters until this works.
