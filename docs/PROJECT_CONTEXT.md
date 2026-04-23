# BacktestStation Project Context

BacktestStation is a local-first futures trading research and monitoring app.

The user is building this with AI coding agents and wants a clean, understandable codebase.

## User Context

The user:

- Trades futures, especially NQ/ES-style strategies
- Already has a coded/backtested strategy
- Has a strategy live-testing now
- Has Databento access
- Has a 24/7 PC available for collecting/logging data
- Wants a polished research/control dashboard
- Wants deep analytics, replay, live monitoring, and eventually stronger backtesting/ML/regime tools

This is not a greenfield "find an edge from nothing" project.

The correct mental model:

BacktestStation should first wrap the user's existing strategy outputs in a serious research/control framework.

## Product Vision

BacktestStation should become a sleek dark quant dashboard for:

- Importing existing backtest results
- Viewing performance analytics
- Comparing strategy versions/configs
- Reviewing individual trades
- Replaying trades on charts
- Monitoring live strategy status
- Recording research notes
- Detecting live/backtest mismatch
- Later running a clean Databento/MBP-1 event-driven backtesting engine

## Correct Build Sequence

Original idea was:

Engine -> Databento pipeline -> Backtest workflow -> Dashboard

Updated correct sequence:

App shell -> Existing-results importer -> Analytics dashboard -> Replay -> Live monitor -> Cleaner engine later

Reason:

The user already has results and live testing. The app becomes valuable faster if it imports and analyzes current outputs first.

## Core Entities

Initial entities:

- Strategy
- StrategyVersion
- BacktestRun
- Trade
- EquityPoint
- RunMetric
- ConfigSnapshot
- LiveSignal
- LiveHeartbeat
- Note
- TradeTag

Later entities:

- Dataset
- DataQualityReport
- EngineRun
- ValidationReport
- RegimeLabel
- ModelScore

## Key Product Questions

The app should help answer:

1. Is the strategy still behaving like expected?
2. Which version/config is best?
3. Where does the strategy work or fail?
4. Is live performance matching backtest?
5. Are changes improving the system or curve-fitting?
6. Which trades/setups should be studied manually?
7. What should be tested next?

## ML Positioning

ML is not Phase 1.

Use ML later for:

- Regime labeling
- Setup scoring
- Trade clustering
- Degradation detection
- Filtering bad environments

Avoid early:

- Direct price prediction
- Replacing the strategy
- Optimizing 100 parameters
- Building ML before the data/import/dashboard foundation exists
