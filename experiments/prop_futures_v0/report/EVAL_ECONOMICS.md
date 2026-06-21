# prop_futures_v0 — Layer-1 eval-economics test of the reversion generator

**Date:** 2026-06-20. **Question (prop_model_v0 thesis):** the market-edge hunt is a null, but the
reversion generator is a stable high-win (~68%) ~0-to-slightly-negative-EV shape. Does that shape clear
the prop EVAL economics net-positive via the asymmetric-bet structure (fee F for a shot at funded value
V), the way `eval_ev` showed +EV even at *zero* market edge?

**Method:** fed the generator's EMPIRICAL `fade_R` distribution (n=1189 events, 6 liquid symbols; mean
−0.020R, median +0.242, win 68.5%, std 0.56; stable design −0.026 / holdout −0.003) through `eval_ev`'s
firm pass/blow/payout machinery (`eval_reversion.py`, monkeypatching the per-trade draw). Two draw modes:
**IID** (independent trades/day) and **day-block CORRELATED** (each sim-day = a real historical date's
actual cross-instrument trade set, preserving same-day correlation; 279 dates, median 5 / max 7 co-
occurring trades/day).

## Result

| firm | IID EV | IID pass | CORR EV | CORR pass | free-coin (edge_r=0) |
|------|------:|------:|------:|------:|------:|
| topstep | +485 | 0.215 | +732 | 0.253 | +989 |
| lucid | +241 | 0.240 | **+1209** | 0.365 | +1031 |
| mffu | −8 | 0.256 | +401 | 0.304 | +929 |
| tradeify | +35 | 0.233 | +810 | 0.323 | +535 |
| apex | +4 | 0.176 | **−90** | 0.001 | +354 |

## Verdict: positive in the model, but it is VARIANCE-FARMING — not an edge

The reversion generator clears eval-EV net-positive in the model (4–5 firms), and correlation HELPS
(lumpy chop-vs-trend days are convex for the eval: capped downside = fee, upside = funded value). This
validates the prop_model_v0 thesis *mechanically*. **But it is variance-farming a slightly-negative
generator, not a tradeable edge**, and must be read that way:

1. **All the EV comes from variance, none from edge.** At n=1 / low variance the EV is ~0 (apex IID +4,
   day-block −90). The positive numbers require piling on variance (≈5 instruments × max risk $900).
2. **The generator is −0.02R.** Funded accounts bleed and blow (pass rates only 25–37%); the model EV is
   "extract the fee↔funded asymmetry on lucky lumpy runs before the account dies," not equity growth.
3. **Fragile / model-dependent.** The IID→correlated swing is huge (lucid +241→+1209). A result that
   sensitive to the variance/correlation assumption is not robust.
4. **Exploits the loosest-ruled firms** (lucid: soft DLL, EOD-only DD, no eval consistency cap) and
   **collapses on the tightest** (apex). Firms' **consistency rules exist to tax exactly this** and are
   only partially modeled here — real-world friction is higher, and rules tighten against variance-gamers.
5. 13-month exploratory distribution; correlation modeled by resampling 279 real dates.

**Bottom line.** prop_futures_v0 has no market edge (thoroughly established). The reversion generator's
only positive expression is eval variance-farming on loose-ruled firms — real in the model, but fragile,
rule-dependent, against-spirit, and built on a negative-EV generator. That is the realistic CEILING of
this effort, not a deploy signal. A responsible next step before any capital would be a consistency-rule
+ correlation STRESS test (tighten the modeled rules, vary the correlation), and forward data — not
deployment. Durable assets: the engine/families/event-dataset/leak-checked discipline and this honest
eval-economics characterization.
