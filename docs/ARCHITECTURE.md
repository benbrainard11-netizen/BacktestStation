# BacktestStation — Architecture

> **Read [`../REPO_GUIDE.md`](../REPO_GUIDE.md) first** for how the three repos fit together
> (research lab → per-strategy live repos → InsyncAPP platform). This doc is the *internal*
> architecture of the research lab. For direction see [`ROADMAP.md`](ROADMAP.md); for current
> state [`PROJECT_STATE.md`](PROJECT_STATE.md); for engineering rules [`../CLAUDE.md`](../CLAUDE.md).

---

## 0. What the lab is for

A local-first quant research environment for futures. The job: **find edges that survive honest,
out-of-sample, no-lookahead testing**, then graduate the winners into their own live repos.
**Nothing here trades live.**

Two kinds of thing live here:
1. **Universal tooling** — reusable research/test infrastructure: the backtest engine, tick replay,
   Monte Carlo / prop-firm simulation, the data warehouse + ingest, feature detectors, the validation harness.
2. **Research projects** — the actual hunts: `experiments/*` and `market_state/`. See
   [`../experiments/_INDEX.md`](../experiments/_INDEX.md) for the live list + verdicts.

### The one rule (research)
Every signal/label/edge earns its place **only by predicting a forward outcome, OOS, no-lookahead.**
Gorgeous labels that don't predict the next move are the central trap (that's what chart-pattern ICT
was — it dissolved on every honest test). The **validation harness is the center of the lab, not an
afterthought.** Structural/microstructure edges (MBO order flow, cross-asset RV cointegration, vol
regime) have held; chart-pattern / index-context prediction keeps dying. Build on the former.

---

## 1. The three layers

| Layer | Repo | Role |
|---|---|---|
| Research + tools | **BacktestStation** (this) | research, backtesting, the data warehouse, reusable tooling |
| Execution | **`live-engine-<name>`** (one per strategy) | a graduated strategy as a live bot. `live_engine/` = Mira (the first) |
| Platform | **InsyncAPP** | plug in the live bots, run them, visualize, manage prop-firm accounts |

Flow: **research/test here → graduate a winner into its own live repo → plug that bot into InsyncAPP.**

---

## 2. System architecture (internals)

```
+----------------+      +-----------------+      +--------------------+
|  Next.js UI    | <--> |  FastAPI        | <--> |  SQLite (meta)     |
|  (local research)| REST|  (Python 3.12)  |      |  Parquet (data)    |
+----------------+      +--------+--------+      |  DuckDB (query)    |
                                 |               +--------------------+
                                 v
                       +-------------------+
                       |  Backtest Engine  |  pure Python, no I/O deps
                       +-------------------+
                                 |
                                 v
                       +-------------------+
                       |  DBN / Parquet    |  D:\data warehouse (append-only)
                       +-------------------+
```

- Frontend ↔ backend over REST (a local research UI, not the production platform — that's InsyncAPP).
- Backend orchestrates engine, ingest, storage, and services.
- The engine is a **pure library** (no DB, no HTTP) — unit-testable in isolation, runnable in a notebook.
- Shared types: Pydantic → `shared/openapi.json` → generated `frontend/lib/api/generated.ts`. Never hand-written twice; regenerate with `bash scripts/generate-types.sh`.

---

## 3. Folder structure

```
BacktestStation/
├── backend/
│   ├── app/
│   │   ├── api/         FastAPI routers (one per resource)
│   │   ├── engine/ backtest/   pure event/bar engine + bracket-order broker + runner
│   │   ├── strategies/ strategy ports (dumb: events in, signals out)
│   │   ├── ingest/     Databento DBN -> Hive parquet (historical, live, gap-filler, R2 upload)
│   │   ├── storage/ data/      warehouse readers, schema, partitioning
│   │   ├── db/         SQLAlchemy models + guarded migrations (meta.sqlite)
│   │   ├── schemas/    Pydantic — single source of truth for the API + TS types
│   │   ├── services/   drift monitor, prop-firm sim, dataset scanner, R2
│   │   ├── features/ research/ order-flow / volume-profile / HTF detectors
│   │   └── cli/        operational CLIs
│   └── tests/          engine determinism, lookahead harness, MBP-1 race, drift, …
├── frontend/           Next.js + Tauri local research UI
├── shared/openapi.json generated, committed
├── experiments/        research lines (see _INDEX.md) — cross-reference by path, don't move
├── market_state/       the broad market-state model (greenfield, validation-first)
├── live_engine/        SEPARATE repo (Mira live bot) nested here
├── client/bsdata/      external warehouse reader (R2-then-local-cache)
├── strategy_lab/        export / publication helpers
├── scripts/            launch + scheduled-task + ops scripts
├── docs/               this folder (minimalist — see REPO_GUIDE.md)
└── data/               gitignored: meta.sqlite + staging (RAW data lives on D:\data)
```

---

## 4. Data architecture

- **RAW market data lives on `D:\data\`** — append-only, never modified, never in the repo. Databento DBN → Hive-partitioned parquet mirror (`symbol=/date=`). See [`SCHEMA_SPEC.md`](SCHEMA_SPEC.md), [`DATA_FORMAT.md`](DATA_FORMAT.md).
- **`data/meta.sqlite`** (~40 GB, 29 tables) — research/ops metadata: backtest_runs, trades, equity_points, research_events, experiments, prop_firm_simulations, datasets, live_signals, etc. The working DB — **never delete it.**
- **DuckDB** — query-over-parquet, no persistent DuckDB file.
- **Cloud mirror** — Cloudflare R2 for cross-machine reads via `client/bsdata`. See [`R2_SETUP.md`](R2_SETUP.md), [`R2_READER_GUIDE.md`](R2_READER_GUIDE.md).
- **Disposable** (safe to delete): `data/meta.sqlite.*.bak` snapshots, `experiments/_archive/`. RAW on `D:\data` is the irreplaceable copy.

---

## 5. Engine correctness — the non-negotiables

These mirror [`../CLAUDE.md`](../CLAUDE.md) and are enforced by tests. They are why a backtest here can be trusted.

- **Pure engine.** No imports from `api/`, `db/`, `storage/`, `ingest/`. Events/bars in, results out.
- **Strategies are dumb.** Events in, signals out. No DB/HTTP/file I/O, no globals.
- **No lookahead.** Strategies only see data up to the current timestamp (`history_up_to(ts)`). A harness test asserts a peeking strategy raises.
- **Honest stop-vs-target fills.** When MBP-1 trade sequence is available, whichever side printed first wins (`fill_confidence=exact`). When ambiguous, **stop wins** (conservative); every run records `ambiguous_fill_count`.
- **Determinism.** Same inputs → byte-identical `equity.parquet` + `trades.parquet`. Test enforces.
- **Reproducibility.** Every run stores backend git SHA, engine version, params JSON, dataset sha256.
- **Named constants.** Contract value, tick, commission, session hours, slippage in a typed config.

See [`BACKTEST_ENGINE.md`](BACKTEST_ENGINE.md) for engine internals and how to write a strategy.

---

## 6. The validation harness

The center of gravity. Before any edge is believed it must forward-test **signal→label** and
**label→outcome** OOS, no-lookahead. Proven tooling: tick-by-tick MBP-1 re-fill (honest entry+stop),
OOS exit-replay, milkability Monte Carlo, and the prop-firm fleet sims in `experiments/sizing_v1`.
`market_state/validation/` is being built first, before any model. A label that can't forward-validate
does not get added.
