# CLAUDE.md

Guidance for AI coding agents working in this repo. Humans: follow the same rules.

## Project

BacktestStation — a local-first quant research terminal for futures strategies. Full architecture plan lives at **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — read it before making non-trivial changes.

## Non-negotiable rules

1. **Engine is pure.** `backend/app/engine/` imports nothing from `api/`, `db/`, `storage/`, or `ingest/`. It takes an event iterator + config, returns results. If you feel the need to import `sqlalchemy` or `httpx` inside the engine, stop — you're doing it wrong.
2. **Strategies are dumb.** Strategy classes receive events and emit signals. No DB access, no HTTP, no file I/O, no reading globals.
3. **No lookahead.** Strategies only see data up to the current event's timestamp. The engine enforces this via accessors like `history_up_to(ts)`; never hand a strategy a raw DataFrame.
4. **Schemas have one source.** Pydantic models in `backend/app/schemas/` are the truth. Run `bash scripts/generate-types.sh` after any schema change — it re-exports `shared/openapi.json` and regenerates `frontend/lib/api/generated.ts`. Both files are committed. Prefer generated types in new frontend code (`import type { components } from "@/lib/api/generated"`). The legacy `frontend/lib/api/types.ts` still works for existing consumers; migrate one call site at a time.
5. **Every backtest is reproducible.** Each run stores: backend git SHA, engine version, full params JSON, dataset sha256. Two runs with identical inputs must produce byte-identical `equity.parquet` and `trades.parquet`. A test enforces this.
6. **Results stored as Parquet, never pickle.** Human-inspectable and forward-compatible.
7. **Named constants.** Contract value, tick size, commission, session hours, slippage — all live in a typed config module. Never inline magic numbers in engine or strategy code.
8. **Stop-vs-target fills must be honest.** Never pick the more favorable outcome. This is the #1 correctness rule for the engine.

   - **If trade-level sequence is available** (e.g., MBP-1 trades print in order within the window), use it. Whichever side printed first wins. Record `fill_confidence = exact`.
   - **If the data is ambiguous** (both stop and target are reachable in the same window but trade order cannot be determined — e.g., OHLC bars only), resolve conservatively. Record `fill_confidence = conservative`.
   - **Conservative default: stop wins.** Do not let the backtester pretend to know something it does not know.
   - **Flag borderline cases** with `fill_confidence = ambiguous` so they surface for review; stop still wins in that case.
   - **Every run records `ambiguous_fill_count`** so runs with a lot of ambiguous fills are visible without digging into trades.

   See `docs/ROADMAP.md` §6 for the full fill-rules spec.
9. **No premature abstractions.** There is one strategy today. Don't build a plugin framework, DSL, or dynamic loader until there are at least three concrete strategies.
10. **Split at 300 lines.** If a file crosses 300 lines or a function crosses 60, split it. This is a beginner-readability floor.

## What not to build yet

Auth, billing, Docker, Kubernetes, Postgres, walk-forward, Monte Carlo, websockets, mobile UI, broker execution integration, no-code strategy builders. See architecture doc §13.

Also defer until explicitly scoped:

- **In-app LLM chat.** The Prompt Generator emits a copyable prompt; the user runs it in Claude or GPT externally.
- **Local LLM infrastructure** (Ollama, llama.cpp, etc.). Stay model-agnostic until a concrete use case forces the choice.
- **Destructive cascade delete** for strategies or strategy versions with attached runs/trades/metrics. Archive instead. Current enforcement: `DELETE /api/strategies/{id}` returns 409 when versions exist; `DELETE /api/strategy-versions/{id}` returns 409 when runs exist. Use `PATCH /api/strategies/{id}` with `status=archived` or `PATCH /api/strategy-versions/{id}/archive`.
- **Complex multi-agent systems** inside the app.
- **Auto-applied AI suggestions.** Anything AI produces must land as a human-reviewable note, experiment, or decision — never modify strategies or configs directly.

## Schema migration discipline

Any schema change (new column, new table, vocabulary change) must include migration handling for existing local SQLite data. Pattern: add the model change, then add a guarded migration in `backend/app/db/session.py:_run_data_migrations` (`ALTER TABLE ... ADD COLUMN ...` or `CREATE TABLE IF NOT EXISTS ...`) so existing `data/meta.sqlite` files pick up the change on next app start. `Base.metadata.create_all()` won't add columns to existing tables — the explicit ALTER is required.

## Repo workflow

- Monorepo. Branch per feature. Small PRs.
- Pre-commit runs ruff + black (Python) and prettier (TS). Don't bypass with `--no-verify`.
- `CLAUDE.md` and `docs/ARCHITECTURE.md` are load-bearing docs. Update them when an architectural decision changes; don't update them for routine code edits.

## Test expectations

Before opening a PR that touches the engine:
- `pytest backend/tests/test_engine_*.py` green
- Determinism test still green (run same backtest twice, diff outputs)
- Lookahead harness still green
- MBP-1 stop-vs-target race test still green

If you touched API shapes: regenerate `shared/openapi.json` and the TS client, and commit both.

## Discipline rules (engineering)

For *direction* rules ("should we build X?"), see [`docs/ROADMAP.md`](docs/ROADMAP.md). These are the *engineering* rules — how we build whatever's currently in scope.

1. **Mocked pages declare themselves.** A page rendering hardcoded data must show `[MOCK]` in its header (visible text in the page, not just a comment). If you find a page violating this, fix it before adding features.
2. **No experimental work in core routes.** Warehouse experiments, ML tinkering, and one-off research go in dedicated routes (`/experiments`, `/data-health`, etc.), never in `/`, `/backtests`, `/monitor`, `/replay`, or `/trade-replay`.
3. **Schema changes update the doc trail.** If you bump `SCHEMA_VERSION` in `app/data/schema.py`, update [`docs/SCHEMA_SPEC.md`](docs/SCHEMA_SPEC.md) AND the warehouse-contents section in [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) in the same PR.
4. **Stale doc claims = bug.** If a doc claims a feature does X but the code shows it doesn't, the doc is wrong; fix it. Don't leave it for "later." (Saw this 2026-04-27 with `PROJECT_STATE.md`'s false "12 months TBBO across 28 symbols" claim.)
5. **Type-check + tests + smoke-test before commit.** `npx tsc --noEmit` clean (frontend), `pytest -q` green (backend), and for UI changes: open the page in the desktop app and confirm the change. UI features are NOT verified by type-check or tests alone.
6. **Pipeline silent failures = active problem.** When a daily-fire scheduled task or live ingester logs `errors=0` but produces no output, that's a bug, not "expected idle." Add the silent-failure case to `/monitor` so it surfaces visually.
7. **Raw data is append-only.** `D:\data\raw\` files are never modified after creation. New pulls write new files. The parquet mirror reads but never writes to `raw/`. See [`docs/LOCAL_INFRASTRUCTURE.md`](docs/LOCAL_INFRASTRUCTURE.md) for full data ownership rules.

## When in doubt

Re-read [`docs/ROADMAP.md`](docs/ROADMAP.md) for direction or [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for system design. If those don't answer your question, ask the user before inventing a convention.
