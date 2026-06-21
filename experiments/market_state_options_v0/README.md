# market_state_options_v0 — options-driven MARKET-STATE context (decision-support, not a signal)

**What Ben wants (2026-06-21):** a *market-state* readout from **options data** — options regime (dealer
gamma posture), **LTF / 0DTE gamma** ("1h gamma hedging" pin/accel dynamics), vol regime — to give his
**discretionary** futures trading context. NOT a microstructure entry model; a "what environment am I in"
layer.

**The honest guardrail (locked).** Gamma/options as a **directional predictor is NULL** in this lab,
tested many times: single-stock gamma ([[stock_options_flow_v0]]), MSTR ([[mstr_gamma_v0]] — walls
inverted), the GEX regime gate (`options_signals_v0`, null 5 cuts), SPX realized-vs-implied
([[index_options_audit_v0]]). So this module is built as **CONTEXT**: it reports the *regime* and how the
market **historically behaves** in it (range / pin / trend), explicitly **not** a buy/sell call. That's
the only honest way to use options data here — and it's genuinely useful for sizing/expectations.

## Components (data we already have)
- **Intraday net dealer GEX** (the new piece) — from the §9 1-min option panels (NDXP/SPXW/RUTW/DJX,
  2025-05+, gamma×oi_prior×underlying). Net = gamma·OI·(call+/put−)·spot². Sign = short-gamma
  (trend-prone) vs long-gamma (pin-prone); magnitude + intraday evolution; **0DTE share** (dominates —
  ~83% at the close in the first probe). Causal: prior-day OI + that-minute chain.
- **Zero-gamma flip level** + spot-vs-flip; **call/put walls** (max/min net-gamma strike).
- **0DTE expected move + pin** (short-DTE panel).
- **Vol regime** — VIX level + term structure (VIX1D/VIX/VIX9D contango↔backwardation) + VVIX
  (`options_signals_v0/out/vol_indices`).

## Method / discipline
- Regime computed at a **causal decision minute** (10:00 ET): prior-day OI + the 10:00 chain + 10:00 spot.
- Characterize **rest-of-day** behaviour by regime: realized range, trend-vs-chop, close-vs-zero-gamma —
  DESCRIPTIVE (regime → typical behaviour), with the explicit caveat it is not a directional edge.
- Validate the GEX computation reproduces the daily walls (§5) as a sanity anchor.

## Status
- [x] **`build_regime.py`** (2026-06-21, NDX 264 days) — **VALIDATED, ADDITIVE read:** the gamma regime
  is a real **range/vol** descriptor. SHORT-gamma days (23%): median rest-of-day range **1.22%**, 73% make
  a >1% move; LONG-gamma: 0.83%, 35%. `corr(GEX, range) = −0.29`. **Trend ratio identical (0.45)** → it
  does NOT call direction (consistent with the gamma-direction nulls). **Additive over realized vol:**
  partial `corr(GEX, range | morning_range) = −0.153` (GEX is partly a vol proxy, corr −0.46 w/ morning
  range, but adds incremental range info). Modest but genuine — survived the "is it just VIX" check that
  kills most options signals. **The honest core read: gamma regime → expected RANGE (size/expectation),
  not direction.**
- [x] **Multi-timeframe (`build_mtf.py`) + GENERALIZATION (2026-06-21):** gamma regime → projected range
  at 1h/4h/EOD, computed at intraday decision times, **holds on NDX, SPX, AND RUT.** All three: short-gamma
  ~1.3-1.8× the range, additive over vol every horizon, STRONGER intraday (0DTE concentrates). SPX strongest
  (corr −0.49/partial −0.31, deepest 0DTE market), NDX mid, RUT weakest — strength tracks options depth =
  real effect. Tables in out/mtf_{NDXP,SPXW,RUTW}.csv. **The validated core market-state read.**
- [x] **PACKAGED readout (`market_state.py`, 2026-06-21):** one call `market_state(index, date, time)` →
  gamma regime + PROJECTED 1h/4h/EOD range (regression range~trailing+GEX per decision bucket) + levels
  (zero-gamma/call-put walls/0DTE pin) + 0DTE expected-move + **vol regime** (VIX level + VIX1D/VIX/VIX9D
  term structure + VVIX, prior-day causal) + honest narrative. Works NDX/SPX/RUT, all causal, CONTEXT-only.
- [ ] (optional next) intraday GEX trajectory tile; wire into the InsyncApp assist + fix the reversal tile
  to show OOS 64% (not in-sample 67.6%).

Python: `backend/.venv/Scripts/python.exe`. Panels: `D:\data\processed\option_panels\panel\root=<R>`.
