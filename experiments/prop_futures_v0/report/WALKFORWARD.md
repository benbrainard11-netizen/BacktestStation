# prop_futures_v0 — WALK-FORWARD re-validation (day-flat family bake-off)

**Date:** 2026-06-20. **Why:** the 12-month sealed holdout was consumed by the ES-ORB shot and no
fresh/future data exists, so RTY gap_fade (which passed every on-merits verification) could not get a
clean single-shot holdout. The rigorous substitute: walk-forward the **selection process** — at each
fold, re-run the full bake-off (6 instruments × 5 families × params) on prior-years-only, deploy what
the survivor rule picks, measure on the next unseen year. `walkforward.py`, expanding folds.

## Result

| Fold | Selected on past data | Train net_R | OOS n | OOS net_R | OOS median_R |
|------|-----------------------|------------:|------:|----------:|-------------:|
| 2021   | RTY gap_fade (g0.5/s0.75)        | +0.086 | 47 | **−0.005** | −0.164 |
| 2022   | GC afternoon_trend (m0.5/s1.0)   | +0.124 | 10 | +0.070 | −0.041 |
| 2023   | GC afternoon_trend               | +0.117 | 10 | **−0.052** | −0.093 |
| 2024   | RTY gap_fade                     | +0.056 | 84 | +0.065 | +0.154 |
| 2025H1 | GC afternoon_trend               | +0.122 |  5 | +0.031 | +0.028 |

- **Pooled OOS (single best-selected per fold):** n=156, mean **+0.036**, median +0.014, win 51.3%,
  sumR +5.56 — **BUT ex-top-2% = −0.011 (NEGATIVE).** The positive mean is outlier-carried; remove the
  top 2% of trades and the OOS edge is gone — the exact disqualifier the survivor rule pre-committed to.
- **Pooled OOS (all survivors equal-weight):** n=1610, mean +0.0097, median +0.021, win 51.6% —
  economically negligible.
- **RTY gap_fade selected in only 2/5 folds**, and split (−0.005 / +0.065) on those two.

## Verdict: NULL — no walk-forward-validated day-flat edge

Three independent failures: (1) the **selection is unstable** (RTY gap_fade picked 2/5 folds; GC
afternoon_trend — tiny n≈10/yr, high train mean — won the rest, a small-sample-overfit symptom);
(2) **RTY gap_fade is inconsistent OOS** (one negative fold, one positive); (3) the **pooled OOS mean
is outlier-driven** (ex-top-2% negative), the same mirage that sank the ES ORB holdout. The strong
single-window design result (+0.073R, median +0.108, all guards passed *in-design*) did NOT generalize
when the selection process was forced to prove itself out-of-sample.

## What this closes

Combined with Phase C (ORB holdout NULL), **prop_futures_v0 finds no robust, OOS-validated, deployable
day-flat edge** across: vol-gated opening-range breakout + 5 day-flat families (gap-fade, gap-cont,
VWAP-revert, afternoon-trend, pre-RTH-break) × 6 liquid instruments (ES/NQ/YM/RTY/CL/GC). This is now
the 5th–6th independent day-flat null in the broader lab. The binding fact: the lab's one robust edge
(energy-RV cointegration, OOS Sharpe +1.44) is **multi-day**, which the universal prop flat-by-close
rule disallows.

## Addendum — accum_poc_break (accumulation→breakout→POC-retest→continuation), added 2026-06-20

User-proposed 6th family: initial-balance accumulation, volume-profile POC of the accumulation, trade
the IB breakout's pullback that retests the POC then resumes. Design survivors on ES (1, ex-top-2%
+0.008) and RTY (2, ex-top-2% +0.012/+0.029) — RTY best (mean +0.080, ex-2020 +0.111). NQ/YM/CL/GC null.
**Re-run walk-forward with this family in the universe = WORSE:** it was the process's 2024 pick
(train +0.104) and LOST OOS (−0.014); pooled single-best OOS went **negative (−0.003, ex-top-2% −0.064)**.
Focused RTY read: per-year +0.10/+0.05/−0.13/**+0.31**/+0.12/+0.13/**−0.01/−0.03** (2018→2025) — mean
carried by 2021, block-bootstrap 90% CI **[−0.002,+0.161] crosses zero** (P=0.945), and **decaying
(2024 & 2025 both negative)**. Same profile as RTY ORB: in-design-positive, OOS-fragile, recency-fading.
NULL.

## Durable assets (the real output)

`orb_engine.py` (honest fill core), `families.py` (5 day-flat families), `sweep.py` / `screen_families.py`
(design bake-off with the **outlier-robust ex-top-2% survivor guard** — which caught both the NQ
pre-RTH and the pooled-OOS mirages), `walkforward.py` (process-level OOS), and MBP-1 tick fill
verification. The discipline repeatedly distinguished a real mean from an outlier-carried one — that is
the reusable win.
