# NQ Opening-Range Middle-Third MBP Largest Validation

## Purpose

This reruns the exact frozen OR middle-third MBP execution study across the largest available MBP history in the repo/R2 setup.

No entries, stops, targets, filters, or thresholds were optimized.

The validation question:

- Does the observed OR middle-third, OR-high continuation effect survive with a larger sample?

## Frozen Rules

The rules are unchanged from the prior study.

- Market: `NQ.c.0`
- Opening range: 09:30-10:00 ET
- Required context: opening-range close in the middle third of the opening-range candle
- First break window: after 10:00 ET through 16:00 ET
- OR-high break: first MBP trade above OR high
- OR-low break: first MBP trade below OR low
- Continuation target: one OR width beyond the broken side
- Reversal target: opposite side of the OR
- Stop for execution tests: opposite side of the OR
- Target for execution tests: one OR width beyond the broken side
- Slippage: 1 tick
- Commission: $2.00 per side
- Quantity: 1 NQ contract
- Entry styles: immediate break, first retest, 30-second confirmation

## Data Coverage

Output folder:

`data/backtests/nq_opening_range_middle_third_mbp_largest_2025-05-01_2026-05-23/combined`

Available source-event window:

- First event date: 2025-05-02
- Last event date: 2026-05-22
- Total opening-range descriptive sessions: 270
- Middle-third context sessions: 74
- MBP partitions available: 74 of 74
- Holdout split: 2026-02-01

Beginner read: this used every middle-third opening-range event currently available from the existing opening-range study and confirmed that each one had MBP data available.

## Continuation Results

Confidence intervals are 95% Wilson intervals. They show the plausible range around the continuation rate given the sample size.

| Scope | Break Type | Events | Labeled | Continuations | Reversals | Ambiguous | Continuation Rate | 95% CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Full | All | 74 | 58 | 37 | 21 | 16 | 63.8% | 50.9% to 74.9% |
| Full | OR high | 36 | 24 | 19 | 5 | 12 | 79.2% | 59.5% to 90.8% |
| Full | OR low | 38 | 34 | 18 | 16 | 4 | 52.9% | 36.7% to 68.5% |
| In-sample | All | 52 | 42 | 26 | 16 | 10 | 61.9% | 46.8% to 75.0% |
| In-sample | OR high | 23 | 16 | 12 | 4 | 7 | 75.0% | 50.5% to 89.8% |
| In-sample | OR low | 29 | 26 | 14 | 12 | 3 | 53.8% | 35.5% to 71.2% |
| Holdout | All | 22 | 16 | 11 | 5 | 6 | 68.8% | 44.4% to 85.8% |
| Holdout | OR high | 13 | 8 | 7 | 1 | 5 | 87.5% | 52.9% to 97.8% |
| Holdout | OR low | 9 | 8 | 4 | 4 | 1 | 50.0% | 21.5% to 78.5% |

## Main Read

The OR-high continuation effect survived the larger validation sample.

Compared with the smaller prior run:

- The full OR-high continuation rate fell from 90.0% to 79.2%.
- The holdout OR-high continuation rate stayed high at 87.5%.
- The sample is larger, but still modest: only 24 labeled OR-high events full-sample and 8 labeled OR-high events in holdout.

Beginner read: the signal did not disappear when we added more data. That is good. But the confidence interval is still wide, so this is promising validation, not final proof.

OR-low breaks did not show the same effect:

- Full OR-low continuation: 52.9%
- Holdout OR-low continuation: 50.0%

Beginner read: the useful behavior still appears direction-specific. The current evidence points to OR-high continuation, not a symmetric OR breakout model.

## Execution Results

| Entry Style | Full Signals | Full Trades | Full Net PnL | Full Avg/Signal | Holdout Trades | Holdout Net PnL | Holdout Avg/Signal | Holdout Win Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Immediate break | 74 | 74 | $40,279 | $544.31 | 22 | $18,152 | $825.09 | 68.2% |
| First retest | 74 | 74 | $37,559 | $507.55 | 22 | $17,792 | $808.73 | 68.2% |
| 30-second confirmation | 74 | 40 | $12,290 | $166.08 | 8 | $83 | $3.77 | 50.0% |

Beginner read:

