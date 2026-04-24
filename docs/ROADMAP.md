# BacktestStation Roadmap

> Source of truth for **product direction**. Update when a decision changes.
> Paired with [`AGENTS.md`](../AGENTS.md) (agent rules), [`PHASE_1_SCOPE.md`](PHASE_1_SCOPE.md) (frozen Phase 1 spec), and [`ARCHITECTURE.md`](ARCHITECTURE.md) (system design / eventual end-state).
>
> Last updated: 2026-04-24 (Phase 2 closed)

---

## 1. What this is

BacktestStation is a local-first futures-strategy research and control terminal.

Plug any strategy into it, import that strategy's result files (trades, equity, metrics, config), inspect them through a dark quant dashboard, replay individual trades, and monitor a live instance. A real event-driven backtest engine on Databento tick data comes later — the first goal is making the strategy results you *already have* easy to look at, compare, and trust.

Personal tool first. Productization is a possible future — not a committed path.

---

## 2. Vision

1. **Any strategy plugs in.** Same dashboard, same import workflow, same analytics — whether the strategy is Fractal AMD, ORB, VWAP mean-reversion, or a future ML-based thing.
2. **Live and backtest live on the same surface.** Imported backtest results and live-bot output flow into the same tables, charts, and pages. Divergence between the two is obvious because they're compared in the same UI.
3. **Engine perfection later, imported-data correctness now.** The first priority is correctly importing, storing, displaying, and comparing existing strategy outputs. Do not fake data or hide mock behavior. The deterministic engine answers "is my strategy actually doing what the backtest said?" — but it's built *after* the imported-results loop feels solid, not before.

---

## 3. Where we are (as of 2026-04-23)

### Backend
- FastAPI + SQLAlchemy + SQLite. Python 3.12+.
- 10 endpoints live: health, import/backtest, strategies list/detail, backtests list/detail/trades/equity/metrics, monitor/live.
- 16 passing pytest tests, including one end-to-end test that imports the real Fractal sample bundle.
- 10 DB tables created. 3 of them (`live_signals`, `live_heartbeats`, `notes`) are schema-only — no writes yet.
- Importer handles `trades.csv`, `equity.csv`, `metrics.json`, `config.json`, `live_status.json`. Tolerates Fractal-specific quirks (BEARISH/BULLISH side, pnl_r, date+time split columns, missing symbol via config).

### Frontend
- Next.js 15 + React 19 + TypeScript + Tailwind + Tauri 2.
- Real data on: `/import`, `/backtests`, `/backtests/[id]`, `/backtests/[id]/replay`, `/backtests/compare`, `/monitor`, `/strategies`, `/strategies/[id]`.
- Placeholders remaining: `/data-health` and `/settings` — both now clearly labeled "PHASE 3 · NOT STARTED" with descriptive copy. All Phase 1-2 spec pages (`/`, `/import`, `/backtests*`, `/strategies*`, `/monitor`, `/journal`) are wired to real API data. Root `/replay` was deleted 2026-04-24.
- Built-in charts: equity curve, drawdown curve, R-multiple histogram, overlaid two-run equity comparison. Replay chart intentionally absent until Databento ticks land.

### Data
- `samples/fractal_trusted_multiyear/` — committed sample bundle derived from a real 586-trade Fractal AMD backtest.
- Local DB has 2 imported runs:
  - BT-1: Fractal AMD `trusted_multiyear` — 586 trades, +274.4R, 40.8% WR, 2024-01 → 2026-03.
  - BT-2: Fractal AMD `live_match_2022_2026` — 929 trades, +307R, 33.3% WR, 2022-01 → 2026-03. Matches live-bot config (MIN_RISK=8, no MAX_HOLD, BLOCK_OVERLAP applied).

### Scope discipline
None of these have been built yet, intentionally:
- Databento ingestion
- Event-driven backtest engine
- Live broker execution
- ML models
- Auth / billing / multi-tenant
- Mobile / cloud / Docker

