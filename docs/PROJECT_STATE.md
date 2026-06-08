# Project State — 2026-06-08

> A scannable snapshot of "what's where, what's working" in the research lab. A checkpoint, not live
> truth — when in doubt, the code + [`../experiments/_INDEX.md`](../experiments/_INDEX.md) win.
> Repo map: [`../REPO_GUIDE.md`](../REPO_GUIDE.md). Direction: [`ROADMAP.md`](ROADMAP.md).

---

## The shape

Three repos (see REPO_GUIDE): **BacktestStation** = research lab + tools (this); **live_engine** = the
Mira live bot (own repo, nested here); **InsyncAPP** = the trading platform (with Husky).

---

## Tooling — the reusable lab (stable)

- **Backtest engine** (`backend/app/backtest/`) — pure, deterministic, lookahead-enforced, honest
  MBP-1 stop-vs-target fills. The trust foundation. Test suite green (run `pytest backend/` for the count).
- **Data warehouse** (`D:\data` + `backend/app/ingest`,`data`) — Databento DBN → Hive parquet; live
  ingester + historical puller + gap-filler + R2 mirror. `data/meta.sqlite` (~40 GB, 29 tables) holds
  run/research metadata.
- **Tick/bar replay** — the engine replays MBP-1 / bars to drive sims (the UI replay viewer went with the frontend).
- **Prop-firm Monte Carlo** (`backend/app/services` + `experiments/sizing_v1`) — fleet sims across firms/accounts.
- **Feature detectors** (`backend/app/research/features/*`) — order flow, volume profile, HTF/SMT, etc.

## Research — the hunts (see `_INDEX.md` for verdicts)

**Validated edges:**
- **Cross-asset RV** (`xsectional_rv_v0` → `energy_rv_v0`) — energy/grains/curve cointegration holds
  OOS; diversified book OOS Sharpe **+1.44**. Most deployable edge.
- **Mira MBO order flow** — structure/SMT alone ≈ noise (0.518 AUC); +MBO book features is real (0.699);
  held real-MBO OOS ~+0.44R. Now a live bot (below).
- **Vol regime** — forecastable (`phase_model_v0`).

**Greenfield:** `market_state/` — the broad "what's the market doing right now" model. Validation-first
(harness before model); builds on MBO order flow + vol regime + RV structure.

**Dead (don't re-chase):** chart-pattern ML (the deleted ML_SNAPSHOT era), gamma/GEX, TGIF, naive orderflow divergence.

## Live (layer 2)

- **`live_engine/`** — Mira MBO reclaim bot. Code-complete, offline-validated (parity tests green),
  connects + streams on Rithmic. **Sim mode only** pending Leg-B parity + the go-live ladder.
  See `live_engine/DEPLOY.md` + `live_engine/docs/BUILD_PLAN.md`.

## Platform (layer 3)

- **InsyncAPP** — Vue3/Tauri. `services/research` live; `services/tradebot` (Rithmic/TakeProfitTrader)
  active build; `services/backtest` ported. Where bots get run + prop accounts managed.

---

## Housekeeping done 2026-06-08

- **~219 GB reclaimed** — old `meta.sqlite` `.bak` snapshots, `experiments/_archive`, the `bs-mira-v15`
  worktree, and gitignored `data/strategy_lab_*` bundles. (Build caches left in place by choice.)
- **Docs culled to minimalist** — ~216 stale docs deleted (recoverable in git); `REPO_GUIDE.md` added;
  these 3 core docs rewritten to the 3-layer model.
- **Backend-only reshape** — removed the web SPA + CRUD API (`frontend/`, `app/api`, most `app/schemas`,
  frontend-only services); `main.py` now serves a read-only status page. The lab is backend + tools, run via CLI/Python.

---

## Pointers

- Live research list + verdicts: [`../experiments/_INDEX.md`](../experiments/_INDEX.md)
- Portfolio state: `../experiments/STRATEGY_REPORT_2026-06-02.md`, `../experiments/OVERNIGHT_2026-06-02.md`
- Schema / data: [`SCHEMA_SPEC.md`](SCHEMA_SPEC.md), [`DATA_FORMAT.md`](DATA_FORMAT.md), [`LOCAL_INFRASTRUCTURE.md`](LOCAL_INFRASTRUCTURE.md)
- Engine internals: [`BACKTEST_ENGINE.md`](BACKTEST_ENGINE.md)
