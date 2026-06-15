# NQ Prior-Day Sweep Decision Tree Study

## Status

Implemented and run as a research study.

This is not a trading strategy yet. It is a context study asking:

```text
When NQ sweeps the prior-day high or prior-day low, which conditions made continuation more likely and which conditions made failure/reversal more likely?
```

The study uses only:

```text
prior_day_high
prior_day_low
```

It excludes overnight high/low sweeps from the decision table.

## Data Window

Inputs came from the existing liquidity sweep study outputs:

```text
data/backtests/nq_liquidity_sweep_outcomes_insample_discovery_2025-05-01_2026-02-01/
data/backtests/nq_liquidity_sweep_outcomes_holdout_oos_2026-02-01_2026-05-23/
```

Decision-tree study outputs were exported to:

```text
data/backtests/nq_prior_day_sweep_decision_tree_full_2025-05-01_2026-05-23/
```

Exported files:

```text
prior_day_sweep_decision_tree_events.csv
prior_day_sweep_decision_tree_labeled_events.csv
prior_day_sweep_decision_tree_factor_table.csv
prior_day_sweep_decision_tree_factor_rankings.csv
prior_day_sweep_decision_tree_combinations.csv
prior_day_sweep_decision_tree_combination_rankings.csv
prior_day_sweep_decision_tree_numeric_stats.csv
prior_day_sweep_decision_tree_monthly_outcomes.csv
prior_day_sweep_decision_tree_summary.json
prior_day_sweep_decision_tree_config.json
```

The `data/` folder is gitignored, so the raw CSV exports stay local.

## Fixed Outcome Definition

The older prior-day sweep result was about 67% continuation using the broader liquidity sweep study labels.

This decision-tree study freezes a simpler fixed target:

```text
continuation target = 8 NQ points beyond the swept prior-day level
reversal target     = 8 NQ points on the other side of the swept prior-day level
outcome window      = after the 30-second feature window, up to 60 minutes after sweep
```

For a prior-day high sweep:

```text
continuation = price reaches prior_day_high + 8 points
reversal     = price reaches prior_day_high - 8 points
```

For a prior-day low sweep:

```text
continuation = price reaches prior_day_low - 8 points
reversal     = price reaches prior_day_low + 8 points
```

Label source:

```text
1-minute bars, starting on the next complete minute after the 30-second feature window
```

This is conservative. If both continuation and reversal targets are touched inside the same 1-minute bar, the event is marked ambiguous instead of pretending we know which happened first.

MBP-1 is still used for the sweep detection and pre-sweep feature:

```text
pre_60s_directional_aggressive_trade_ratio
```

## Factors Tested

All bins were fixed before evaluation. No thresholds were optimized.

| Factor | Beginner meaning | Fixed bins |
|---|---|---|
| `level_type` | Prior-day high vs prior-day low | high / low |
| `overnight_trend_vs_sweep` | Did overnight move with or against the sweep direction? | with / against / neutral using +/- 8 points |
| `overnight_range_location_vs_sweep` | Did RTH open near the side that later swept? | near / middle / away |
| `rth_gap_vs_sweep` | Did RTH open gap with or against the sweep direction? | with / against / neutral using +/- 8 points |
| `time_of_day_bucket` | When did the sweep happen? | opening drive, late morning, midday, afternoon |
| `pre60_dir_aggr_ratio_band` | Did aggressive trading in the prior 60s lean with or against the sweep? | strong/mild against, neutral, mild/strong with |

## Walk-Forward Validation

The study uses expanding monthly walk-forward validation:

1. Train on the first 3 months.
2. Evaluate the next month.
3. Add that month to the training set.
4. Repeat through the final month.

Beginner translation:

```text
The study asks, "If this context looked good in the past, did it still help in the next unseen month?"
```

This is much safer than randomly shuffling rows because markets change over time.

## Overall Result

| Item | Value |
|---|---:|
| Total prior-day sweeps | 268 |
| Non-ambiguous fixed-label sweeps | 244 |
| Continuations | 172 |
| Reversals / failures | 72 |
| Ambiguous | 24 |
| Baseline continuation rate | 70.5% |
| Baseline failure rate | 29.5% |
| Months represented | 13 |

By level type:

| Level | Continuations | Reversals | Continuation rate | Failure rate |
|---|---:|---:|---:|---:|
| Prior-day high | 102 | 43 | 70.3% | 29.7% |
| Prior-day low | 70 | 29 | 70.7% | 29.3% |

The edge was not meaningfully different between prior-day highs and lows by themselves.

## Top Single Factors

| Rank | Factor | Best context | OOS sample | OOS continuation | OOS failure | Improvement vs baseline | Stability |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | `pre60_dir_aggr_ratio_band` | `mild_against_sweep` | 29 | 93.1% | 6.9% | +22.7 pts | 8/8 folds |
| 2 | `time_of_day_bucket` | `opening_drive` | 133 | 81.2% | 18.8% | +10.1 pts | 9/10 folds |
| 3 | `overnight_range_location_vs_sweep` | `near_sweep_side` | 92 | 81.5% | 18.5% | +10.4 pts | 8/10 folds |
| 4 | `rth_gap_vs_sweep` | `with_sweep` | 135 | 79.3% | 20.7% | +8.1 pts | 8/10 folds |
| 5 | `level_type` | `prior_day_low` | 75 | 72.0% | 28.0% | +0.9 pts | 6/10 folds |

