# prop_futures_v0 — HOLDOUT LOG (sealed-shot register)

The holdout is read ONCE per pre-registered config. Every shot logged here win-or-lose.
Bar-only holdout = last 12 months (2025-06-10 → 2026-06-09). Design = 2016-01-01 → 2025-06-09.

---

## Shot #1 — ES.c.0 vol-gated ORB — 2026-06-20 — RESULT: NULL (outlier-driven, not deployable)

**Pre-registered config** (best design survivor, cleared by the verification workflow's GO):
`or_minutes=30, target_R=0.0 (ride-to-close, day-flat), vol_gate=prior_atr @ 166.329 ticks (design-derived)`.
Design net_R = **+0.086** (n=941, both halves +, ex-2020 +0.107, bootstrap P(edge>0)=0.97, survives 2t slip).

**Holdout (2025-06-10 → 2026-06-09):**
| metric | value |
|---|---|
| n trades | 227 |
| mean net_R | **+0.013** |
| median net_R | **−0.359** |
| win rate | 0.436 |
| mean ex-top-1 | −0.026 |
| mean ex-top-3 | −0.058 |
| total R | +2.86 (top 3 trades = +8.61, +3.79, +3.54 = +15.9R; other 224 ≈ −13R) |

**Verdict: NULL / NOT DEPLOYABLE.** The mean is technically > 0, so the naive bar "net_R>0 OOS"
passes — but both pre-registered read-guards FAIL: the **median trade loses 0.36R** and the mean
**flips negative when the 3 best trades are removed**. The design edge (+0.086) was substantially a
few trend-day outliers; OOS it shrank ~6× to a coin-flip carried by 3 of 227 days. This is the exact
fragility the verification flagged for `target_R=0` ride-to-close configs (single +42.6R design
outlier, no tail guard in the survivor rule). A 43.6%-win-rate, outlier-dependent trend-ride is also
the worst shape for a prop daily-loss limit. **The ES ORB shot is SPENT.**

## Not fired (NO-GO at verification, holdout preserved)
- **CL.c.0** — design +0.027 but bootstrap CI straddles zero (P=0.77) and the edge flips negative on
  +1 tick of cost; mean driven by one +42.6R outlier. NO-GO.
- **RTY.c.0** — design +0.026 but CI crosses zero (P=0.83) and worst year is 2025 (−0.11), i.e. the
  edge is decaying into the holdout window. NO-GO.
- **NG.c.0** — 0 design survivors. Dead.

## What this means
The honestly-built vol-gated opening-range-breakout does **not** produce a robust, cost-surviving,
shape-appropriate day-flat edge on CL / NG / ES / RTY. The design survivors were either tail-driven
(ES/CL `target_R=0`), cost-fragile (CL), or decaying (RTY). The **engine, sweep harness, MBP-1 fill
verification, and discipline are the durable assets** — reusable for the next pre-registered hypothesis.

**Methodological lesson for v2:** ranking design survivors by raw mean net_R steered the pre-registered
pick to the highest-variance, most outlier-fragile config (`target_R=0`). A robustness-aware selection
(bootstrap CI clear of zero + mean-survives-removing-top-k) would have favored the fixed-R variants
(e.g. ES 15m/2R/or_width: design +0.075, halves +0.093/+0.056, bounded tail) — which were NOT tested
OOS and remain a clean, untested hypothesis for a future walk-forward (the single 12-mo holdout is now
partially seen, so a fresh OOS scheme is required).