---

## 4. Phase 2: Close out + polish — ✅ COMPLETE (2026-04-24)

All "Imported Results Command Center" edges have been sanded. Remaining convenience features (bulk import, delete, rename, CSV export) moved to Phase 3 scope since they're not structural.

### Shipped
- **`/journal` page** — `POST /api/notes` + `GET /api/notes` with optional run_id/trade_id filters, FK validation. Frontend page lists + creates notes, no mock data.
- **`/` Command Center real KPIs** — fetches `/api/backtests`, `/api/backtests/{latest}/metrics`, `/api/monitor/live`, `/api/notes` in parallel. Summary row, latest metrics panel, monitor panel, recent runs + notes. MockDataBanner and all 9 mock components deleted.
- **Root `/replay` deleted** — `/backtests/[id]/replay` is the only replay surface.
- **`/data-health` and `/settings`** — kept as EmptyState placeholders with clear "PHASE 3 · NOT STARTED" labels.
- **Graceful panel degradation** — a failed API endpoint now degrades the affected Command Center panel, not the whole page.
- **Sidebar/TopBar chrome** — fake CPU/MEM/DISK sparklines and "DB READY" pill removed. Version shown as static "Local build · v0.1.0" (honest about being hardcoded).

### Deferred to Phase 3 (see §5)
- Bulk import / re-import / overwrite-existing.
- Delete run, rename run, run favoriting/tagging.
- Export trades/metrics back to CSV.
- Shared `<ChartPlaceholder />` component.
- Pydantic → OpenAPI → TS type generation (biggest structural risk; promote to early Phase 3).

---

## 5. Phase 3: Databento ingestion

First "big" chunk. Turns the app from "analyze imported files" into "ingest tick data for yourself." Per [`ARCHITECTURE.md §6`](ARCHITECTURE.md).

### What gets built
- **CLI + API:** `POST /api/ingest/databento` — dataset code, symbol, date range → streams DBN to `data/raw/`, converts to Parquet per-day, registers in SQLite.
- **New tables:** `datasets` (id, symbol, schema_kind, start/end_ts, file_path, sha256, row_count), `data_quality_reports` (gaps, duplicates, out-of-order, halt detection).
- **`/data` page** — Data Vault showing what's been ingested, with quality reports visible.
- **Scripts:** `scripts/generate-types.sh` for Pydantic → OpenAPI → TS type codegen (promised by `ARCHITECTURE.md` but never written).

### Opens the door for
Phase 4's real backtests, since those need tick data to run against.

### Risks
- MBP-1 data is ~1 GB/month per symbol. Plan for 10-50 GB of local storage. Parquet partitioning is the only lever.
- The existing `lib/api/types.ts` hand-authored types will need to migrate to generated ones when a real codegen pipeline exists.

---

## 6. Phase 4: Event-driven backtest engine

The actual correctness goal. Per [`ARCHITECTURE.md §7 and §14`](ARCHITECTURE.md).

### What gets built
- Pure Python engine under `backend/app/engine/`. No I/O dependencies. No imports from `api/`, `db/`, `storage/`, `ingest/`.
- Event types: `TickEvent`, `BarEvent`, `SignalEvent`, `OrderEvent`, `FillEvent`.
- Strategy base with `on_tick` / `on_bar` and `emit_bracket(side, size, stop, target)` as the primary API.
- **Conservative-fill broker** with OCO bracket handling (see rules below).
- **Fractal AMD port** as the first concrete strategy. One real strategy validates the abstraction exists because it has something to abstract over.

### Stop-vs-target fill rules
The backtester must not pretend it knows something it doesn't.

