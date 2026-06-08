# Repo Guide

How my trading repos fit together. Read this first.

## The three layers

1. **BacktestStation** (this repo) — **Research lab + universal tooling.**
   Where I research strategies and where reusable test infrastructure lives:
   the backtest engine, tick replay, Monte Carlo, the data warehouse, feature
   detectors, prop-firm simulator. Can hold multiple research projects
   (e.g. `market_state/`, `experiments/*`). **Nothing here trades live.**
   Remote: `benbrainard11-netizen/BacktestStation`.

2. **Per-strategy live repos** — **Execution.**
   When research graduates into a live strategy, it gets its **own repo**. The
   current one is `live_engine/` (the Mira model turned into a live bot —
   remote `benbrainard11-netizen/live-engine-mira`, currently nested inside
   BacktestStation). Future strategies → their own `live-engine-<name>` repos,
   each self-contained for deployment (model frozen + detection code vendored).

3. **InsyncAPP** — **The trading platform** (shared with Husky).
   Where live strategies/bots plug in, run, and are visualized; manages
   prop-firm accounts. The production control center. Vue 3 + Tauri 2.
   Remote: `huskyfv/InsyncAPP`.

## Flow

```
research/test in BacktestStation  ->  graduate a strategy into its own live repo  ->  plug that bot into InsyncAPP to run, watch, and manage accounts
```

## Where new work goes

- New research or a new reusable tool → **BacktestStation**
- Productionizing a strategy for live trading → **new `live-engine-<name>` repo**
- Running / visualizing / managing live bots & prop accounts → **InsyncAPP**

## Canonical docs per repo

Minimalist by design. If a doc isn't in this list, it was intentionally cut —
check git history to recover.

### BacktestStation
- `README.md`, `CLAUDE.md` / `AGENTS.md` (agent rules), `REPO_GUIDE.md` (this file)
- `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/PROJECT_STATE.md`
- Reference: `docs/SCHEMA_SPEC.md`, `docs/DATA_FORMAT.md`, `docs/LOCAL_INFRASTRUCTURE.md`,
  `docs/BACKTEST_ENGINE.md`, `docs/MBO_TRADING_DAY_CONTRACT.md`
- Ops: `docs/R2_SETUP.md`, `docs/R2_READER_GUIDE.md`, `docs/SERVER_DEPLOYMENT.md`
- `experiments/_INDEX.md` + per-active-experiment READMEs
- Per-project READMEs (`market_state/`, etc.) and code-adjacent module READMEs

### Per-strategy live repos (live_engine, …)
- `README.md`, `DEPLOY.md`, `docs/ARCHITECTURE.md`, `docs/BUILD_PLAN.md`

### InsyncAPP
- `README.md`, `CLAUDE.md`, `BEN_PERSONAL_BRANCH.md`, per-service READMEs
