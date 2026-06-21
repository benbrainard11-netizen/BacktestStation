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

## v2 — continuation vs reversion, with a fresh design/holdout split (`of_accum_v2.py`)

Did it right (user: "do it right, test both ways"). Same absorption-box detection; added the box volume
POC; design = 2025-05..2026-02-14, holdout = 2026-02-15..2026-06-09 (read once). Three day-flat strats:
cont_flow (continuation in flow dir), rev_fade (fade the breakout back to POC), rev_vsflow (fade only
against-flow breakouts). Honest fills; fades check the entry bar (start_at_entry=True) so the breakout
bar's overshoot can stop them.

**Pooled (4 index futures):**
| strat | design net_R | holdout net_R | win% | median | ex-top5% |
|-------|------:|------:|----:|------:|------:|
| cont_flow | +0.069 | **−0.016** | 46% | −0.35 | −0.15 |
| rev_fade | −0.052 | −0.019 | **62%** | **+0.30** | −0.06 |
| rev_vsflow | −0.049 | **−0.001** | **66%** | **+0.34** | −0.05 |

**Findings:**
1. **CONTINUATION = DEAD.** RTY design +0.358 → holdout −0.058; inconsistent across the complex; pooled
   holdout negative. Chasing the accumulation breakout does not work. Final.
2. **REVERSION = a REAL, STABLE pattern (net slightly negative as built).** Fading the accumulation-box
   breakout back to the POC is right **62–66%** with a **+0.30..+0.34 median**, and it is consistent
   across ALL 4 instruments AND design↔holdout (not a single-window/single-instrument artifact like
   everything before). The MEAN is ~−0.02..−0.05R only because the ~⅓ real breakouts run to the stop and
   outweigh the many small fade-wins. rev_vsflow (trapped-aggressor fade) is ~breakeven OOS (−0.001).

**Significance.** This is the first construction in the whole module that is (a) directionally
consistent across the complex and (b) stable in/out of sample. The signal (accumulation breakouts revert
~2/3 of the time) is genuine. It is NOT deployable as-built (slightly negative EV), but its **shape —
high win rate, smooth, ~0 EV — is exactly the "controllable-variance, not-negative-expectancy generator"
that prop_model_v0 Layer-1 needs** for variance-shaping the eval (profit from the eval asymmetry without
a market edge). The expectancy gap is an exit-geometry problem (rare big losses), which is tunable — BUT
the holdout is now spent, and the consistent slight-negativity warns against assuming a tune fixes it.

**Disciplined next step (NOT done):** to develop the exit honestly needs MORE TAPE (pull more MBP-1
history on the 247 box, or forward-test), not re-cutting these 13 months. Then either (a) find an
exit/stop geometry that makes EV robustly ≥0 on fresh data, or (b) feed the ~0-EV high-win generator
into the Layer-1 eval-economics model. Don't optimize exits on the spent holdout.

## v3 — exit-geometry sweep on the reversion (`of_accum_v3.py`). RESULT: exit tuning does NOT rescue EV.

User accepted the spent-holdout risk to tune the exit. Swept stop_buf {0.3,0.5}*ATR × target
{POC, 1.5R, 3R, ride-to-close} = 8 configs on the reversion fade, pooled over the 4 index futures.
**Every config is design-NEGATIVE (−0.035 to −0.120) and none is positive on both splits.** The "let
winners run" hypothesis FAILED: R-multiple and ride targets dropped the win rate to ~37–48% with no mean
improvement, because **the reversion winners do not run past the POC** — price reverts to the volume POC
and then stalls/reverses. The POC IS the natural target; capping there preserves the 58–65% win rate but
the mean stays slightly negative (the ~⅓ real breakouts run full to the stop). Best design (ride_sb0.5
−0.035) → holdout −0.017, per-instrument mixed (RTY −0.02, ES −0.07, NQ +0.08, YM −0.04).

**CONCLUSION (order-flow accumulation, final):** continuation is dead; reversion is a GENUINE, stable,
cross-instrument, in/out-of-sample-consistent **high-win (~62%) ~0-to-slightly-negative-EV generator**
that **cannot be tuned positive via exit geometry.** It is NOT a standalone market edge. Its only live
use is the **Layer-1 eval-economics route** (`prop_model_v0` + `sizing_v1`): a high-win, smooth, ~0-EV
generator is the variance shape that can profit from the eval asymmetry WITHOUT a market edge — that is
now a sizing/eval question, not a market-research one. If Layer-1 math can't make a slightly-negative-EV
generator pay, then prop_futures_v0 is a complete, honest day-flat NULL.

## v4 — event dataset + reverse-vs-continue model (`event_build.py` + `analyze_events.py`)

To "test it many ways" without variant-spraying: built one event table (1,189 accumulation-breakout
events over 6 liquid symbols ES/NQ/YM/RTY/CL/NG, 13-mo MBP-1, design 856 / holdout 333) with causal
order-flow features known AT the breakout + outcomes, and modeled **reverse-vs-continue** (logistic).

**LOOK-AHEAD CAUGHT:** the first run included `overshoot_atr` (how far price ran AFTER the breakout — a
future quantity) in the feature set → faked AUC 0.79 holdout, conditional EV +0.40R, 79% win. That is the
same future path as the target (small overshoot ≡ it reverted); circular. Removed it (it is an OUTCOME,
not a feature).

**HONEST result (causal features only):** AUC design 0.596 → **holdout 0.541 (≈ coin flip)**; conditional
(fade if P(revert)>0.5 else chase) EV **+0.009 holdout** — does NOT beat always-fade (−0.003) or
always-chase (+0.017). Every causal feature has near-zero IC, INCLUDING all order-flow ones
(box_absorption +0.01, box_delta_sign −0.07, breakout-bar delta +0.02, flow-alignment +0.02); only
time-of-day reaches ~0.12 and doesn't generalize. **Order flow does NOT predict the reverse-vs-continue
resolution out-of-sample.** Entry-timing note: breakouts overshoot ~0.3–0.4 ATR before reverting (edge
entry isn't badly late), but moot without a directional edge.

**FINAL (accumulation/order-flow line): NULL.** Continuation dead; reversion a real stable ~62%-win
~0-EV pattern; exits can't tune it positive; and the reverse-vs-continue resolution is unpredictable
from causal features (incl order flow), leak-checked. The reversion's only remaining possible use is the
Layer-1 eval-economics shape question. The leak-catch is the case study for why the event-dataset +
causal-feature discipline matters (variant-spraying would have "deployed" the fake AUC-0.79 model).

