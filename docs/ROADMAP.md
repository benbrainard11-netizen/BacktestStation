# BacktestStation — Roadmap

> *Direction* for the research lab. What each repo is: [`../REPO_GUIDE.md`](../REPO_GUIDE.md).
> Current state: [`PROJECT_STATE.md`](PROJECT_STATE.md). Engineering rules: [`../CLAUDE.md`](../CLAUDE.md).
> Live research lines + verdicts: [`../experiments/_INDEX.md`](../experiments/_INDEX.md).

---

## Vision

A personal local quant research lab: a broad market/data warehouse + reusable test tooling + local
ML/training, used to **find edges that survive honest OOS testing** — then graduate each winner into
its own live repo, run from the InsyncAPP platform. One trader (Ben); one collaborator (Husky, mostly
on the platform side).

ML / model training is **in scope** — it's the core of the lab now (Mira's MBO model, cross-asset RV,
the `market_state` model). The earlier roadmap's "no ML until 6 months of data" and "no 2nd strategy"
gates are **retired**: the data exists, the edges are real, and the per-strategy-live-repo model means
extra strategies aren't a maintenance tax on one codebase.

---

## The graduation flow

```
research a hypothesis in experiments/ or market_state/
  -> forward-validate it OOS, no-lookahead  (the one rule)
  -> if it survives: freeze the model, vendor it into a new live-engine-<name> repo
  -> plug that bot into InsyncAPP to run / visualize / manage prop accounts
```

---

## Current focus

1. **`market_state/`** — the broad market-state model. Build the **validation harness first**, then wire
   the two already-validated inputs (MBO order flow + vol regime); grow only as new inputs forward-validate.
2. **Mira → live.** `live_engine/` (the Mira MBO reclaim bot) is code-complete and offline-validated,
   currently **sim mode**. Path to capital: Leg-B parity + go-live ladder (`live_engine/DEPLOY.md`).
3. **Cross-asset RV → deployable.** `energy_rv_v0` is the most deployable edge (diversified book OOS
   Sharpe +1.44). Productionize into its own live repo when ready.
4. **Sizing / money layer.** `sizing_v1` turns model probabilities → contracts per prop account and sims
   fleet pass rates — the bridge from "edge" to "funded accounts."

---

## Validated vs dead (2026-06-02 — see `_INDEX.md` for live truth)

**Validated (survived honest testing):** cross-asset RV cointegration (energy/grains/curve), Mira MBO
order flow (structure/SMT alone is noise; +MBO book features is the real signal), vol-regime forecastability.

**Dead — do not re-chase:** chart-pattern ML (the whole ML_SNAPSHOT era), gamma/GEX regime gate, TGIF,
naive orderflow divergence, index-context / "predict the next candle."

---

## Discipline rules (direction)

1. **No label/edge exists until it forward-validates** OOS, no-lookahead. The harness is the product.
2. **Build on structural/microstructure edges** (order flow, RV, vol regime). Chart-pattern and
   index-context prediction keep dying — stop seeding models with them.
3. **One strategy = one live repo.** Don't bolt a 2nd live strategy into an existing live repo.
4. **The warehouse is append-only.** RAW on `D:\data` is never modified; layout is canonical per `SCHEMA_SPEC.md`.
5. **Docs stay minimalist.** New findings → memory or the experiment's own README, not new top-level docs.
   (~216 stale docs were deleted 2026-06-08; don't rebuild the sprawl.)
6. **Engineering rules** ("how to build cleanly") live in [`../CLAUDE.md`](../CLAUDE.md).

Last updated: 2026-06-08.
