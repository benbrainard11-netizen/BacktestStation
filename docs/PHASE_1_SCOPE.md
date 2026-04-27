# Phase 1 Scope

> **Status (2026-04-27): Phase 1 shipped.** This doc remains as the historical record of the original Phase 1 (Imported Results Command Center) scope and done-criteria. For *current direction*, see [`ROADMAP.md`](ROADMAP.md). For *what's running today*, see [`PROJECT_STATE.md`](PROJECT_STATE.md).

## Phase 1 Name

Imported Results Command Center

## Objective

Build a useful app around existing strategy outputs before building the full backtesting engine.

The app should allow the user to import current backtest/live files and inspect them through a polished dark quant dashboard.

## Must Build

### Backend

Use FastAPI.

Required endpoints:

- GET /api/health
- POST /api/import/backtest
- GET /api/strategies
- GET /api/strategies/{id}
- GET /api/backtests
- GET /api/backtests/{id}
- GET /api/backtests/{id}/trades
- GET /api/backtests/{id}/equity
- GET /api/backtests/{id}/metrics
- GET /api/monitor/live

### Database

Use SQLite first.

Required tables:

- strategies
- strategy_versions
- backtest_runs
- trades
- equity_points
- run_metrics
- config_snapshots
- live_signals
- live_heartbeats
- notes

### Importer

Support sample files:

- trades.csv
- equity.csv
- metrics.json
- config.json
- live_status.json

Normalize imports into the database.

Do not just show hardcoded mock cards forever. Mock data is allowed for UI scaffolding only, but Phase 1 must end with imported data powering the dashboard.

### Frontend

Use Next.js + TypeScript + Tailwind.

Required pages:

- /
- /import
- /strategies
- /strategies/[id]
- /backtests
- /backtests/[id]
- /backtests/[id]/replay
- /monitor
- /journal

### Dashboard Metrics

Show:

- Net PnL
- Net R
- Win rate
- Profit factor
- Max drawdown
- Average R
- Average win
- Average loss
- Trade count
- Longest losing streak if available
- Best trade
- Worst trade

### Charts

Show:

- Equity curve
- Drawdown curve
- R-multiple distribution if trade data supports it
- Day/session breakdown later if fields exist

### Trade Table

Columns:

- Entry time
- Exit time
- Symbol
- Side
- Entry price
- Exit price
- Stop
- Target
- Size
- PnL
- R multiple
- Exit reason
- Tags/session/setup

### Trade Replay

Phase 1 replay can be simple:

- Show trade details
- Show entry/exit/stop/target fields
- Use mock candle chart if candle data is not imported yet
- Clearly label if chart data is mocked

Later replay should use real candle/tick data.

### Live Monitor

Read a local JSON status file first.

Show:

- Strategy status
- Last heartbeat
- Current symbol
- Current session
- Today PnL
- Today R
- Trades today
- Last signal
- Last error

## Must Not Build In Phase 1

- Databento ingestion
- Full backtest engine
- MBP-1 fill simulation
- Live broker execution
- ML models
- SaaS auth/billing
- Deployment/cloud work
- No-code strategy builder

## Done Criteria

Phase 1 is done when:

1. App runs locally.
2. Backend health endpoint works.
3. User can import sample backtest files.
4. Imported run appears in /backtests.
5. Run detail page shows real imported metrics.
6. Trade table shows imported trades.
7. Equity/drawdown chart uses imported equity data.
8. Replay page can open a selected trade.
9. Monitor page reads local JSON status.
10. README explains how to run everything.
