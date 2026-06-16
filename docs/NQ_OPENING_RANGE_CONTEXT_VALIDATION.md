# NQ Opening-Range Context Validation

## Purpose

This is a follow-up validation study using the frozen NQ opening-range definitions.

It does not build a strategy, change targets, optimize thresholds, or add filters.

The goal is only to ask:

- Which opening-range contexts improved continuation probability?
- Which contexts worsened continuation probability?
- Did those effects survive holdout and walk-forward checks?

## Frozen Event Definition

The event definitions are unchanged from the prior opening-range descriptive study:

- Opening range: 09:30-10:00 ET
- First break window: after 10:00 ET through 16:00 ET
- High break: first bar whose high trades above the OR high
- Low break: first bar whose low trades below the OR low
- Continuation target: one full OR width beyond the broken side
- Reversal target: the opposite side of the OR
- Same-bar continuation and reversal target hits are labeled ambiguous

Only labeled continuation/reversal events are used for context probability testing.

## Data Used

Output folder:

`data/backtests/nq_opening_range_descriptive_2025-05-01_2026-05-23`

New validation files:

- `opening_range_descriptive_context_validation.csv`
- `opening_range_descriptive_walk_forward.csv`

Study window:

- Start: 2025-05-01
- End: 2026-05-23 available window
- Last analyzed session: 2026-05-22
- Holdout split: 2026-02-01

Baseline:

| Scope | Sessions | Labeled | Continuation Rate |
|---|---:|---:|---:|
| Full | 270 | 179 | 53.1% |
| In-sample | 192 | 126 | 53.2% |
| Holdout | 78 | 53 | 52.8% |

Beginner read: baseline continuation is only slightly above 50/50. A context needs to beat this by a meaningful amount and remain stable in later data before we should care about it.

## Contexts Tested

The study evaluated:

- First-break direction: OR high break vs OR low break
- Opening-drive alignment: whether the 09:30-10:00 candle direction aligned with the later break
- Opening-drive close position: lower, middle, or upper third of the OR candle range
- Overnight trend: up, down, or flat using the frozen 8-point deadzone
- Overnight trend alignment: whether overnight trend aligned with the break
- Overnight inventory/location: where RTH opened inside the overnight range
- Gap context: RTH gap up, down, or flat using the frozen 8-point deadzone
- Gap alignment: whether the RTH gap aligned with the break
- Time of break: first 15m, 15-30m, 30-60m, 60-120m, or after 120m

## Validation Method

Two checks are used.

Holdout test:

- In-sample period is before 2026-02-01.
- Holdout period is 2026-02-01 onward.
- A context must point the same direction in both periods to be interesting.

Walk-forward test:

- Each month is tested using only the months before it as the training window.
- The table records whether the next month improved or worsened continuation versus that month's baseline.
- This is stricter than a single holdout split because it checks whether the effect keeps showing up through time.

Fixed reporting rule:

- At least 10 labeled holdout events.
- At least 3 walk-forward folds.
- At least 60% of walk-forward folds point in the same direction.
- "Stable" also requires at least 5 percentage points of effect in both holdout and average walk-forward delta.

These are reporting rules only. They are not trade-entry thresholds.

## Stable Improver

Only one context clearly improved continuation probability:

| Context | Full Rate | IS Rate | IS Delta | HO Rate | HO Delta | WF Mean Delta | WF Direction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Opening-drive close in middle third | 63.8% | 61.9% | +8.7 pp | 68.8% | +15.9 pp | +15.5 pp | 7/11 positive folds |

Beginner read: when the opening range closed in the middle third of its own 09:30-10:00 range, later breaks were more likely to continue. This is the only context that survived the stricter validation as a meaningful improver.

Possible market intuition:

- A middle-third close can mean the opening drive did not fully exhaust to one extreme.
- The later break may have more room to continue because price was not already stretched at the end of the opening range.

Important caution:

- Sample size is still modest: 58 full labeled events and 16 holdout labeled events.
- This is good enough for a research lead, not enough for a strategy by itself.

## Stable Worsener

One context clearly worsened continuation probability:

| Context | Full Rate | IS Rate | IS Delta | HO Rate | HO Delta | WF Mean Delta | WF Direction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Opening-drive close in upper third | 41.8% | 44.7% | -8.5 pp | 35.0% | -17.8 pp | -15.9 pp | 9/12 negative folds |

Beginner read: when the opening range closed in the upper third, later OR breaks were less likely to continue. This was the cleanest negative context.

Possible market intuition:

- The opening drive may have already spent directional energy.
- Later upside breaks may be more prone to failure, and downside breaks are rare from this context.

## Mild But Small Contexts

These pointed the same direction but were too small to call meaningful:

| Context | Full Rate | IS Delta | HO Delta | WF Mean Delta | Read |
|---|---:|---:|---:|---:|---|
| OR low first break | 55.8% | +3.3 pp | +1.3 pp | +2.8 pp | Directionally consistent but small |
| OR high first break | 50.5% | -3.2 pp | -1.1 pp | -6.1 pp | Directionally consistent but small |
| Opening-drive close in lower third | 55.6% | +0.9 pp | +6.0 pp | +0.3 pp | Directionally consistent but small |

Beginner read: low breaks still look a little better than high breaks, but the edge is small. It is not enough to justify a strategy rule.

## Contexts That Did Not Survive

Opening-drive alignment:

- Aligned direction was not stable.
- In-sample delta: -2.0 pp
- Holdout delta: +1.0 pp
- Walk-forward mean delta: -0.6 pp

Overnight inventory/location:

- Upper-third overnight location looked better in holdout but worse in-sample.
- Middle-third flipped worse in holdout.
- Lower-third was too mild and inconsistent.

Overnight trend and overnight trend alignment:

- Both flipped between in-sample, holdout, and walk-forward.
- No stable overnight trend context was proven.

Gap context and gap alignment:

- Gap direction and gap-with-break alignment were inconsistent.
- The holdout did not confirm the in-sample direction.

Time of break:

- First 15 minutes after 10:00 had enough sample but worsened in holdout.
- Later break buckets were too sparse to trust.

## Answer

The only opening-range context with stable, meaningful improvement was:

1. Opening-drive close in the middle third of the 09:30-10:00 range.

The only context with stable, meaningful deterioration was:

1. Opening-drive close in the upper third of the 09:30-10:00 range.

The OR low first-break effect remains a mild research hint, but it is too small to treat as a strong edge.

The other requested context families - opening-drive alignment, overnight trend/inventory, gap context, and time-of-break - did not show stable enough evidence to carry forward as primary research drivers yet.

## Conclusion

There is not enough evidence here to build a strategy.

There is enough evidence to justify one future predeclared research hypothesis:

When the 09:30-10:00 opening range closes in the middle third, first OR breaks may have better continuation odds; when it closes in the upper third, continuation odds may be worse.

That future study should stay descriptive first and should validate on new unseen data before any trading rules are considered.
