# NQ Prior-Day Low Sweep Refinement Study

## Purpose

This study looks only at prior-day low sweep events, where the strategy direction is short. It uses the existing prior-day sweep framework and the MBP/event-level validation outputs from the frozen top-3 variants.

The goal is diagnosis, not optimization. No thresholds, stops, targets, entries, or execution assumptions were changed.

Every observation below is a hypothesis for future validation, not a new trading rule.

## Data Used

Input files:

- `data/backtests/nq_prior_day_sweep_strategy_prototype_mbp_top3_combined_2025-05-01_2026-05-23/prior_day_sweep_strategy_attempts.csv`
- `data/backtests/nq_prior_day_sweep_decision_tree_full_2025-05-01_2026-05-23/prior_day_sweep_decision_tree_events.csv`

Generated local output:

`data/backtests/nq_prior_day_low_refinement_mbp_top3_2025-05-01_2026-05-23`

Key output files:

- `prior_day_low_refinement_attempts.csv`
- `prior_day_low_refinement_strategy.csv`
- `prior_day_low_refinement_variants.csv`
- `prior_day_low_refinement_categorical.csv`
- `prior_day_low_refinement_numeric.csv`
- `prior_day_low_refinement_context_validation.csv`
- `prior_day_low_refinement_numeric_validation.csv`
- `prior_day_low_refinement_monthly.csv`
- `prior_day_low_refinement_summary.json`

Important row definition: this is attempt-level analysis, not unique-event analysis. The same sweep can appear more than once because the three frozen variants were tested on the same prior-day low sweep.

Important evidence split:

- In-sample: 2025-05-01 through 2026-01-31
- Holdout: 2026-02-01 through 2026-05-23

The holdout period was not used to choose thresholds. It is used only to check whether in-sample patterns survived.

## Baseline Short-Side Result

| Scope | Attempts | Fills | Target Rate | Stop Rate | Forced Flat Rate | Net PnL | Avg PnL / Attempt |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 204 | 179 | 50.3% | 44.7% | 5.0% | +$5,084 | +$24.92 |
| In-sample | 132 | 115 | 54.8% | 42.6% | 2.6% | +$4,755 | +$36.02 |
| Holdout | 72 | 64 | 42.2% | 48.4% | 9.4% | +$329 | +$4.57 |

Beginner read: the low-sweep short side stayed positive in holdout, but barely. The edge compressed a lot after 2026-02-01. That means the short-side idea is not dead, but it is not strong enough to trust without more careful validation.

## Market Continuation Labels

These labels come from the existing decision-tree event file. They answer a simple market question: after sweeping the prior-day low, did price reach the fixed continuation target before the fixed reversal target?

| Scope | Sweeps | Continuations | Reversals | Continuation Rate |
|---|---:|---:|---:|---:|
| Full | 99 | 70 | 29 | 70.7% |
| In-sample | 71 | 51 | 20 | 71.8% |
| Holdout | 28 | 19 | 9 | 67.9% |

Beginner read: prior-day low sweeps often continued lower by the fixed market label. But the actual strategy result was much weaker than the raw continuation label because entry timing, stop placement, target placement, skips, and execution sequencing all matter.

## Context Validation

This table compares context categories in-sample versus holdout. A good context should improve win rate in-sample and still improve win rate in holdout with enough trades.

| Factor | Category | IS Trades | IS Win Rate | IS Delta | HO Trades | HO Win Rate | HO Delta | HO PnL | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Time of day | Opening drive | 106 | 55.7% | +0.9 pp | 58 | 46.6% | +4.4 pp | +$453 | Survived, weak |
| Opening drive aligned | True | 106 | 55.7% | +0.9 pp | 58 | 46.6% | +4.4 pp | +$453 | Survived, weak |
| Overnight location vs sweep | Near sweep side | 73 | 54.8% | +0.0 pp | 47 | 44.7% | +2.5 pp | +$852 | Survived, weak |
| Overnight location | Lower third | 73 | 54.8% | +0.0 pp | 47 | 44.7% | +2.5 pp | +$852 | Survived, weak |
| Reclaim in 30s | False | 58 | 46.6% | -8.2 pp | 28 | 67.9% | +25.7 pp | +$2,323 | Holdout-only hint |
| Overnight trend vs sweep | With sweep | 100 | 60.0% | +5.2 pp | 56 | 39.3% | -2.9 pp | -$224 | Reversed |
| Overnight location vs sweep | Middle | 30 | 60.0% | +5.2 pp | 12 | 33.3% | -8.9 pp | -$448 | Reversed |
| Reclaim in 30s | True | 57 | 63.2% | +8.4 pp | 36 | 22.2% | -20.0 pp | -$1,994 | Reversed |