Practical read:

```text
Level type alone did not explain much.
Session context explained more.
The strongest broad contexts were opening-drive sweeps, RTH gaps with the sweep, and opens near the sweep side of the overnight range.
```

## Worst Single Contexts

| Factor | Bad context | OOS sample | OOS continuation | OOS failure | Read |
|---|---|---:|---:|---:|---|
| `rth_gap_vs_sweep` | `against_sweep` | 38 | 42.1% | 57.9% | Gap against the sweep was bad for continuation. |
| `overnight_range_location_vs_sweep` | `away_from_sweep_side` | 30 | 43.3% | 56.7% | Opening away from the sweep side was bad. |
| `overnight_trend_vs_sweep` | `against_sweep` | 39 | 43.6% | 56.4% | Overnight trend against the sweep was bad. |
| `pre60_dir_aggr_ratio_band` | `mild_with_sweep` | 67 | 52.2% | 47.8% | Chasing into the sweep often failed. |
| `time_of_day_bucket` | `late_morning` | 20 | 35.0% | 65.0% | Weak but concerning sample. |

Beginner translation:

```text
Continuation worked best when the broader session was already leaning toward the sweep.
It failed more often when the sweep fought the gap, fought overnight direction, or happened after the opening-drive window.
```

## Top Context Combinations

Sparse combinations can look amazing by accident, so the practical ranking favors combinations with enough sample and stable walk-forward behavior.

| Rank | Combination | OOS sample | OOS continuation | OOS failure | Improvement vs baseline | Stability |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `near_sweep_side + rth_gap_with_sweep` | 88 | 84.1% | 15.9% | +13.0 pts | 9/10 folds |
| 2 | `rth_gap_with_sweep + mild_against_sweep_pre60` | 21 | 95.2% | 4.8% | +25.6 pts | 7/7 folds |
| 3 | `prior_day_low + opening_drive` | 51 | 84.3% | 15.7% | +13.2 pts | 8/10 folds |
| 4 | `prior_day_low + rth_gap_with_sweep` | 53 | 81.1% | 18.9% | +10.0 pts | 8/10 folds |
| 5 | `prior_day_low + overnight_trend_with_sweep` | 47 | 83.0% | 17.0% | +11.9 pts | 8/10 folds |

Most practical current combination:

```text
RTH opens near the sweep side of the overnight range
AND
RTH gap is with the sweep direction
```

Why this matters:

```text
This combination has a decent sample size, good continuation rate, and stable walk-forward behavior.
```

## Numeric Factor Evidence

| Feature | Continuation median | Reversal median | Separation AUC | Cliff's delta | Months same direction |
|---|---:|---:|---:|---:|---:|
| `sweep_minutes_after_rth_open` | 5.0 | 77.7 | 0.809 | -0.617 | 13/13 |
| `directional_rth_gap_pts` | 101.9 | 15.9 | 0.733 | 0.466 | 11/13 |
| `directional_overnight_trend_pts` | 81.0 | 12.0 | 0.687 | 0.375 | 11/13 |
| `pre_60s_directional_aggressive_trade_ratio` | 0.018 | 0.066 | 0.657 | -0.314 | 12/13 |
| `directional_rth_open_overnight_location` | 0.700 | 0.496 | 0.651 | 0.302 | 11/13 |

Important beginner read:

```text
Earlier sweeps were much better than later sweeps.
Bigger gap with the sweep helped.
Bigger overnight trend with the sweep helped.
More aggressive trade chasing into the sweep did not help; reversals had the higher median.
```

## What Looks Real Versus Noisy

Likely real enough to keep:

```text
opening-drive timing
RTH gap with the sweep
RTH open near the sweep side of the overnight range
overnight trend with the sweep
pre-60s aggressive trading not too strongly chasing with the sweep
```

More likely noisy or too sparse:

```text
level type by itself
tiny two-factor samples under 20 trades
late-day buckets with very few examples
any rule that depends on one very small category
```

## Decision Table Takeaway

Historically better continuation contexts:

```text
opening_drive
near_sweep_side
rth_gap_with_sweep
overnight_trend_with_sweep
mild_against_sweep or neutral pre-60s aggressive trade ratio
```

Historically worse continuation contexts:

```text
rth_gap_against_sweep
overnight_trend_against_sweep
away_from_sweep_side
late_morning or later sweeps
mild_with_sweep pre-60s aggressive trade ratio
```

## Strategy Prototype Readiness

There is enough evidence to justify designing a simple prototype candidate, but not enough to trade it or optimize thresholds.

The safest prototype direction would be:

```text
prior-day high/low sweep continuation
only during the opening-drive window
only when session context supports the sweep
especially when RTH opens near the sweep side of the overnight range and gaps with the sweep
```

The `pre60_dir_aggr_ratio_band = mild_against_sweep` result is interesting, but the sample is only 29 OOS examples. It should be used as a hypothesis or optional confirmation, not as the main rule yet.

## Caveats

The fixed-label run uses 1-minute bars for target labeling to make the full walk-forward study practical over R2.

This is conservative because:

```text
labels start on the next complete minute after the 30-second feature window
same-bar continuation/reversal conflicts are marked ambiguous
```

For a final strategy backtest, the execution simulator should eventually use MBP-1/event-level sequencing for fills and target/stop order priority.
