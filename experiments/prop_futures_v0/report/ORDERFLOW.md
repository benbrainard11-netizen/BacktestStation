# prop_futures_v0 — ORDER-FLOW accumulation -> breakout (exploratory)

**Date:** 2026-06-20. **Idea (user):** model *accumulating orders* (not a price proxy) — detect where
heavy volume is absorbed in a tight range, read which side is accumulating, then trade the breakout.
**Data:** MBP-1 trade tape, aggressor side ('B'=buy lifts ask, 'A'=sell hits bid) -> signed delta.
**EXPLORATORY:** tape is only ~2025-05 -> 2026-06 (~13 mo, ~280 RTH days), no walk-forward possible.

**Method:** detect accumulation box = first RTH 20-min window with range <= 0.4*ATR AND volume >=
expanding-baseline (fires ~150-220x/instrument); record net delta sign = flow direction. Trade the
breakout (stop = opposite box edge, day-flat, honest fills). Compare breakout ALIGNED with the
accumulated flow vs AGAINST it. `of_accum.py`.

## Result (net_R per trade; median in parens)

| Instrument | boxes | baseline | flow_aligned | flow_against | aligned−against |
|------------|------:|---------:|-------------:|-------------:|----------------:|
| RTY | 155 | +0.154 (−0.10) | **+0.209 (+0.00)** n84 | +0.087 (−0.23) n70 | **+0.12** |
| ES  | 218 | +0.004 (−0.45) | **+0.057 (−0.25)** n131 | −0.077 (−0.59) n85 | **+0.13** |
| NQ  | 166 | −0.016 (−0.19) | −0.042 n106 | +0.037 n54 | −0.08 |
| YM  | 148 | +0.070 (−0.27) | −0.047 (−0.38) n76 | +0.196 (+0.09) n70 | −0.25 |

## Verdict: signal present but NOT consistent (no robust edge yet)

- **Half-confirms:** on RTY and ES, flow-aligned breakouts beat flow-against by +0.12/+0.13R — the
  hypothesis (order flow predicts the break) working. This is the FIRST construction in the whole
  prop_futures_v0 effort to show *any* directional signal (the price-pattern families gave flat zero).
- **Half-inverts:** on NQ and YM the sign flips (fading the flow won, YM strongly). Per-cell deltas are
  only ~1-2 SE; across the 4 instruments the effect nets to ~zero. Every cell still has a negative
  median (lottery payoff). The "strong imbalance" subset was too rare to read (n=0-2).
- It is a **13-month, in-sample, exploratory** read — even the RTY/ES support could be noise.

**So:** not a deployable edge, but the only thread that flickered. Unlike the price-pattern nulls,
this one is worth *one* more honest push IF pursued — the open improvements are real: (1) the box
detection is still crude (tight-range+volume); a proper **absorption** metric (delta vs price
displacement, or resting-size depletion from MBO for ES/NQ/RTY/YM 2026-01+) may separate signal from
noise; (2) the **retest-continuation** entry (user's full spec) was not tested on the flow box;
(3) the consistent negative medians say *breakout-continuation* is the weak part — the data keeps
favoring **reversion** (YM's only positive-median cell was fading the flow), echoing RTY gap_fade.
Caveat: more constructions = more multiple-comparison exposure; any further push needs a fresh OOS
plan and ideally more tape, not just re-cutting these 13 months.