Beginner read:

- Opening-drive and near-sweep-side context survived holdout, but the improvement was small.
- Quick reclaim behavior was the most interesting holdout-only clue, but it did not work in-sample.
- Overnight trend with the sweep looked good in-sample and then failed in holdout.
- RTH gap direction could not explain much because the frozen framework already selected almost all low trades as `with_sweep` / `down`.

## Numeric Feature Validation

This table compares winning short trades versus losing short trades. AUC means how well the feature separates wins from losses. Around 0.50 means no separation. Higher than 0.60 starts to become more interesting, but only if it survives holdout.

| Feature | IS Winner Median | IS Loser Median | IS AUC | IS Cliff's Delta | HO Winner Median | HO Loser Median | HO AUC | HO Cliff's Delta | Read |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `post_5_30s_trade_events_per_second` | 35.88 | 33.96 | 0.527 | 0.055 | 33.32 | 29.68 | 0.581 | 0.162 | Best stable MBP hint |
| `directional_overnight_trend_pts` | 113.25 | 87.00 | 0.548 | 0.096 | 185.75 | 162.75 | 0.543 | 0.086 | Mild stable context hint |
| `sweep_0_5s_mbp_events_per_second` | 886.60 | 940.00 | 0.407 | -0.186 | 1096.80 | 1252.00 | 0.567 | 0.134 | Mixed distribution, noisy |
| `post_5_30s_mbp_events_per_second` | 647.00 | 689.16 | 0.435 | -0.131 | 782.44 | 949.28 | 0.505 | 0.010 | Quote churn, not useful alone |
| `sweep_distance_pts` | 2.00 | 21.13 | 0.429 | -0.143 | 60.00 | 1.25 | 0.797 | 0.595 | Reversed, do not trust |
| `sweep_minutes_after_rth_open` | 5.36 | 5.00 | 0.602 | 0.203 | 5.00 | 5.52 | 0.243 | -0.515 | Reversed, do not trust |
| `pre_60s_directional_aggressive_trade_ratio` | 0.065 | 0.028 | 0.661 | 0.323 | -0.031 | 0.021 | 0.261 | -0.478 | Reversed badly |
| `sweep_0_5s_trade_events_per_second` | 50.40 | 54.00 | 0.484 | -0.032 | 51.60 | 50.60 | 0.652 | 0.304 | Holdout-only, not proven |

Beginner read: the cleanest MBP feature is actual trade activity 5 to 30 seconds after the sweep. Winners had more real trade prints after the sweep in both in-sample and holdout. The effect is still modest, so it is a confirmation hypothesis, not a finished strategy rule.

The difference between trade events and MBP events matters. Trade events are real executions. MBP events include quote changes. Quote churn by itself did not separate winners cleanly.

## Factor Notes

### Overnight Location

Near-sweep-side location means the market was already positioned near the prior-day low side before the sweep. For low sweeps, that usually means the session was already sitting in the lower part of the overnight range.

This survived holdout, but only weakly:

- In-sample: 73 trades, 54.8% win rate, +$3,138
- Holdout: 47 trades, 44.7% win rate, +$852

Hypothesis: a low sweep may work better when price is already leaning toward that low, but this is not strong enough as a standalone filter.

### Overnight Trend

Overnight trend with the sweep looked strong in-sample:

- In-sample: 100 trades, 60.0% win rate, +$6,115

But it failed holdout:

- Holdout: 56 trades, 39.3% win rate, -$224

Hypothesis: overnight trend may be regime-sensitive. Do not use it as a rule yet.

### Time Of Day And Opening Drive

Most trades were opening-drive trades, so there is not much variation left to study.

- Opening drive in-sample: 106 trades, 55.7% win rate, +$4,381
- Opening drive holdout: 58 trades, 46.6% win rate, +$453

Sparse later buckets were poor:

- Midday in-sample: 0 wins / 3 losses
- Midday holdout: 0 wins / 6 losses

Hypothesis: keep later sweeps on the warning list, but sample size is too small to call this proven.

### RTH Gap Context

RTH gap context was not useful as a separator in this specific run.

All filled holdout low-sweep trades were already `with_sweep` and `down`, so there was no real contrast group.

Beginner read: if almost every row has the same value, that factor cannot explain why one trade won and another lost.

