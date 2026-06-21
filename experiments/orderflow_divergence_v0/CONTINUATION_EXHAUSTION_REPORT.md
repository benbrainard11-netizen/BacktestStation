# Continuation + Exhaustion tests — verdict

Tests of the user's two live hypotheses after the PO3/reversal thesis was shown not to beat mean-reversion.
The user's framing: *"a LTF reversal can be a HTF continuation, so they work together"* — both are the same
move (a level sweep) seen from two sides. So one experiment probes both: **at a level sweep, does order flow
predict CONTINUATION (real breakout) vs REVERSAL (fakeout)?**

## 1. The 1H swept-only hint (reversal_harness.py --swept-only)
Conditioning the 1H harness on a real prior-level sweep produced the first promising flow signal of the whole
investigation:
- **Base rates validate PO3:** only **12–24%** of swept 1H lows continue down — **76–88% are fakeouts that
  reverse.** "The high/low is usually a manipulation" is literally true in the data.
- Flow features lit up: ZN `sgn_into_low` univ AUC **0.657**, ZB `absorp_low` **0.680**, ZB ablation
  ALL **0.650** vs mean-reversion 0.575.
- **BUT:** only ~150–180 test events → GBDT overfit (ZN `absorption-ONLY` GBDT = 0.500 despite univ 0.657),
  and the full-sample ZN run (1,391 events) showed flow adding nothing. **Suggestive, not proven — needs more
  events.** That motivated the 1-min test.

## 2. The 1-min breakout-vs-fakeout / exhaustion test (exhaustion_test.py)
Built at 1-minute scale → **thousands** of sweep events (not 150). Event = fresh penetration of the prior
60-min swing low. Features: mean-reversion (`ret_pre`, `pen_depth`), confirming flow (`pre_sgn`, `pre_absorp`),
exhaustion/delta-flip (`post_sgn` = reaction flow after the sweep, `delta_div` = flow vs the prior sweep).

### The mirage, caught and killed
First label set barriers relative to `ref` (the local low through the decision window). Because `ref` is a
local minimum by construction, a tiny bounce hits the up-barrier almost automatically → **base rate 0.875–0.939
reversal**, "precision 0.95", "E[R] +0.8". **All artifact** — you can't enter at the low; you only know it
after the fact.

### The honest version
Enter at the **decision-time price** (D=3 min after the sweep — a price you could actually fill), barriers in
**horizon-scaled volatility** units. Base rate snaps to **~0.48–0.54**, and the edge disappears:

| symbol | base | best univ AUC | ALL ablation AUC | E[R/trade] top-15% (post-cost) |
|---|---|---|---|---|
| ZN | 0.482 | pre_sgn 0.551 | 0.537 | **−0.062** |
| ZB | 0.535 | pen_depth 0.549 | 0.509 | +0.070 (n=94, noise) |
| ES | 0.498 | pre_absorp 0.550 | 0.481 | **−0.052** |
| CL | 0.490 | ret_pre 0.527 | 0.506 | **−0.094** |

Flow features at **0.50–0.55 AUC** (noise), ablation **inconsistent** across instruments (a real effect would
be consistent), **E[R/trade] negative after costs** everywhere but one 94-event slice. The 1H hint was
small-sample overfitting — at 10× events with an honest label, it collapses to 0.55.

## Verdict
**Both the continuation (flow-with-the-grain) and exhaustion (delta-flip) theses fail the honest, at-scale,
tradeable test.** Order flow does not predict whether a sweep continues or reverses in a way you can monetize.

This closes the order-flow-divergence thesis family (six experiments now: 1s/5s/30s direction, 5-min candles,
cross-asset divergence, 1H reversal/continuation, 1-min exhaustion). Consistent finding throughout:
**order flow predicts short-horizon DIRECTION/continuation on large-tick rates (ZN/ZB 83–85% dir-acc) — but
that's market-making (moves < spread), and it does NOT predict reversal, exhaustion, or breakout-vs-fakeout
tradeably at any horizon tested.** The one real, tradeable edge remains **RV cointegration mean-reversion**,
with order flow best used as an **execution-timing overlay** for it.

### Methodological keeper
The local-low barrier artifact (base rate 0.88–0.94 → "precision 0.95" mirage) is a reusable trap to remember:
**triple-barrier labels must enter at a tradeable price and use horizon-scaled vol, never barriers measured
from a local extreme.** Any backtest that enters "at the low" is lying.
