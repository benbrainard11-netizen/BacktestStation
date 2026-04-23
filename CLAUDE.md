# CLAUDE.md

Guidance for AI coding agents working in this repo. Humans: follow the same rules.

## Project

BacktestStation — a local-first quant research terminal for futures strategies. Full architecture plan lives at **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — read it before making non-trivial changes.

## Non-negotiable rules

1. **Engine is pure.** `backend/app/engine/` imports nothing from `api/`, `db/`, `storage/`, or `ingest/`. It takes an event iterator + config, returns results. If you feel the need to import `sqlalchemy` or `httpx` inside the engine, stop — you're doing it wrong.
2. **Strategies are dumb.** Strategy classes receive events and emit signals. No DB access, no HTTP, no file I/O, no reading globals.
3. **No lookahead.** Strategies only see data up to the current event's timestamp. The engine enforces this via accessors like `history_up_to(ts)`; never hand a strategy a raw DataFrame.
4. **Schemas have one source.** Pydantic models in `backend/app/schemas/` are the truth. Frontend imports generated TS types from `frontend/lib/api/` — never hand-write types that duplicate backend shapes. After any schema change, regenerate (`scripts/generate-types.sh`).
5. **Every backtest is reproducible.** Each run stores: backend git SHA, engine version, full params JSON, dataset sha256. Two runs with identical inputs must produce byte-identical `equity.parquet` and `trades.parquet`. A test enforces this.
6. **Results stored as Parquet, never pickle.** Human-inspectable and forward-compatible.
7. **Named constants.** Contract value, tick size, commission, session hours, slippage — all live in a typed config module. Never inline magic numbers in engine or strategy code.
8. **MBP-1 fills must be realistic.** When a stop and target are both reachable within the same tick window, resolve the race using the actual MBP-1 trade sequence. Never pick the more favorable outcome. This is the #1 correctness rule for this engine.
9. **No premature abstractions.** There is one strategy today. Don't build a plugin framework, DSL, or dynamic loader until there are at least three concrete strategies.
10. **Split at 300 lines.** If a file crosses 300 lines or a function crosses 60, split it. This is a beginner-readability floor.

## What not to build yet

Auth, billing, Docker, Kubernetes, Postgres, walk-forward, Monte Carlo, websockets, mobile UI, broker execution integration, no-code strategy builders. See architecture doc §13.

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

## When in doubt

Re-read `docs/ARCHITECTURE.md`. If the plan doesn't answer your question, ask the user before inventing a convention.
