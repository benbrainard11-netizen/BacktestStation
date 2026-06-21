# Research brief — cross-asset orderflow-divergence forecasting (futures)

You are a senior quant-research advisor. I want a deep, cited, substantive report — not
basics. Assume strong engineering and rigorous honest backtesting on my side (walk-forward,
purge/embargo, cost-stress, OOS, no-lookahead). Be skeptical; flag overhyped vs evidence-backed.

## Goal
A model that forecasts short-horizon futures moves from **cross-asset order-flow divergence**
within correlated complexes (one asset's flow absorbs/holds while a correlated one runs), to
drive a systematic trading system.

## Already established empirically — do NOT re-recommend these
- Outright **direction** of liquid index futures is ~unforecastable at 15–60 min (IC≈0, stable
  across seeds, multiple methods).
- **Chart-pattern structure alone** (ICT SMT / FVG / swing pivots) ≈ random (0.518 AUC OOS in my
  tests). Widely taught → no moat.
- What worked: **MBO order-flow** features (took a model 0.518 → 0.699 AUC OOS).
- **Cross-asset spread / cointegration mean-reversion** is real (energy complex, e.g. WTI–Brent,
  OOS Sharpe ~1.5) — but only when pairs are selected by **cointegration structure**, not backtest
  Sharpe (selecting by Sharpe fails OOS; corr(in-sample Sh, OOS Sh) ≈ +0.12).
- Correlation *level* is redundant with volatility; correlation *regime/breakdown* is useful only as
  a **risk gate**.

## Model thesis
- Universe: correlated complexes — index, FX, metals, energy, rates, grains.
- **Signal** = cross-asset order-flow imbalance divergence (OFI, book imbalance, signed-volume/CVD
  divergence, absorption asymmetry).
- **Map** = structure/levels (Volume-Profile LVN/HVN/naked-POC, FVG, SMT) — *where/when* to evaluate.
- **Gate** = correlation / cointegration regime.
- **Target** = does the divergence resolve toward a liquidity objective (path-aware / triple-barrier
  label), multi-horizon, probabilistic.
- Honest bar: must beat a simple baseline OOS after costs + real stops.

## Data
- MBP-1 (top-of-book + trades): 1 yr, 28 futures across asset classes.
- MBO (full depth-by-order): 4 index symbols, ~120 days, expanding.
- 8 yr 1-min bars, 28 symbols.
- Already compute: signed-volume ratio, absorption, cancel/add, book-imbalance, microprice drift.

## What I need (research these)
1. **Divergence / imbalance taxonomy — the priority.** Beyond {OFI, book imbalance, CVD/delta
   divergence, absorption asymmetry, VP LVN/HVN, FVG, SMT, lead-lag}, what **cross-asset
   microstructure divergence signals am I missing** that have empirical/literature support for
   short-horizon prediction? Rank by evidence strength; cite.
2. **OFI / microstructure feature construction** — best-practice definitions (Cont–Kukanov–Stoikov
   OFI, microprice, multi-level book imbalance, queue/cancel dynamics); which are robust vs fragile;
   how to handle the fast decay of book-imbalance predictability.
3. **Cross-asset divergence construction** — how to define & normalize an asymmetry signal between
   correlated assets so it's stationary/tradeable; lead-lag alignment across instruments.
4. **Architecture** — best model class for multivariate cross-asset microstructure forecasting:
   transformer (asset/pair/global tokens + axial attention) vs TCN vs state-space (Mamba) vs
   gradient boosting; multi-resolution (sub-second → minutes).
5. **Pretrained TSFMs** — honest assessment: do Moirai / Chronos / TimesFM / TTM add real value on
   financial microstructure or spread series vs training from scratch? How to use them right
   (zero-shot vs fine-tune; univariate-on-spread vs multivariate)?
6. **Labeling** — best label for "does this divergence resolve toward the objective" (triple-barrier,
   meta-labeling, path-aware); how to encode a liquidity draw/objective as a no-lookahead target.
7. **Regime gating / breakdown detection** — real-time methods to detect cointegration/correlation
   breakdown (so we don't fade a dying relationship — the LTCM failure mode).
8. **Pitfalls** — what most commonly kills cross-asset orderflow / stat-arb models OOS, beyond generic
   overfitting? Microstructure-specific traps.

## Output
Specific, actionable, cited. Flag overhyped vs evidence-backed. Substance over basics.
