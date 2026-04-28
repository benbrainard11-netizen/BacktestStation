# BacktestStation — Roadmap

> Source of truth for *direction*. For "what's running right now," see [`PROJECT_STATE.md`](PROJECT_STATE.md). For *engineering* discipline ("how do we build it?"), see [`../CLAUDE.md`](../CLAUDE.md). For machine roles + data ownership, see [`LOCAL_INFRASTRUCTURE.md`](LOCAL_INFRASTRUCTURE.md).

---

## Vision (long-term)

BacktestStation is a personal local quant/trading lab — eventually a mini-institution research environment for one trader (Ben), with one contributor (Husky). The full vision:

- Local-first trading research terminal
- Imported + engine-generated backtest results
- Replay and review system across multiple timeframes + tick depth
- Live monitoring of bots and pipelines
- Historical futures data warehouse (L1 / L2 / L3 / tick)
- Personal model training + AI research agents
- GPU-powered local ML/LLM workflows
- Full decision-support system feeding live trading

The vision is **the destination**, not permission to build the whole stack at once. The whole point of having tiers below is preventing scope creep into "everything at once."

---

## Build tiers

### CURRENT FOCUS (next ~30 days)

Three lanes running in parallel — pick whichever has momentum on a given day.

#### A. Fractal AMD live-readiness

The headline goal. The whole system exists to put real money on a validated strategy.