### Post-Sweep Trade Activity

The best stable MBP hint was `post_5_30s_trade_events_per_second`.

- In-sample winners: 35.88 trades/sec
- In-sample losers: 33.96 trades/sec
- Holdout winners: 33.32 trades/sec
- Holdout losers: 29.68 trades/sec

Hypothesis: after a prior-day low sweep, continuation shorts need real executed trade follow-through. More trades after the sweep may indicate actual participation instead of just quote noise.

### Sweep Distance

Sweep distance reversed between in-sample and holdout.

- In-sample winners had smaller median sweep distance than losers.
- Holdout winners had much larger median sweep distance than losers.

Hypothesis: this is unstable. Do not use sweep distance as a filter yet.

### Reclaim Behavior

`reclaimed_0_30s` means price traded back to the swept prior-day low within 30 seconds after the sweep.

The surprising holdout result:

- No reclaim in 30 seconds: 28 holdout trades, 67.9% win rate, +$2,323
- Reclaim in 30 seconds: 36 holdout trades, 22.2% win rate, -$1,994

But in-sample said the opposite:

- No reclaim in 30 seconds: 46.6% win rate
- Reclaim in 30 seconds: 63.2% win rate

Hypothesis: no quick reclaim is the most interesting new clue, but it is holdout-only. It must be frozen and tested on future unseen data before it can become an invalidation rule.

## Monthly Regime View

| Month | Attempts | Fills | Win Rate | Net PnL | Event Continuation Rate |
|---|---:|---:|---:|---:|---:|
| 2025-05 | 24 | 22 | 50.0% | +$852 | 88.9% |
| 2025-06 | 6 | 4 | 100.0% | +$784 | 60.0% |
| 2025-07 | 12 | 12 | 58.3% | +$647 | 50.0% |
| 2025-08 | 21 | 19 | 52.6% | +$639 | 75.0% |
| 2025-09 | 9 | 7 | 42.9% | -$48 | 85.7% |
| 2025-10 | 9 | 8 | 62.5% | +$513 | 83.3% |
| 2025-11 | 21 | 17 | 35.3% | -$603 | 66.7% |
| 2025-12 | 18 | 17 | 70.6% | +$1,627 | 70.0% |
| 2026-01 | 12 | 9 | 55.6% | +$344 | 71.4% |
| 2026-02 | 21 | 21 | 33.3% | -$344 | 66.7% |
| 2026-03 | 30 | 25 | 44.0% | +$350 | 70.0% |
| 2026-04 | 12 | 10 | 40.0% | -$190 | 57.1% |
| 2026-05 | 9 | 8 | 62.5% | +$513 | 80.0% |

Beginner read: the low-side short idea is not smooth. It had good months and weak months. Holdout was mixed: February and April were negative, March and May were positive. This is another reason not to optimize rules from the current sample.

## Practical Findings

1. Prior-day low sweep shorts remain the only side worth refining from the prior-day sweep family.
   The holdout result was positive, but only slightly.

2. Opening-drive and near-sweep-side context survived holdout, but weakly.
   They are reasonable baseline context, not proof of a strong edge.

3. Post-sweep real trade activity is the best MBP confirmation hypothesis.
   It separated winners from losers in the same direction in-sample and holdout.

4. Quick reclaim is the most interesting new diagnostic clue.
   In holdout, no reclaim within 30 seconds was much better than quick reclaim. But because in-sample did not agree, this must be treated as an unproven future-validation hypothesis.

5. Pre-sweep aggressive ratio did not survive.
   It looked strong in-sample and reversed badly in holdout.

6. Sweep distance and exact sweep timing did not survive.
   They changed direction between in-sample and holdout.

7. RTH gap context cannot be judged here.
   The frozen framework already selected almost all low trades into the same gap context, so there was no meaningful contrast.

## Conclusion

There is enough evidence to keep researching prior-day low sweep shorts, but not enough evidence to add a new optimized filter yet.

The most defensible next validation hypotheses are:

- Keep prior-day low sweeps separated from prior-day high sweeps.
- Preserve the existing opening-drive / near-sweep-side context as the baseline candidate.
- Freeze `post_5_30s_trade_events_per_second` as the main MBP confirmation feature to test next.
- Freeze no-reclaim-within-30-seconds as a separate future validation hypothesis, not a current rule.

The core out-of-sample integrity read is simple: the low-side result survived, but the edge became thin. Any refinement must be validated on future unseen data before it is allowed into a real strategy prototype.