- Immediate break and first retest both stayed positive in full sample and holdout.
- 30-second confirmation technically remains positive full-sample, but holdout is basically flat and trade count collapses.
- The cleaner practical candidates remain immediate break and first retest.

## Walk-Forward Results

Walk-forward uses each later month as a test after at least 3 earlier months are available.

| Entry Style | Folds | Positive Folds | Positive Fold Rate | Walk-Forward Net PnL | Read |
|---|---:|---:|---:|---:|---|
| Immediate break | 10 | 8 | 80.0% | $36,361 | Stable positive |
| First retest | 10 | 8 | 80.0% | $35,141 | Stable positive |
| 30-second confirmation | 10 | 6 | 60.0% | $14,796 | Weak/fragile positive |

The two negative walk-forward months for immediate and first retest were October 2025 and May 2026.

Beginner read: walk-forward is important because it asks, "Did the next month work using only the past?" Immediate break and first retest passed that check better than the confirmation entry.

## Monthly Performance

Immediate break:

| Month | Signals | Net PnL | Avg/Signal | Win Rate |
|---|---:|---:|---:|---:|
| 2025-05 | 8 | $2,168 | $271.00 | 50.0% |
| 2025-06 | 9 | $119 | $13.22 | 55.6% |
| 2025-07 | 6 | $1,631 | $271.83 | 50.0% |
| 2025-08 | 3 | $6,368 | $2,122.67 | 100.0% |
| 2025-09 | 3 | $4,243 | $1,414.33 | 100.0% |
| 2025-10 | 6 | -$194 | -$32.33 | 50.0% |
| 2025-11 | 4 | $5,629 | $1,407.25 | 75.0% |
| 2025-12 | 9 | $1,524 | $169.33 | 44.4% |
| 2026-01 | 4 | $639 | $159.75 | 50.0% |
| 2026-02 | 4 | $3,859 | $964.75 | 75.0% |
| 2026-03 | 5 | $9,150 | $1,830.00 | 80.0% |
| 2026-04 | 7 | $7,377 | $1,053.86 | 71.4% |
| 2026-05 | 6 | -$2,234 | -$372.33 | 50.0% |

First retest:

| Month | Signals | Net PnL | Avg/Signal | Win Rate |
|---|---:|---:|---:|---:|
| 2025-05 | 8 | $1,943 | $242.88 | 50.0% |
| 2025-06 | 9 | -$1,011 | -$112.33 | 55.6% |
| 2025-07 | 6 | $1,486 | $247.67 | 50.0% |
| 2025-08 | 3 | $6,183 | $2,061.00 | 100.0% |
| 2025-09 | 3 | $4,173 | $1,391.00 | 100.0% |
| 2025-10 | 6 | -$294 | -$49.00 | 50.0% |
| 2025-11 | 4 | $5,474 | $1,368.50 | 75.0% |
| 2025-12 | 9 | $1,354 | $150.44 | 44.4% |
| 2026-01 | 4 | $459 | $114.75 | 50.0% |
| 2026-02 | 4 | $3,684 | $921.00 | 75.0% |
| 2026-03 | 5 | $9,280 | $1,856.00 | 80.0% |
| 2026-04 | 7 | $7,242 | $1,034.57 | 71.4% |
| 2026-05 | 6 | -$2,414 | -$402.33 | 50.0% |

## Validation Conclusion

The observed OR middle-third OR-high continuation effect survives the larger available MBP validation.

The strongest evidence:

- Full OR-high continuation: 19/24 = 79.2%
- In-sample OR-high continuation: 12/16 = 75.0%
- Holdout OR-high continuation: 7/8 = 87.5%
- Immediate and first-retest execution variants were positive in full sample, holdout, and 8 of 10 walk-forward folds.

The main cautions:

- OR-high labeled sample is still only 24 events.
- Holdout OR-high labeled sample is only 8 events.
- The full OR-high confidence interval is wide: 59.5% to 90.8%.
- October 2025 and May 2026 were weak months.
- The broad middle-third context is not enough by itself; the effect is concentrated in OR-high breaks.

Decision:

- This is strong enough to keep as a serious strategy-prototype candidate.
- It is not strong enough to optimize or add filters yet.
- The next proper step would be a frozen OR-high-only prototype using the same immediate-break and first-retest assumptions, with no parameter tuning.