- Paper-trade the live bot for at least 2 weeks; track via Forward Drift v1 + the live-trades pipeline (already feeding `meta.sqlite` daily 17:00 ET).
- Close the one remaining port↔live signal-detection gap (1 of 6 live trades doesn't fire in the port).
- Define a "ready for capital" gate. Concrete proposal: ≥40% WR over ≥30 paper trades, max DD < 10R, no entries fired outside 09:30-14:00 ET (the validated window).
- Until the gate is met: paper-only, no real capital.

#### B. Warehouse stabilization

The data layer the rest of the system depends on. Already mostly built; needs to be verified and rounded out.

- Manually trigger the first historical MBP-1 pull (NQ.c.0); verify `parquet_mirror` handles MBP-1 correctly end-to-end (it works for TBBO; MBP-1 is untested at scale).
- Build the weekly gap-filler discussed earlier: NQ/ES/YM/RTY (matching the historical puller's 4-index-future scope), MBP-1 1mo + TBBO 12mo, Sundays 03:00 local, $0-cost guardrail (skip+warn if a missing month estimates >$0).
- Ship Forward Drift v1 frontend panels in `/monitor` (backend exists since 2026-04-25; this is just surfacing it).
- Live-trades pipeline: confirm daily fire works for 2 consecutive weeks without manual intervention. The `/monitor` panel turns red if it doesn't.

#### C. Husky's prop-firm UI

Parallel lane, Husky-owned. Don't stomp his WIP.

- Un-mock `/prop-simulator` dashboard, `/prop-simulator/firms`, `/prop-simulator/compare`. Backend already exists (`app/services/prop_firm.py` + endpoints). This is wiring + UX work.
- The simulator runs page (`/prop-simulator/runs`) is already on real data; only the pages above are mocked.

### DEFERRED — do not build until current focus is done

These are explicit no's. If you find yourself building one, stop and re-read the discipline rules below.

- **ML / model training layer.** Gated by ≥6 months of own-collected TBBO/MBP-1 data AND a concrete falsifiable trading hypothesis. ML is research, not infrastructure — building the registry/tracker before the models is putting carts before horses.
- **A 2nd custom strategy.** Don't add until Fractal AMD is real-money. Custom strategies are a maintenance commitment; one is enough until one is profitable.
- **New warehouse schemas** (L3 book depth, imbalance, options chains). The existing four (TBBO, MBP-1, OHLCV-1m, OHLCV-1s) need to be queryable + trusted in real workflows first. Don't ingest data the app can't actually use.
- **Institutional automation, multi-account orchestration, agent crews.** When the lab has more than two users, this conversation reopens.
- **Cloud / SaaS / sharing features.** This is a personal lab.
- **Docker / containerization.** The Tauri + uvicorn sidecar setup works for two machines. Revisit only if cross-machine deploys become painful.
- **Folder restructure of `D:\data\`.** The current layout is canonical per [`SCHEMA_SPEC.md`](SCHEMA_SPEC.md). Renaming for aesthetics breaks every downstream tool.

### RECENTLY SHIPPED — for context (last ~3 weeks)

What's in `main` already, so you don't accidentally re-build it:

- **Backtest engine v1** — pure, deterministic, lookahead-tested.
- **Fractal AMD strategy port** — matches the live bot on 5 of 6 fills (the unmatched one is a signal-detection difference, tracked).
- **Live TBBO ingester** on ben-247 → `D:\data\raw\live\`. Online since 2026-04-24.
- **Strategy-aware Run-a-Backtest UI** — Fractal AMD selectable, typed param fields per strategy.
- **Risk Profile manager** — CRUD + retroactive evaluator + dossier panel.
- **Per-day chart replay** at `/replay` — 1m candles, entry markers, 4-speed playback.
- **Trade replay** at `/trade-replay` — TBBO + bars at 1s/1m/5m/15m/30m, ET time axis, anchor lines that reveal as cursor passes entry.
- **Live-trades pipeline** — daily 17:00 ET, ben-247 reconciles + Taildrops `trades.jsonl` → benpc imports.
- **Live-trades pipeline health panel** on `/monitor` — surfaces silent failures.
- **Forward Drift Monitor v1 backend** — WR + entry-time chi-square against a baseline run.
- **`merge-review` subagent** at `.claude/agents/merge-review.md` — run before merging a branch.
- **444 backend tests**, all green.

---

## Discipline rules (direction)

These are the rules for *should we build X?* — engineering rules ("how do we build it?") live in [`../CLAUDE.md`](../CLAUDE.md).

1. **Vision is destination, not permission.** Default answer to "should we add X?" is **no** unless X serves Current Focus tier (A, B, or C). When the vision tempts a future-tier build, point at this doc and ask Ben before writing code.
2. **No 2nd custom strategy until Fractal AMD trades real money.** One at a time. A 2nd strategy is a 2x maintenance load on tests, drift comparisons, and dossier UI.
3. **No ML / model-training work** until both: ≥6 months of own-collected TBBO/MBP-1 data, AND a concrete falsifiable hypothesis. ML is research, not infrastructure.
4. **Mocked pages must declare themselves.** A page rendering hardcoded data must show `[MOCK]` in its visible header (not just a code comment) so future sessions don't read it as functional. Applies retroactively to `/prop-simulator/*` pages until Husky un-mocks them.
5. **New warehouse schemas don't ship until existing schemas are queryable in a UI flow** — i.e., you can run a backtest from them or render a chart from them. Don't ingest data the app can't actually use.
6. **One feature per PR per lane.** Don't bundle warehouse work into a UI PR or strategy work into a data PR. The merge-review agent flags this.
7. **Daily command center stability is sacred.** Experimental ML, warehouse experiments, and one-off research go in dedicated routes (`/experiments`, `/data-health`), never in `/`, `/backtests`, `/monitor`, `/replay`, or `/trade-replay`.
8. **The roadmap is a living doc.** When something ships, move it from Current Focus → Recently Shipped in the same PR. When something becomes Current Focus, move it from Deferred → Current Focus in a deliberate, Ben-approved PR.

---

## How to use this doc

- **"What should we build next?"** → Current Focus tier. Pick A, B, or C based on momentum.
- **"Can I add X?"** → if X isn't in Current Focus, default no; ask Ben.
- **"Is X done?"** → check Recently Shipped here, or [`PROJECT_STATE.md`](PROJECT_STATE.md) (the live-state mirror).
- **"What's the long game?"** → Vision section. Don't translate vision into PRs without Ben's explicit say-so.
- **"How do I build it cleanly?"** → [`../CLAUDE.md`](../CLAUDE.md) (engineering rules).
- **"Which machine does this belong on?"** → [`LOCAL_INFRASTRUCTURE.md`](LOCAL_INFRASTRUCTURE.md).
- **"Is this branch safe to merge?"** → invoke the [`merge-review`](../.claude/agents/merge-review.md) subagent.

Last updated: 2026-04-27.
