# BacktestStation — Architecture

> **⚠ Roadmap override (current).** This document was written assuming an **engine-first** Phase 1 (build the MBP-1 backtester before anything else). That ordering has been **superseded**.
>
> For current Phase 1 work, the source of truth is:
> - [`AGENTS.md`](../AGENTS.md) — agent rules and current build order
> - [`docs/PHASE_1_SCOPE.md`](PHASE_1_SCOPE.md) — explicit Phase 1 scope and done-criteria
> - [`docs/PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — project context
>
> **Phase 1 is now "Imported Results Command Center"**: import existing backtest/live result files (CSV/JSON) and surface them through the dashboard. The Databento ingestion pipeline and the event-driven MBP-1 engine described below are deferred until that vertical slice is working.
>
> Sections 4–7 (database schema, Databento ingestion, engine design) and the §12 phase ordering still describe the eventual end-state — useful as long-term reference, not as the next step.

---

## 0. Vision

BacktestStation is a local-first strategy development workstation for futures strategies. It supports the full research loop:

**idea → thesis → rules → version → experiment → backtest → analysis → decision → forward/live monitor → refine**

The AI layer is a research assistant, not an autonomous trader. AI suggestions land as human-reviewed notes, experiments, and decisions — never automatic strategy changes.

### Scope

- **Shipped on `main`:** Strategy Library, imported backtest runs + metrics + autopsy + compare, CSV export, prop-firm simulator, data-quality report, tags editor.
- **In progress (on branch, pre-merge):** Strategy Lifecycle Pipeline, Strategy Dossier page (initial version — will grow to include research, experiments, risk profile, live monitor, AI context), archive-not-delete at strategy + version level, board ↔ table toggle on `/strategies`, latest-run metrics panel.
- **Next (after the in-progress branch merges):** Research Workspace, Experiment Ledger.
- **Later:** AI Prompt Generator, Forward/Live Drift Monitor, Risk Profile Manager, In-App Strategy Engine.

### Current phase

Strategy lifecycle foundation: pipeline board, manual strategy creation, strategy versions, lifecycle stages, linked imported runs, archive-not-delete semantics at both strategy and version level. Status: working tree on `task/strategy-editor-pipeline`, not yet merged to `main`.

### Next phase

**Research Workspace** — extend the existing `Note` model (`backend/app/db/models.py` — currently attaches to `backtest_run_id` / `trade_id`). Add:
- `strategy_id` (FK, nullable)
- `strategy_version_id` (FK, nullable)
- `note_type` with vocabulary `observation, hypothesis, question, decision, bug, risk_note`
  - No `ai_idea` type until AI generation exists
- `tags` (JSON list)

Expose `NOTE_TYPES` through a `GET /api/notes/types` endpoint that mirrors the `STRATEGY_STAGES` pattern.

**Experiment Ledger** — new `Experiment` table, minimal shape:
- `id`
- `strategy_version_id` (FK, required)
- `hypothesis` (text, required)
- `baseline_run_id` (FK, nullable)
- `variant_run_id` (FK, nullable)
- `change_description` (markdown text — freeform, no structured sub-fields at this scale)
- `decision` (enum: `pending, promote, reject, retest, forward_test, archive`)
- `notes` (text)
- `created_at`, `updated_at`

Expose `EXPERIMENT_DECISIONS` as a vocabulary endpoint.

### Acceptance criteria for next phase

**Research Workspace is done** when a user can:
- create, edit, and delete a note attached to any of: strategy, strategy version, backtest run, trade
- pick a `note_type` at creation time from the `NOTE_TYPES` vocabulary
- add free-form tags
- filter notes on the strategy dossier by `note_type` and by tag
- see notes grouped by target (strategy-level vs version-level vs run/trade-level)

**Experiment Ledger is done** when a user can:
- create an experiment from the strategy dossier, picking a `strategy_version_id`
- write a hypothesis and a markdown change description
- link a `baseline_run_id` and an optional `variant_run_id` from runs already imported under that strategy
- record a `decision` from the `EXPERIMENT_DECISIONS` vocabulary
- view all experiments for a strategy from the dossier page

### AI direction

First AI feature is a **Research Prompt Generator**, not chat:
- User picks a mode: Researcher, Critic, Statistician, Risk Manager, Engineer, Live Monitor
- App bundles strategy context, version rules, recent notes, metrics, data quality, autopsy, linked runs
- Output is a copyable prompt for Claude or GPT, run externally
- Later: paste the response back as a note, experiment, or decision

Model-agnostic from day one. No local-model lock-in, no specific API commitment. Possible modes later: private/redacted/full-context.

The Prompt Generator is the first feature of an eventual **AI Command Center** layer. The full long-arc vision for that layer is captured (docs-only, non-binding) in:
- [`AI_COMMAND_CENTER_SPEC.md`](AI_COMMAND_CENTER_SPEC.md) — umbrella spec
- [`AI_MEMORY_AND_KNOWLEDGE_DESIGN.md`](AI_MEMORY_AND_KNOWLEDGE_DESIGN.md) — memory categories (mostly already covered by existing models)
- [`AI_AGENT_MODES.md`](AI_AGENT_MODES.md) — possible future modes
- [`AI_LOCAL_CLOUD_WORKFLOW.md`](AI_LOCAL_CLOUD_WORKFLOW.md) — local + cloud composition
- [`AI_ROADMAP.md`](AI_ROADMAP.md) — phased roadmap, gated by triggers, not dates

Those docs are **vision capture, not implementation commitments.** Phase 1 here remains the priority; AI Command Center work doesn't start until the triggers in the roadmap fire.

### Safety rules

- Database + metrics are source of truth. AI output is never authoritative.
- No destructive cascade delete for strategies or strategy versions with attached data. Archive/retire first.
- Existing import, backtest detail, compare, and autopsy pages must keep working as new features land.
- AI suggestions become human-reviewed notes, experiments, or decisions — never auto-applied.

### Build order

1. Strategy lifecycle pipeline — ✓ shipped
2. Strategy Dossier page — ✓ shipped (initial version; will expand in later phases)
3. Linked imported runs — ✓ shipped
4. Research Workspace (Note model extended) — ✓ shipped
5. Experiment Ledger (new `Experiment` table) — ✓ shipped
6. AI Prompt Generator — ✓ shipped
7. Data warehouse layer (Hive parquet, manifests, reader API) — ✓ shipped
8. Backtest engine v1 (bar-based, single-position, bracket orders) — ✓ shipped (see [`BACKTEST_ENGINE.md`](BACKTEST_ENGINE.md))
9. Port real strategies as engine plugins (Fractal AMD first)
10. Forward/live drift monitor
11. Risk Profile Manager
12. Tick-replay engine (Level 2)
13. MBP-1 order book replay (Level 3)

---

## Context

Solo beginner (using AI tools) building a futures-trading research/control center. Porting a real live-running strategy that uses **stop-loss + take-profit brackets**, ingesting **MBP-1 tick data** from Databento from day one, **monorepo** layout, full 12-item MVP on a stretched ~14-week timeline. Design prioritizes backtest correctness over UI polish.

The combination of (beginner + MBP-1 + OCO brackets + full MVP scope) means engine correctness is where we spend the most care; UI is mostly scaffolding shadcn components.

---

## 1. Product summary

Local-first research terminal for futures strategies: ingest Databento → validate → register strategies → backtest with realistic OCO fills on MBP-1 data → analyze → replay trades → monitor a live instance. Single-user for now, monorepo, runs locally, Docker optional later.

---

## 2. System architecture

```
+-------------------+       +--------------------+       +-------------------+
|  Next.js UI       | <---> |  FastAPI           | <---> |  SQLite (meta)    |
|  (dashboard)      | HTTPS |  (Python 3.12)     |       |  Parquet (data)   |
+-------------------+       +---------+----------+       |  DuckDB (query)   |
                                      |                  +-------------------+
                                      v
                            +-------------------+
                            |  Backtest Engine  |  pure Python, no I/O deps
                            |  (event-driven)   |
                            +-------------------+
                                      |
                                      v
                            +-------------------+
                            |  DBN / Parquet    |
                            |  raw market data  |
                            +-------------------+
```

- Frontend ↔ backend over REST.
- Backend orchestrates engine, ingestion, storage.
- Engine is a pure library (no DB, no HTTP), unit-testable in isolation.
- Shared types: Pydantic → `openapi.json` → `openapi-typescript` → TS types. Never hand-written twice.

---

## 3. Folder structure

```
BacktestStation/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers, one per resource
│   │   ├── core/             # config, logging, paths
│   │   ├── db/               # SQLAlchemy models, session, migrations
│   │   ├── engine/           # pure engine, no I/O
│   │   │   ├── events.py
│   │   │   ├── strategy.py
│   │   │   ├── broker.py
│   │   │   ├── runner.py
│   │   │   └── strategies/
│   │   │       └── my_strategy.py
│   │   ├── ingest/           # Databento → DBN → Parquet
│   │   ├── storage/          # DuckDB / Parquet helpers
│   │   └── schemas/          # Pydantic — single source of truth
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/                  # Next.js app router
│   ├── components/           # ui/ (shadcn), charts/, tables/
│   ├── lib/api/              # generated TS client — do not edit
│   └── package.json
├── shared/
│   └── openapi.json          # generated, committed
├── data/                     # gitignored
│   ├── raw/                  # DBN files
│   └── parquet/              # converted
├── scripts/
│   └── generate-types.sh
├── README.md
└── CLAUDE.md
```

---

## 4. Database schema (SQLite → Postgres later if needed)

- **strategies** (id, name, slug UNIQUE, description_md, status[idea|testing|live|retired], tags[], created_at)
- **strategy_versions** (id, strategy_id, version, entry_md, exit_md, risk_md, git_commit_sha, created_at)
- **datasets** (id, symbol, dataset_code, schema_kind[mbp-1|ohlcv-1m|...], start_ts, end_ts, file_path, row_count, sha256, created_at)
- **data_quality_reports** (id, dataset_id, gaps_json, duplicates_count, checked_at)
- **backtest_runs** (id, strategy_version_id, dataset_id, params_json, git_commit_sha, engine_version, status, started_at, completed_at, results_dir)
- **trades** (id, backtest_run_id, entry_ts, exit_ts, side, entry_price, exit_price, size, stop_price, target_price, exit_reason[stop|target|eod|manual], pnl, r_multiple, tags[])
- **notes** (id, backtest_run_id NULL, trade_id NULL, body_md, created_at)
- **live_signals** (id, strategy_version_id, ts, side, price, reason, executed_bool) — written by the 24/7 PC

Equity curves stored as Parquet at `data/results/{backtest_run_id}/equity.parquet`, not in SQLite.

---

## 5. Data storage design

- **Raw DBN**: `data/raw/{dataset}/{symbol}/{YYYY-MM-DD}.dbn.zst` — unchanged from Databento.
- **Parquet mirror**: `data/parquet/{symbol}/{schema}/{YYYY-MM-DD}.parquet` — zstd-compressed, Arrow-friendly, per-day partitioning for fast range queries.
- **DuckDB**: query-over-files, no persistent DuckDB file.
- **SQLite** at `data/meta.sqlite` for metadata only.

DBN is immutable source-of-truth. Parquet is derived and rebuildable.

---

## 6. Databento ingestion design

CLI (`python -m app.ingest`) and API (`POST /api/ingest/databento`) share identical logic:

1. `historical.timeseries.get_range({dataset, symbols, start, end, schema})`
2. Stream DBN to `data/raw/...` (resumable, checksummed)
3. Convert to Parquet day-by-day via the `databento` client's Arrow export
4. Register in SQLite, compute sha256, store row count
5. Run data quality check

Quality checks:
- **Gaps**: consecutive timestamps further apart than expected
- **Duplicates**: exact timestamp collisions per symbol
- **Out-of-order**: strictly-increasing timestamp assertion
- **Halt detection**: long gaps during RTH that aren't scheduled sessions
- Results stored in `data_quality_reports`

---

## 7. Backtest engine design

**Style:** event-driven, single-threaded, deterministic. Not vectorized — vectorized engines are harder to get right with OCO brackets on tick data.

**Event types:**
- `TickEvent` — MBP-1 snapshot (ts, bid, ask, bid_size, ask_size, last_trade_price, last_trade_size)
- `BarEvent` — optional aggregated bar
- `SignalEvent`, `OrderEvent`, `FillEvent`

**Event loop (`runner.py`):**
```
for event in stream:          # strictly increasing timestamps
    strategy.handle(event)    # may emit signals
    broker.handle(event)      # may emit fills; resolves OCO brackets
    portfolio.update(event)
```

**Strategy contract (`strategy.py`):**
- `on_tick(tick)` / `on_bar(bar)`
- `self.emit_bracket(side, size, stop, target)` — primary API
- No access to future data, DB, or filesystem. Only events + own state.

**Broker (`broker.py`):**
- Entry: market order fills at next tick's ask (buy) or bid (sell) + configurable slippage.
- OCO bracket: each subsequent tick, check whether stop or target would trigger.
  - **Critical MBP-1 rule**: if both could fill within the same window, resolve using the actual MBP-1 trade sequence. Whichever side of the book printed first wins. This is THE correctness point for tick-based futures backtesting.
  - Never let fill price be better than what the book showed.
- Commission + slippage are explicit config values.

**Reproducibility:**
- Every run stores: backend git SHA, engine version, params JSON, dataset sha256, seed.
- Run twice → byte-identical `equity.parquet` and `trades.parquet`. Test enforces this.

**Lookahead prevention:**
- Engine exposes only `history_up_to(ts)` accessors, not raw DataFrames.
- Harness test: inject a strategy that tries to peek ahead, assert engine raises.

---

## 8. API endpoint plan (MVP)

```
POST /api/ingest/databento
GET  /api/datasets
GET  /api/datasets/{id}

POST /api/strategies
GET  /api/strategies
GET  /api/strategies/{id}

POST /api/backtests
GET  /api/backtests
GET  /api/backtests/{id}
GET  /api/backtests/{id}/equity
GET  /api/backtests/{id}/trades
GET  /api/backtests/{id}/bars

POST /api/notes
GET  /api/notes

GET  /api/monitor/live
```

Background execution: FastAPI `BackgroundTasks` to start; upgrade to `arq` only if runs get long. All responses use Pydantic models, never raw dicts.

---

## 9. Frontend pages / components

Pages (Next.js app router):
- `/` — Command Center
- `/data` — Data Vault
- `/strategies`, `/strategies/[id]`
- `/backtest` — Workbench
- `/backtests`, `/backtests/[id]`, `/backtests/[id]/replay`, `/backtests/[id]/validation`
- `/monitor`

Shared components:
- `components/ui/` — shadcn primitives
- `components/charts/EquityCurve.tsx`, `DrawdownCurve.tsx` — Recharts
- `components/charts/TradingViewChart.tsx` — Lightweight Charts + markers + stop/target lines
- `components/tables/TradeTable.tsx` — virtualized (tanstack-table + tanstack-virtual)
- `components/layout/Sidebar.tsx`, `TopBar.tsx`

---

## 10. UI design system

- Tailwind: `zinc-950` bg, `zinc-100` fg, `zinc-800` borders, `zinc-400` muted.
- Accents: `emerald-400` gains, `rose-400` losses. No other accent colors.
- Fonts: Inter for UI, JetBrains Mono for numbers & tables.
- Density: table rows 32px, card padding 16px, no shadows, 1px borders.
- Charts: dark background, grid lines ~6% white, axis `zinc-500`.
- No gradients, no rounded-3xl, no emoji.

---

## 11. Testing plan

Engine tests (most important):
1. **Known-result fixture** — synthetic 200-tick dataset, hand-calculated expected trades.
2. **Lookahead harness** — strategy peeks ahead, engine raises.
3. **Determinism** — run twice, byte-compare Parquet outputs.
4. **MBP-1 stop-vs-target race** — both levels in range, assert actual trade sequence wins.
5. **EOD flatten** — open position at close, forced exit.
6. **Slippage / commission** — same trades, different config, expected P&L deltas.

API: pytest + httpx against temp SQLite.
Frontend: one Playwright smoke test (create strategy → run backtest → see result).
CI (later): GitHub Actions with ruff + black + pytest + `npm run build` + playwright.

---

## 12. MVP roadmap (~14 weeks)

**Phase 0 — Foundations (weeks 1–2)**
Monorepo scaffold, pyproject.toml, package.json, pre-commit (ruff/black/prettier), SQLite + SQLAlchemy + Alembic, Pydantic → OpenAPI → TS codegen pipeline, UI shell with sidebar/dark theme/routing stubs.

**Phase 1 — Engine (weeks 3–5)** ← highest-risk work
Events, event loop, strategy base, broker with OCO. Port live strategy. All 6 engine tests green.

**Phase 2 — Data pipeline (weeks 6–7)**
Databento ingestion CLI + API. DBN → Parquet. Quality checker. `/data` page.

**Phase 3 — Backtest workflow (weeks 8–9)**
Runner wired to API with background execution. `/backtest` workbench. Results storage.

**Phase 4 — Results + Replay (weeks 10–12)**
Results dashboard (equity, drawdown, stats, trade table). TradingView replay with OCO lines. Compare two runs.

**Phase 5 — Command Center + Monitor (weeks 13–14)**
`/` dashboard. `/monitor` reads JSON written by the 24/7 PC. Notes system.

---

## 13. What NOT to build yet

Auth, users, billing. Docker, Kubernetes, cloud deploy. Walk-forward, Monte Carlo, overfitting detection (Validation Lab gets placeholders only). Broker execution integration. No-code strategy builder. Websocket real-time streams (use polling). Postgres. Non-futures asset classes. Mobile UI. Strategy plugin framework.

---

## 14. Risks & anti-spaghetti rules

- **Engine is pure.** No imports from `api/`, `db/`, `storage/`. Takes events in, returns results. Runnable in a notebook.
- **Strategies are dumb.** No DB, HTTP, or file I/O inside a strategy. Events in, signals out.
- **Schemas single-source.** Pydantic in `backend/app/schemas/`, never redefined on frontend.
- **No hand-written API clients.** Regenerate after every schema change.
- **All magic numbers named.** Contract value, tick size, commission, session hours in a typed config.
- **Every backtest reproducible.** Git SHA + data sha256 + params JSON stored with every run. Non-negotiable.
- **Parquet, never pickle.**
- **No premature abstractions.** One strategy → one class. Don't build a framework until three exist.
- **300-line / 60-line rule.** Split anything larger.
- **MBP-1 reality check.** NQ MBP-1 is ~1 GB/month raw. Plan for 10–50 GB of local storage. Slow queries? Parquet partitioning is the lever, not Postgres.

---

## Verification per phase

- **Phase 1**: `pytest backend/tests/test_engine_*.py` — all green, including MBP-1 race test.
- **Phase 2**: import 1 week NQ MBP-1, appears in `/data`, quality report shows expected gap count.
- **Phase 3**: submit backtest via `/backtest`, appears in `/backtests`, status completes.
- **Phase 4**: open `/backtests/[id]`, see equity curve + trades, replay shows correct stop/target lines. Compare two runs side-by-side.
- **Phase 5**: `/` shows last run + today's signals + data health. `/monitor` reflects 24/7 PC's last JSON write.

Final smoke: run same backtest twice, `diff` the two `equity.parquet` files → empty.
