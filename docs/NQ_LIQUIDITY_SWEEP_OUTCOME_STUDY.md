# NQ Liquidity Sweep Outcome Study

## Status

Design spec only. This is not a strategy and should not create entries, stops, targets, or live-trading rules yet.

The purpose is to prove whether MBP-1 features have predictive value around liquidity sweeps before we use them inside a strategy.

## Beginner Summary

A liquidity sweep happens when price trades beyond an obvious high or low where many traders may have stops or breakout orders.

This study asks:

If NQ sweeps an important level, can MBP-1 order book behavior help us tell whether that sweep is more likely to continue or fail?

We are not trying to predict the whole day. We are studying one event at a time:

1. Price sweeps a level.
2. We measure order book behavior around that sweep.
3. Later, price either continues through the level or reverses back.
4. We test which MBP-1 features best separated those two outcomes.

## Levels To Detect

For each NQ session, detect sweeps of four levels:

| Level | Definition | When The Level Is Known |
|---|---|---|
| Prior day high | Previous completed RTH session high | Before the next session opens |
| Prior day low | Previous completed RTH session low | Before the next session opens |
| Overnight high | Globex high from prior evening open through 09:29:59 ET | At 09:30 ET |
| Overnight low | Globex low from prior evening open through 09:29:59 ET | At 09:30 ET |

Primary sweep detection window:

```text
09:35 ET through 16:00 ET
```

The first five minutes of RTH are skipped at first because the open can be unusually noisy.

## Sweep Detection

Use MBP-1 trade prints, not bar highs/lows, to detect the actual sweep.

For NQ:

```text
high sweep = trade price >= level_price + 0.25
low sweep  = trade price <= level_price - 0.25
```

Use only the first sweep of each level per session in the baseline study. This keeps the dataset clean and avoids letting one messy session create many duplicate examples.

Each sweep event should include:

```text
session_date
level_type
level_price
sweep_side
sweep_ts
sweep_price
ticks_through_level
time_of_day
```

## Outcome Labels

Each sweep gets one of three labels:

```text
continuation_breakout
failed_breakout_reversal
ambiguous
```

For a high sweep:

- Continuation means price expands higher after the sweep.
- Failed breakout / reversal means price trades back below the swept level and expands lower.

For a low sweep:

- Continuation means price expands lower after the sweep.
- Failed breakout / reversal means price trades back above the swept level and expands higher.

The baseline timing rule:

```text
feature window: sweep_ts through sweep_ts + 30 seconds
outcome window: sweep_ts + 30 seconds through sweep_ts + 60 minutes
```

This matters because the feature window must finish before the outcome window starts.

Baseline outcome distance:

```text
max(8 NQ points, 0.5 * pre-sweep 15m realized range)
```

If neither continuation nor reversal wins inside the outcome window, label the event `ambiguous`. Do not force a fake answer.

## MBP-1 Feature Groups

Measure features in these windows:

| Window | Purpose |
|---|---|
| pre_60s | Baseline book state before the sweep |
| pre_10s | Immediate pressure before the sweep |
| sweep_0_5s | The burst during the sweep |
| post_5_30s | The early reaction after the sweep |

Feature groups:

| Group | Beginner Meaning |
|---|---|
| Imbalance | Whether bid size or ask size is heavier |
| Size changes | Whether liquidity is being added or pulled |
| Spread | Whether the market is tight or unstable |
| Event intensity | How fast the book is updating |
| Trade activity | Whether real trades are active around the level |

Candidate features include:

```text
top_book_imbalance
directional_top_book_imbalance
mean_bid_size
mean_ask_size
bid_size_change
ask_size_change
directional_size_change
mean_spread
max_spread
spread_widening
mbp_event_count
mbp_events_per_second
trade_count
trade_volume
trade_events_per_second
aggressive_trade_ratio
ticks_through_level
time_to_reclaim_level
```

Direction-normalized features should be created so high and low sweeps can be compared together:

```text
direction_sign = +1 for high sweeps
direction_sign = -1 for low sweeps

directional_feature = direction_sign * raw_feature
```

Positive directional values should mean the feature supports continuation. Negative values should mean the feature supports reversal.

## Leakage Rules

No feature may use data from the future outcome window.

Rules:

- Prior day levels must be based only on completed prior RTH data.
- Overnight levels must freeze at 09:30 ET.
- Sweep detection must use prints available at the sweep time.
- Feature windows must end before outcome labeling begins.
- Outcome labels must not be used inside features.
- Do not use the session close, final high, final low, or future bars as features.
- Do not tune thresholds on the same data used to claim predictive value.
- Split validation by date/month, not random rows.

## Knowable Before Entry Flag

Every feature must be tagged with one of these timing classes:

| Timing Class | Meaning | Eligible For Future Strategy Work? |
|---|---|---|
| pre_sweep | Known before the sweep happens | Yes |
| at_sweep | Known at the sweep print | Yes, if entry waits until after the print |
| post_sweep_confirmation | Known after a fixed confirmation window, such as +30s | Yes, if entry waits until the window closes |
| post_outcome | Uses data after the outcome starts | No, research-only/leakage |

The top 5 list must explicitly state whether each feature is knowable before a possible entry. Any `post_outcome` feature is disqualified from predictive ranking.

## Required Outputs

After the study completes, export:

```text
liquidity_sweep_events.csv
liquidity_sweep_features.csv
liquidity_sweep_feature_rankings.csv
liquidity_sweep_top5_features.csv
liquidity_sweep_feature_distributions.csv
liquidity_sweep_monthly_stability.csv
liquidity_sweep_examples.csv
liquidity_sweep_summary.json
```

## Top 5 Feature Ranking Requirement

After the study completes, identify the top 5 MBP-1 features that most consistently separate continuation sweeps from failed breakout / reversal sweeps.

For each feature, report:

```text
rank
feature_name
feature_group
feature_window
timing_class
knowable_before_entry
sample_size_total
sample_size_continuation
sample_size_reversal
sample_size_ambiguous_excluded
continuation_median
reversal_median
median_difference
standardized_effect_size
cliffs_delta
auc
auc_bootstrap_ci_low
auc_bootstrap_ci_high
ks_stat
permutation_p_value
monthly_auc_values
monthly_effect_direction
months_with_same_effect_direction
worst_month_auc
best_month_auc
stability_score
ranking_reason
```

## Statistical Evidence

Each top feature must show evidence from multiple angles.

Use:

- AUC: how well the feature separates continuation from reversal.
- Median difference: how different the typical continuation value is from the typical reversal value.
- Cliff's delta: effect size that works well when feature distributions are not normal.
- KS statistic: whether the two distributions have meaningfully different shapes.
- Permutation test: whether the separation is unlikely under shuffled labels.
- Bootstrap confidence intervals: uncertainty estimate, resampled by session date.

Beginner translation:

We do not want a feature that only looks good because of one lucky day. We want a feature that repeatedly looks different when sweeps continue versus when they fail.

## Effect Size

Do not rank features by p-value alone.

Report effect size in at least two ways:

1. Raw median difference.
2. Standardized or distribution-aware effect size, preferably Cliff's delta.

Suggested interpretation for Cliff's delta:

| Absolute Cliff's Delta | Interpretation |
|---:|---|
| < 0.147 | Tiny |
| 0.147 to 0.33 | Small |
| 0.33 to 0.474 | Medium |
| > 0.474 | Large |

Tiny effects should not be treated as useful just because they are statistically significant.

## Monthly Stability

For every candidate feature, compute the separation by month.

Report:

```text
month
sample_size
continuation_count
reversal_count
monthly_auc
monthly_median_difference
monthly_cliffs_delta
effect_direction
```

A feature is more promising if:

- It has the same effect direction in most months.
- It does not depend on one unusually good month.
- Its worst month is not catastrophically bad.
- It has enough examples in each month to be believable.

## Sample Size Rules

The top 5 list must show sample size clearly.

Minimum recommended evidence before calling a feature promising:

```text
at least 100 labeled non-ambiguous sweeps total
at least 30 continuation examples
at least 30 reversal examples
at least 3 calendar months represented
```

If the available MBP-1 window is smaller than this, the result must be labeled:

```text
early evidence only
```

Do not claim a robust edge from a tiny sample.

## Ranking Method

Rank features from most promising to least promising using:

1. Eligibility: must be knowable before entry.
2. Directional consistency across months.
3. Out-of-sample or walk-forward AUC.
4. Effect size.
5. Bootstrap confidence interval quality.
6. Sample size.
7. Simplicity and interpretability.

Disqualify features if:

- They use post-outcome data.
- They only work in one month.
- Their sample size is too small.
- They are impossible to know before a realistic entry.
- Their signal direction flips repeatedly.

## Examples To Export

Export examples for inspection:

```text
best_continuation_signals
best_reversal_signals
false_continuation_signals
false_reversal_signals
ambiguous_chop_examples
```

Each example should include:

```text
session_date
level_type
sweep_ts
outcome_label
top_feature_values
reason_selected
```

## Final Deliverable

The final study report should answer:

1. Which level type had the clearest continuation/reversal behavior?
2. Which MBP-1 feature groups mattered most?
3. What are the top 5 features?
4. What statistical evidence supports each feature?
5. What is the effect size?
6. Is the effect stable by month?
7. What is the sample size?
8. Is the feature knowable before entry?
9. Which features are research-only because they leak future information?
10. Is there enough evidence to justify moving toward a strategy prototype?

The answer may be "not enough evidence yet." That is a valid research result.
