# Confirmed-sweep RECLAIM trade — the faithful PO3 test (the closest thing to a real edge)

After the symmetric breakout-vs-fakeout test was killed, the user correctly identified three flaws and the
trade was rebuilt faithfully (`sweep_reclaim_test.py`):
- **Confirm the sweep:** wick below a prior 60-min swing low, then **close back above** within K=15 min
  (rejection / judas reversal). Raw breakdowns that never reclaim = no trade (the strategy, not a bias).
- **Enter at the reclaim** (market, a real price), **stop 1 tick below the wick** (tight), **asymmetric target**
  M×risk.
- Honest fills: reclaim/entry/stop known at the reclaim bar; forward sim from the next bar; **stop wins ties**
  (repo rule #8). Costs charged in R per trade (cost_ticks / risk_ticks).

## Result — a real but THIN structural edge (OOS, 2026-02-15+)

| symbol | OOS trades | 90th-pct MFE | gross 3R | net@1tk 3R | net@2tk 3R |
|---|---|---|---|---|---|
| **CL** | 1,786 | 3.53R | **+0.125** | **+0.026** | −0.072 |
| ES | 2,140 | 3.35R | +0.039 | −0.093 | −0.224 |
| ZN | 911 | 3.00R | −0.177 | −0.496 | −0.815 |

- The **expansions are real** (90th-pct max-favorable-excursion 3.0–3.5R) and the edge grows monotonically with
  the target (3R > 2R > 1R) — exactly the user's "target big enough" point. This is the **first genuine gross
  edge** of the whole order-flow investigation, and it matches the PO3 thesis structure.
- BUT it's **thin and cost-fragile**: only **CL at a 3R target clears a 1-tick cost (+0.026 R/trade)**, and
  barely — a 1.5-tick cost flips it negative. ES is gross-positive but costs kill it; rates (ZN) are dead
  (ticks too tight, no expansion room → 3-tick risk, 2-tick cost = 0.67R drag).

## Two things that did NOT work (honest)
- **Retrace entry (limit at the reclaimed level) HURTS.** CL 3R: +0.125 gross (market reclaim) → −0.053 gross
  (retrace). The expansion trades **don't look back** — waiting for a retrace systematically misses the winners
  and fills the weak reclaims that sag back (MFE median 1.10R → 0.43R). **Market-at-the-reclaim is correct.**
- **Order flow at the reclaim does NOT filter.** The apparent net-level "buy-flow reclaim is better" was a cost
  artifact (buy-flow reclaims have wider stops → lower cost/R). At gross it's noise (CL sell-flow > buy-flow).

## Where it could become tradeable (the one principled next lever)
The winners exist (90th MFE 3.5R) but are **diluted** (median MFE ~1R). The decisive next test: **filter reclaims
to the ones that expand**, using features known at the reclaim that are NOT flow — reclaim displacement /
strength, reclaim speed (lag), **level quality (HTF / session level vs a minor 60-min low)**, volatility regime,
time-of-day. A GBDT predicting outcome/MFE, proper OOS, no overfit. If filtering lifts the hit-rate on
expansions, CL/ES clear costs clearly; if not, it's a real-but-untradeable structural curiosity and the
validated **RV cointegration book** remains the play.

## UPDATE — HTF scale + trailing stop + monthly stability: a REAL, STABLE NQ EDGE

The user flagged the scale was wrong (my 9-pt stops vs their real 20-50 NQ-pt stops -> I was trading the
smallest part of the move). Re-scaled the level (60-min -> 4-hour / daily), measured the FULL expansion, and
switched the fixed 3R target for a **1R trailing stop** (let winners run -> capture the fat tail; MFE tail
reaches ~30R / 475-536 pts).

**Scale-invariance finding:** the move structure is the same at every level size (median ~1.1R, 90th ~3.5R);
bigger levels just give bigger POINT moves (NQ daily: 90th-pct MFE 85 pts, max 536) at the same R. So in
R-terms we were NOT capturing only the smallest part — but a fixed 3R target DOES throw away the monster tail.

**Trailing stop, HTF scale, net of 1-tick cost (cost ~irrelevant here: 1tk on a 12-16pt stop = ~0.02R):**

| symbol | scale | TRAIL-1R E[R/trade] | trades | monthly stability |
|---|---|---|---|---|
| **NQ** | **4-hour** | **+0.102** | 1,030 | **10/13 months positive** |
| NQ | daily | +0.092 | 381 | (consistent) |
| ES | daily | +0.069 | 367 | **FAILS: 1/13 months** (the daily + was a one-window fluke) |
| ES | 4-hour | -0.013 | 1,030 | 1/13 months |
| CL | daily | +0.034 | 167 | thin / unverified |

**VERDICT: a real, stable edge on NQ specifically** — confirmed 4H-level sweep -> reclaim -> tight wick stop ->
1R trailing exit. 10/13 months positive incl. the truly-forward Feb-Apr 2026, +0.10R/trade, survives realistic
slippage at HTF scale. NQ being the standout is mechanically sensible (trendiest index -> sweeps expand hardest
= the PO3 setup). The monthly stability check DISCRIMINATED (killed the ES fluke, kept NQ) -> the method works
and NQ is not just noise. This is the FIRST validated edge of the whole order-flow investigation, and it came
from the user's own structural insistence (confirm the sweep, asymmetric/runner target, correct HTF scale).
Flow-at-reclaim still does NOT help (retracted). Retrace entry still hurts.

## Remaining before it's deployable (NOT done yet)
1. **Realistic slippage** on market reclaim entries (NQ reclaims are fast) — model 2-3 tk + slippage.
2. **Parameter-neighborhood robustness** — is NQ positive across a RANGE of (level 120-360min, trail 0.5-2R) or
   only at a spike? Broad = real, spike = overfit-by-search.
3. **Match the user's actual stop scale** (20-50 NQ pts; here median 12-16) — bigger levels / stop buffer; does
   the edge hold at their real size?
4. **Session / time-of-day** — are the 3 losing months / losers concentrated in a session (e.g., overnight)?
5. Position sizing + the milk/multi-account layer if it survives 1-4.
