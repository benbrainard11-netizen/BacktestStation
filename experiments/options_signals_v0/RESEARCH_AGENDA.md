# Options-derived signals — research agenda (v0)

**NOT trading options.** Using options-market *data* as signals / regime gates for the ES/NQ index
futures strategies. Same underlying (SPX/NDX options ↔ ES/NQ futures), so this is directly about our
markets. Captured 2026-06-02 from a brainstorm; this is the map, not yet built — gated on options data.

## Thesis
The highest-value form isn't a new options bot — it's a **regime gate**: "is today a pin / mean-revert
day, or a trend day?" That conditions the index strategies we already have. It plugs straight into the
open question from the regime work: realized vol IS forecastable, trendiness is NOT (corr ~ -0.03) —
**dealer gamma may be the thing that forecasts the pin-vs-trend regime.** If so, it makes Mira better
(only take reclaims when the regime favors the move) and enables a regime-aware index strategy.

## The signal landscape (real vs hype)
| signal | what it is | what it predicts | honest verdict |
|---|---|---|---|
| **Gamma / GEX regime** | dealer net gamma from the option chain; +gamma = dealers fade moves, −gamma = dealers chase | calm/pin/mean-revert (+) vs volatile/trend (−) | **the real one** for vol/regime; direction-from-GEX is arbed + hyped (SpotGamma mainstream). Depends on a dealer long/short *assumption*, not observed |
| **0DTE flows** | same-day-expiry options (>half of SPX volume now) → huge fast intraday hedging | intraday pin / unpin, EOD acceleration | frontier, **less arbed (new)** but data-hungry (intraday) + up against Citadel/SIG |
| **Vanna / charm** | 2nd-order greeks: delta vs vol (vanna), delta vs time (charm) → predictable dealer flow | OPEX drift, the "vanna rally" (vol down → dealers buy), into-close flows | real, well-documented around OPEX; needs greeks + intraday |
| **Volatility risk premium (VRP)** | implied vol systematically > realized | the most *robust* options edge | real but it's a **vol-selling** game (tail risk), not a regime gate; and not on futures-only prop accounts |
| **Skew / term structure** | put-call skew, IV term curve | tail pricing, stress | secondary / confirmatory |
| **DIX** (dark-pool flow) | SqueezeMetrics dark index | passive buying pressure | separate flow signal, secondary |

## Data requirement (THE gate)
- **Regime test (the MVP) needs only DAILY / end-of-day SPX (+NDX) option chains**: OI + greeks per
  strike. Far cheaper than intraday tick.
- Sources to price: **Databento OPRA** (consolidated options; pricey, intraday-grade), **CBOE DataShop /
  ORATS** (historical EOD chains, usually cheaper), free GEX feeds (lower quality / assumption-baked).
- **0DTE / vanna / charm need INTRADAY options data** → pricier → defer until the EOD regime test pays off.

## Test sequence (cheapest, highest-value first)
1. **Gamma regime gate (EOD data):** compute daily total GEX + zero-gamma flip; test whether it predicts
   next-day / intraday ES realized vol AND mean-reversion-vs-trend. Honest bar: beat the vol-persistence
   baseline we already have, no-lookahead, OOS.
2. **If it gates:** condition Mira on it (regime filter), and/or build a regime-aware index strategy.
3. **Later (pricier intraday data):** 0DTE pin/unpin, vanna/charm around OPEX.

## Honest gates (don't skip)
- **Costs money** like the MBO pull — scope the exact number, decide deliberately. Cheap-first: EOD before intraday.
- GEX rests on a **dealer-positioning assumption** (not observed) — validate the proxy before trusting it.
- The direction edge is **arbed/hyped**; the durable part is the **vol/regime** effect. Test for *that*.
- **Sequencing reality:** the current bottleneck on actual income is still **Mira execution** (other PC).
  This is a queued direction — scope it, free-proxy what we can, pull data when execution's sorted + budget allows.

## RESULT (2026-06-02) — regime gate TESTED and DEAD ($75 well-spent)
Pulled the SPX+NDX 2025 EOD bundle (~$75, 421 MB), computed daily GEX (`gex_compute.py`, VIX-flat IV v0;
sign 61% pos / 39% neg = sane SPX profile), tested the regime gate (`gex_regime.py`, n=245):
- **GEX conditions realized vol** (corr −0.16, clean) — but that's **redundant with VIX** (free).
- **GEX does NOT condition trendiness / pin-vs-trend** (corr **−0.004**, flat) — and the **free VIX proxy
  (+0.007) independently agrees.** The gate we bought the data for does not exist for daily ES.
=> The daily gamma regime gate is **dead**. Killed for $75 BEFORE any live pipeline — cheap-first worked.
Caveats: n=245 (1yr, small), v0 VIX-flat IV, intraday-0DTE (the pricier frontier) untested. Data +
compute pipeline are built and reusable if ever chasing the intraday version. Don't spend more here.

## Status (original plan, for reference)
Mapped + priced + free-proxy-tested.
- **Priced (2026-06-02):** SPX+NDX EOD bundle (bars + OI + strikes), 1yr ≈ **$75** total via Databento OPRA.
  Intraday (0DTE/vanna) is pricier + a different schema (deferred).
- **Free VIX-proxy test (`vix_regime_proxy.py`, 2026-06-02):** VIX term structure (VIX/VIX3M/VIX9D, CBOE)
  as a crude gamma-regime stand-in. Result over 2,083 days: it conditions **realized vol** strongly
  (corr +0.69..+0.77 — expected, VIX *is* implied vol) but does **NOT** condition **intraday trendiness**
  (the pin-vs-trend gate we'd actually buy GEX for): corr **+0.007**, stress-regime trendiness 0.0548 vs
  calm 0.0544 — flat. Consistent with the earlier phase-model null (trendiness ≈ unforecastable).
- **Verdict:** the cheap proxy gives **no encouragement** for the trend-gate thesis. Real dealer GEX is a
  sharper/different signal so this isn't a definitive kill, but it **downgrades the ~$75 buy from
  "best-value, go" to "speculative."** Deprioritize vs execution. Revisit only if a specific GEX hypothesis
  (e.g. pinning near large 0DTE strikes — needs the strike-level data) is worth a speculative $75.