1. **If trade-level sequence is available** (e.g., MBP-1 trades print in exact order within the window) — use it. The side that printed first wins.
2. **If the data is ambiguous** (both stop and target are reachable in the same window but trade order can't be determined, e.g., OHLC bars only) — resolve conservatively.
3. **Default conservative rule: stop wins.** Never pick the more-favorable outcome when it's not supported by the data.

Every trade must store a `fill_confidence` field:
- `exact` — trade-level sequence used, unambiguous resolution.
- `conservative` — ambiguous window, default-stop rule applied.
- `ambiguous` — flagged for review, stop used.

Every run summary records `ambiguous_fill_count` so runs with a lot of ambiguous fills are visible without digging into trades.

### Schema changes this introduces
- **`backtest_runs.source_type`** — `imported | internal_engine | live_replay`. One table serves all three so the dashboard is unified. Imported runs (Phase 1) use `imported`; engine runs use `internal_engine`; live-bot replay comparisons use `live_replay`.
- **`trades.fill_confidence`** — `exact | conservative | ambiguous`. Imported trades from Phase 1 source files get `exact` (we trust what the source produced). Engine-produced trades get whichever the broker determined.
- **`run_metrics.ambiguous_fill_count`** — integer count of `ambiguous` fills in the run.

### Correctness tests (all blocking)
- **Known-result fixture** — synthetic 200-tick dataset, hand-calculated expected trades.
- **Lookahead harness** — strategy that tries to peek ahead → engine raises.
- **Determinism** — run same backtest twice → byte-identical `equity.parquet` + `trades.parquet`.
- **Stop-vs-target fill decisions** —
  - Trade-level sequence available → `fill_confidence=exact`, correct side wins.
  - Ambiguous OHLC-only window with both levels reachable → `fill_confidence=conservative`, stop wins by default.
- **EOD flatten** — open position at session close → forced exit.

### What this resolves
The "3+ backtest files disagree, none call live bot's SignalEngine" divergence. When the engine is authoritative and the live bot runs the same strategy code, results converge.

---

## 7. Phase 5: Tick-level replay + validation lab

Payoff of Phases 3 + 4.

### What gets built
- **Real candle chart** on `/backtests/[id]/replay?trade=N`. Replaces the current "chart lands when Databento pipeline is wired" placeholder. Uses TradingView Lightweight Charts over Parquet bars.
- **Validation lab** (`/backtests/[id]/validation` or similar) — side-by-side live-vs-backtest for the same day. If the live bot took a trade the backtest didn't (or vice versa), the UI flags it.

### Why this matters
Answers the question the whole app exists to answer: "is my strategy actually doing what the backtest said?" — at the per-trade, per-tick level.

---

## 8. Phase 6+: Aspirational

Items that aren't committed, just flagged so they don't get re-invented. Park until earlier phases are solid.

- **Embedded LLM assistant.** Ben raised this. Could be any of:
  - Strategy research chatbot ("what was my win rate in Q2 2024 BEARISH setups?")
  - Auto-journal generator ("summarize what went wrong on April 19")
  - Divergence explainer ("why did the live bot skip this trade?")
  - Config-tuning suggester ("given these losses, what parameters would have helped?")

  Each is a different-sized project with different cost/latency trade-offs. Decide scope when we're ready to touch it.

- **Multi-asset.** ES, YM, MES, MNQ or other futures. Strategy/broker abstractions should already tolerate this; the work is more about data ingestion and symbol/tick-size config per instrument.
- **Walk-forward / Monte Carlo / overfitting detection.**
- **Strategy marketplace or plugin framework.** Not until at least 3 concrete strategies exist (per [`AGENTS.md`](../AGENTS.md) "no premature abstraction").
- **Productization.** Multi-tenant, auth, billing, hosted vs desktop-only. Only if Ben decides to sell it.

---

## 9. Work division

Five contributors, clear lanes.

| Who | Primary role | Also does |
|---|---|---|
| **Ben** | Product decisions, strategy logic, live trading validation. Approves merges. Calls scope. | Spots aesthetic problems ("looks like shit"), final judge on ship/no-ship. |
| **Husky** | Frontend polish, visual components, layout. | Backend tasks when needed — full-stack capable. |
| **Claude Code** | Backend, pipelines, wiring, tests, planning docs. Narrow per-branch tasks. | Writes documentation. Flags risks. |
| **Codex** | Audit mode — skeptical reviewer, spaghetti detector, scope enforcer. | Suggests exact next patches. Not a primary author. |
| **GPT-5.5 Chat** | Prompt drafter, spec writer. Turns Ben's ideas into exact Claude Code prompts. | Stress-tests assumptions. Reviews outputs. |

### Working loop
```
Ben (idea)
  → GPT-5.5 Chat (spec)
    → Claude Code (build on a new task/ branch)
      → Codex (audit)
        → Ben (decide merge)
```

Husky fills in parallel frontend work on his own task branches and hands them back for merge review the same way.

### Branch discipline
- One task per branch. Name: `task/<short-description>`.
- Fast-forward merge to `main` when tests + Ben approval are in.
- If two branches touch the same file, whoever lands first wins the fast-forward; the other rebases before their own merge.

---

## 10. Open questions

Decisions that aren't made yet. Capture them here instead of letting them drift between sessions.

1. **Embedded LLM — Phase 6 commitment or "someday"?** Until this is answered, skip it entirely.
2. ~~**Engine runs vs imported runs.**~~ **Resolved 2026-04-24:** one `backtest_runs` table for everything, with a `source_type` column (`imported | internal_engine | live_replay`). Same dashboard, same list, same detail page. See Phase 4 schema changes.
3. **Productization.** If Ben ever decides to sell it, what's the first step — marketing site, auth system, hosted-vs-desktop decision? Until that's answered, skip anything that only matters for paying customers.
4. **Sunday live test truth arbiter.** If Sunday's live Fractal bot diverges from the `live_match_2022_2026` backtest, which one is the source of truth for next iteration? Current best answer: live is truth; backtest is the parallel estimate.
5. ~~**Replay route structure.**~~ **Resolved 2026-04-24:** `/backtests/[id]/replay` is the only replay surface. The root `/replay` page is a leftover placeholder — do not build it, and delete the file next time it's touched. A future `/backtests/[id]/validation` stays a separate route (different purpose: live-vs-backtest diff, not trade replay).
6. **Default branch.** Renamed to `main` on 2026-04-23. Anything else drifted from the old branch name? (Check CI, deploy configs, README links once we add any.)

---

## 11. Non-goals

What we will **not** build, and why. Mirrors [`ARCHITECTURE.md §13`](ARCHITECTURE.md) and [`AGENTS.md`](../AGENTS.md) "Do Not Build Yet" but in one place with current context.

- **No broker execution inside BacktestStation.** The Fractal live bot stays standalone in `C:\Fractal-AMD\production\live_bot.py`. This app is for research and monitoring, not order routing.
- **No auth, billing, SSO, multi-tenant** until Ben signals productization.
- **No ML** before the import/analyze/backtest/compare loop is solid (Phase 4 done). When ML does land, use it for regime labeling / setup scoring / degradation detection — *not* for direct price prediction or strategy replacement.
- **No mobile UI, no cloud deploy, no Kubernetes, no Postgres.**
- **No premature abstractions.** Don't build a plugin framework until ≥3 concrete strategies exist. Don't build a generic "connector" layer for non-Fractal files until at least two strategies are imported.
- **No hand-written frontend API clients** once [`scripts/generate-types.sh`](../scripts/generate-types.sh) exists (Phase 3+).
- **No websockets** for Phase 1-3. Polling is fine. Upgrade to websockets only when we can name a user-facing reason.
- **No root `/replay` page.** `/backtests/[id]/replay` is the only replay surface. The leftover `frontend/app/replay/page.tsx` should be deleted the next time someone is in that directory.
- **No favorable-outcome assumptions in the backtester.** If the data can't resolve a stop-vs-target race, the fill is conservative (stop wins). See Phase 4 stop-vs-target fill rules. Every trade records `fill_confidence`; every run summary records `ambiguous_fill_count`. Never let the backtester silently pick the better of two outcomes.
