# mstr_gamma_v0 — does MicroStrategy's own options gamma / forced-flow predict MSTR direction?

**Origin.** Spun out of `prop_futures_v0` (2026-06-20). Ben's idea: trade off "what big players are
*forced* to do" — options-dealer gamma hedging, convertible-arb, ETF/issuance flows. The cross-asset
"BTC off MSTR" version is 2-hop and tested null at the price level (MSTR moves *with* BTC, doesn't lead).
This module tests the **1-hop, directly testable** version: **MSTR's own dealer gamma → MSTR's own
direction / vol.** MSTR is the most options-driven, convertible-laden, reflexive equity alive — the
extreme-outlier test of whether single-stock gamma bites where options dominate most.

**Honest prior: MODEST-TO-LOW.** Single-stock gamma→direction was already tested and **killed** in
`stock_options_flow_v0` (9 mid-tier + 8 mega-caps: gamma→vol mostly a price-structure confound;
flow→direction sign-flipped OOS). The live reason MSTR *might* differ: its options/convertible/ATM
machinery is structurally extreme (forced dealer + arb hedging at a scale no normal stock has). That's
the same "X is different because it's extreme" shape as the (also-failed) "mid-tier is different" bet —
so we test it cleanly and let it be null if it's null.

## Pre-registered hypotheses (set BEFORE any result)

1. **Gamma-regime → trend vs revert.** Negative dealer GEX (dealers short gamma → hedge with the move)
   → momentum/trend; positive GEX → mean-reversion/pin. Test: `sign(GEX_t)` (known at close t) →
   next-session return autocorr / |move|, and a directional/trend strategy split by regime.
2. **Wall reaction.** Distance to `call_wall` / `put_wall` / `zero_gamma` → reaction (walls as
   magnets/barriers; zero_gamma as the trend/revert flip level). Intraday on MSTR minute bars.
3. **Gamma magnitude → realized vol.** High |GEX| → vol suppression (pin); low/negative → expansion.
   (Re-test of the `stock_options_flow_v0` gamma→vol null, on the extreme name.)
4. **Pin / forced-flow into expiration.** Does price get pulled toward `pin` (max-|gamma| strike) into
   monthly expiry?

## Discipline (locked)

- **Causality / no look-ahead.** Gamma features use the prior session's close greeks + **prior-day OI**
  (leak-clean) to predict the **next** session. Feature-window ≤ decision time, asserted. (The
  `prop_futures_v0` AUC-0.79 overshoot leak is the cautionary tale — an outcome quantity must never be
  a feature.)
- **HOLDOUT — SEALED.** Design = walls start (~2023) → **2025-09-30**; holdout = **2025-10-01 →
  2026-06-30**. Screen/select on design only; one pre-registered config per hypothesis on the holdout,
  logged win-or-lose.
- **Two-regime same-sign** within the design window; **outlier-robust** (mean survives dropping top
  trades — the `prop_futures_v0` lesson).
- **Honest costs.** MSTR is liquid but high-vol; charge spread + slippage + commission, stressed.
- **Multiple-comparisons aware.** 4 hypotheses × configs; survivors clear an adjusted bar + the holdout.

## Data

- **MSTR gamma walls** (`out/walls_mstr.parquet`, 7-col walls_v2 schema: date, spot, call_wall,
  put_wall, zero_gamma, pin, gex_proxy) — built by the existing `options_signals_v0/build_walls_stock.py`
  from ThetaData EOD greeks×OI (MSTR covered 2012-2028; pulled via `stock_options_flow_v0/pull_chain.py`,
  monthlies, WINDOW=35). Cache-only build: `THETA_CACHE_ONLY=1`.
- **MSTR price** — Polygon survivorship-clean daily (`data_io.load_polygon_daily('MSTR')`) + adjusted
  minute (`load_polygon_minute('MSTR', YYYYMMDD)`) for intraday wall reactions.
- ADJUSTMENT GOTCHA: MSTR did a 10:1 split (2024-08). Gamma-wall strikes are in the unadjusted
  contract space of their date; Polygon adjusted price is split-adjusted. Align spot↔strikes carefully
  (the walls' own `spot`/`underlying_price` is the contract-space anchor; validate vs raw, not adjusted).

## Status — DONE 2026-06-20: NULL across all hypotheses

- [x] **Data** — pulled MSTR options (ThetaData, 41/43 monthlies, 0 err, 30s) → built
  `options_signals_v0/out/walls_mstr.parquet` (806 days 2023-2026, validated vs MSTR close ratio 1.0000,
  100% within 3%). The data path (ThetaData → `build_walls_stock`) worked end-to-end and is reusable.
- [x] **H1 (gamma regime → direction):** gamma-specific signal **flips sign OOS** (neg-GEX→momentum holds
  in design, inverts in holdout); the only positive is plain daily mean-reversion (always-fade), which is
  **outlier-driven** (ex-top-5% negative) and cost-fragile (MSTR daily |r| ~3.1%). NULL.
- [x] **H3 (gamma → vol):** design IC −0.094 → **holdout −0.005 (gone)**; gamma-sign→vol flips. NULL.
- [x] **H2 (wall reaction / pin):** **null and INVERTED** — pin gravitation 0.39/0.42 (<0.5 = anti-pin);
  call-wall pierced → *continues* 64-73% (not resistance); **fading wall touches loses −3.7%/−4.7%** per
  trade both splits. Walls are NOT barriers for MSTR.

**VERDICT — NULL.** Dealer-gamma does not predict MSTR direction, vol, or wall reactions. The coherent
explanation: MSTR is a **short-gamma, momentum-AMPLIFYING** name (heavy retail call demand → dealers
hedge *with* the move), so the long-gamma pin/revert playbook (which works on indices) is backwards here —
walls get blown through, fading loses. The forced flow is real but it **forces momentum, not reversion.**
Confirms the modest prior + the `stock_options_flow_v0` single-stock-gamma null on the extreme name;
"MSTR is different because it's extreme" = false, like "mid-tier is different."

**Durable:** the MSTR gamma-walls dataset (`walls_mstr.parquet`) + the proven ThetaData→walls pipeline
for any single name. **Residual low-prior thread (untested):** the *continuation* (momentum-amplification)
version — buy the call-wall break — would need MSTR minute data; but breakout-continuation has been
universally null + cost-heavy, so the prior is low. Recommend banking.

Python: `C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe`.
