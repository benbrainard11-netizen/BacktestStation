# Pre-Registration — Locked Walk-Forward 2026-05-17

_Falsifiable claims about expected results, written BEFORE running the locked-window simulations._

## Why pre-register

Per GPT-5 Pro Research protocol: writing expected results before seeing them prevents post-hoc rationalization. If the result doesn't match expectations, we can't move the goalposts.

Specifically: if I see the locked-window result and then say "well, of course it was going to look like that because of X" without having said X in advance, I am fooling myself.

## Lockfile reference

This pre-registration is bound to `experiments/locked_walkforward_2026_05_17/lockfile.yaml`. Any change to that lockfile invalidates this pre-registration.

## Background context (no peeking at locked windows allowed)

Known from exploratory window (2020-2025):

| Family | cum_R (2020-2025) | avg_R | yrs_positive |
|---|---:|---:|---:|
| FVG strict | +6,342 (post 2-tick slippage) | 0.150 | 6/6 |
| OB strict | +5,262 (post slippage) | 0.440 | 6/6 |
| Swing reversed | +2,947 (post slippage, 15% haircut) | 0.200 | 6/6 |
| Sweep reversed (filtered) | +3,200 (post 2-tick slippage, hour-filter) | 0.529 | 6/6 |

Critical caveat: these were discovered through audit on the 2020-2025 window. Per the GPT-5 Pro review, this means the SELECTION of which families/directions/filters to include was made with information from this window. The locked walk-forward tests whether those selections **generalize** to 2018-2019 and 2026 YTD.

## Pre-registered expectations

### A. Headline claim

**The candidate is bar-level real to the precision the simulator measured (89% TBBO retention validated), and the underlying event-class biases (Type B properties) are market-structural, not regime-specific.**

If true: the candidate should remain Type-B positive on 2018-2019 with per-trade R values in the same order of magnitude as 2020-2025.

If false: 2018-2019 will show meaningful failures — flat results, negative cum_R, or per-trade R degraded by more than 50% from 2020-2025 values.

### B. Per-family expectations for 2018-2019

**Loose bar — should be met if the strategy is real:**

For each family, on 2018-2019:
- `cum_R > 0` (positive overall)
- `yrs_positive >= 1 of 2` (at least one year positive)

**Tighter bar — should be met if the strategy generalizes well:**

For each family, on 2018-2019:
- `avg_R within ±40% of 2020-2025 value`
- For families with `direction_reversed=True` (Swing reversed, Sweep reversed): the same direction must remain positive — i.e., running with `direction_reversed=False` should give a negative result (NOT a sign that the direction flips by regime)

### C. Combined-portfolio expectations for 2018-2019

- Total cum_R across 4 families: **positive**
- No single family contributes > 75% of total (i.e., the basket isn't carried by one family)
- Both NQ and ES contribute positive cum_R in aggregate
- Top 20 days contribute < 60% of total cum_R (i.e., not carried by a handful of outlier days)
- Result survives 2-tick slippage (primary fill model)

### D. 2026 YTD expectations (small sample, loose)

- Total cum_R across 4 families: **positive** (any positive)
- Pro-rated annual rate within **±70% of 2020-2025 expected**

The wider tolerance reflects that 2026 YTD is ~95 trading days — too small for tight CIs. The 2026 YTD test is **supplementary evidence**, not the gate.

## What would falsify the candidate

This is the ruthless side. Any of these on 2018-2019 = candidate fails:

1. **3+ of 4 families have negative cum_R.** Even with regime differences, 3-of-4 failure is strong evidence the candidate is overfit.

2. **Combined cum_R is negative.** Hard fail.

3. **Either NQ or ES alone is materially negative** while the other carries the result. Suggests symbol-specific overfitting.

4. **Top 5 days contribute > 70% of total cum_R.** Suggests result is dominated by a small number of outlier events, not a real recurring edge.

5. **For Swing reversed or Sweep reversed: the reversed direction is NOT positive** while natural direction IS positive. Would indicate the "reverse" decision was 2020-2025 regime-specific.

6. **All 4 families' avg_R is more than 60% degraded** from 2020-2025 values, even if signs remain positive. Suggests the magnitudes were inflated by selection.

## What would falsify the candidate's deployability without falsifying the bar-level edge

These don't kill the strategy entirely, but kill the deploy candidate as currently specified:

1. Strong dependence on a single market hour or session.
2. Inability to survive the 1-tick-through target stress test in Lane 1's fill-model torture work.
3. Roll-mechanic distortion revealed by Lane 1's continuous-symbol audit.

These would require redesign, not abandonment.

## What I expect to actually see

I'm being honest about my prior here, knowing that writing it down constrains me:

I expect:
- **FVG strict** to be the most robust — it's a structural market-microstructure event, and FVGs form on every timeframe. Should generalize. Expected avg_R on 2018-2019: ~0.10-0.15.
- **OB strict** to mostly generalize. The OB definition is the cleanest of the four (price closes past a specific level). Expected avg_R: ~0.30-0.45.
- **Swing reversed** to be the riskiest. The "reverse direction" finding was the most surprising on 2020-2025 — could be a regime artifact. Expected avg_R: ~0.05-0.20 if generalizes; near zero or negative if regime-specific.
- **Sweep reversed (filtered)** to mostly generalize, but the hour filter is the post-hoc element. Expected avg_R on 2018-2019: ~0.30-0.50 if filter generalizes; ~0.10-0.20 if filter is regime-specific.

**Combined cum_R expectation on 2018-2019 (2 years):** ~+2,000R to +4,000R (vs 2020-2025's ~+18K combined naive sum scaled to 2 years = ~+6K — so the lower end of my range reflects "edge generalizes but at lower magnitude").

**If combined cum_R on 2018-2019 is ≥ +1,000R: candidate likely real.**
**If combined cum_R on 2018-2019 is ≤ 0: candidate likely overfit.**
**If combined cum_R on 2018-2019 is between 0 and +1,000R: ambiguous, requires deeper investigation.**

## Process commitments

I commit to:
1. Running the locked simulation ONCE per window (2018-2019, 2026 YTD) — no retries unless a documented bug exception applies.
2. Recording pass/fail per the lockfile thresholds BEFORE doing any postmortem analysis.
3. Not modifying the candidate, trade rule, fill model, hour filter, or any other locked element based on locked-window results.
4. If the candidate fails, marking it as `failed_locked_walkforward_2026_05_17` and treating any subsequent research on the same families as a NEW protocol (not an "adjustment").

## Sign-off

- Lockfile committed at: `experiments/locked_walkforward_2026_05_17/lockfile.yaml`
- Lockfile hash (post-creation, before run): TBD (compute after committing this MD)
- Repo commit at lock time: `e2368d0c7f74e7655adf6dcb553bba3e223f299f`
- Locked at: 2026-05-17 (date of this file)
- Operator: benpc (Claude Opus 4.7 assistant + human operator)
- Status: locked, not yet run
