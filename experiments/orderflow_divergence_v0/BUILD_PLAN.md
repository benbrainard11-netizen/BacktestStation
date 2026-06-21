# v0 Build Plan — cross-asset orderflow-divergence model

Derived from two corroborating research passes (`research_synthesis.md`). Guiding principle:
**prove cheap before building.** Every phase has a go/no-go gate; phase N+1 is not built until phase N
beats its baseline OOS after costs. Stop early if a gate fails — that's the win, not the loss.

## Scope (v0)
- **First complex: INDEX (ES/NQ/YM/RTY)** — most correlated, MBO depth available, large-tick-ish, the
  user's intuition home. NOTE: this is INTRADAY order-flow divergence at event/second scale — a *different*
  thing from the dead DAILY index direction/RV work; the research specifically supports it.
- **Second complex: ENERGY (CL/BZ/HO/RB/NG)** — where RV already worked; MBP-1 broad. Add after index proves out.
- **Resolution: event-time / ~1s, NOT minute bars.** The research is emphatic — the signal decays in
  seconds-to-minutes; the current 15-min buckets are too coarse and explain why prior 15–60min work was dead.
- **Data tiers:** MBP-1 (top-of-book OFI + trades, 1yr, 28 syms) = the statistical workhorse. MBO-deep
  (multi-level OFI, 4 index syms, ~120d) = a *tested enhancement only* — thin, so heavy overfitting caution.

## Phase 0 — Fine-resolution feature layer (prerequisite)
Per asset, at event-time/1s (not 15-min):
- Event-based OFI (Cont-Kukanov-Stoikov: limit+market+cancel, not just signed volume), **depth-normalized**.
- Microprice (Stoikov) + microprice−mid gap.
- Queue imbalance (top-of-book) as a hazard variable.
- Multi-level integrated OFI (MBO syms only; Ridge/PCA-compressed, ~4-5 levels).
- Multiple short EWMA kernels (not a single trailing sum); intraday-seasonality / time-of-day normalization.
Reuse `orderflow_features.py` logic at finer resolution. New: event-time aggregation, multi-level OFI, microprice.

## Phase 1 — THE DECISIVE TRANSFER TEST (cheapest — do FIRST)
**Question: does OWN-asset OFI predict short-horizon returns on YOUR FUTURES at all?** (The #1 unknown — all
evidence is equities; own-asset OFI must work before cross-asset can.)
- Target: next-move sign / few-second forward return, on the large-tick index symbols (ES first).
- Model: linear + GBDT on own-asset OFI / microprice / queue features.
- Gate: OOS predictive (beat random AND a trade-volume baseline) AND survives a tick-path stop + costs.
- **GO** if own-asset OFI works on ES/index. **NO-GO** → thesis is equities-only; stop (huge saved effort).

## Phase 2 — Common-factor residualization + cross-asset divergence (only if Phase 1 passes)
- Complex common-flow factor `f`; idiosyncratic pressure `u_i = z_i − λ_i·f` (THE key construct — without it
  you measure the same complex-wide shove twice).
- Hayashi-Yoshida lead-lag `τ_ij` (handles async; **sign-flip across windows = do-not-trade flag**).
- Lag-aligned idiosyncratic divergence `D_ij = u_i − β_ij·u_j(t−τ_ij)`.
- Replenishment/resiliency asymmetry feature (the user's "one holds while the other runs").
- Gate: does `D_ij` add INCREMENTAL OOS power OVER own-asset OFI? (Research: small-but-real — bar is "adds
  anything beyond own + common factor").

## Phase 3 — Label + honest eval (TICK-path)
- Extend the forward-path engine **bar → tick/event level** (research: bar-high/low too crude at this horizon).
- First-touch triple-barrier; upper barrier = **ex-ante liquidity objective** (prev-session VP level, current
  POC from flow-so-far, microprice zone), frozen at decision time (no-lookahead).
- Honest economics: real stops, costs, OOS. **The fill model is part of the alpha model** — model legging/queue.

## Phase 4 — The model
- **GBDT hard baseline** (medium heterogeneous tabular data favors trees).
- Compact LOB conv encoder (TCN / DeepLOB) on MBO syms ONLY if it beats GBDT OOS (120d → overfitting caution).
- TSFM (TTM/Moirai) as **auxiliary baseline only**, on regular derived residual series; zero-shot = curiosity.

## Phase 5 — Gate + sizing (productionize)
- Qualification: Gregory-Hansen (cointegration WITH breaks). Monitoring: Wagner-Wied + BOCPD/CUSUM/MOSUM on
  {residual, hedge ratio, lead-lag, idio-flow variance} → cut/downweight on destabilize.
- `sizing_v1` integration; combine with the RV book + MBO at the account level.

## Reuse map
- `orderflow_features.py` → finer-resolution feature layer (Phase 0).
- `honest_economics.py` + `build_forward_path_sidecar.py` → extend bar→tick (Phase 3).
- cointegration machinery in `xsectional_rv_v0/` → the Phase 5 gate.
- `sizing_v1/` → the money layer (Phase 5).

## First concrete step
**Phase 1 transfer test on ES.** Own-asset OFI → short-horizon move, OOS, tick-path stop + costs. Cheap,
decisive, answers the #1 unknown before any big build. If it works, we proceed; if not, we've saved weeks.
