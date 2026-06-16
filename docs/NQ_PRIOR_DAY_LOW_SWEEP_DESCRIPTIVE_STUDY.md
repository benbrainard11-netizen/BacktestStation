# NQ Prior-Day Low Sweep Descriptive Study

## Purpose

This is a descriptive study, not a strategy study.

It uses only prior-day low sweep events from the frozen MBP/event-level prior-day sweep validation. The goal is to compare winning short trades versus losing short trades and identify which effects point in the same direction in both in-sample and holdout data.

No thresholds were optimized. No entry, stop, target, or execution assumption was changed.

## Data Used

Input files:

- `data/backtests/nq_prior_day_sweep_strategy_prototype_mbp_top3_combined_2025-05-01_2026-05-23/prior_day_sweep_strategy_attempts.csv`
- `data/backtests/nq_prior_day_sweep_decision_tree_full_2025-05-01_2026-05-23/prior_day_sweep_decision_tree_events.csv`

Generated local output:

`data/backtests/nq_prior_day_low_descriptive_mbp_top3_2025-05-01_2026-05-23`

Key output files:

- `prior_day_low_descriptive_trades.csv`
- `prior_day_low_descriptive_categorical.csv`
- `prior_day_low_descriptive_numeric_distributions.csv`
- `prior_day_low_descriptive_numeric_effects.csv`
- `prior_day_low_descriptive_consistency.csv`
- `prior_day_low_descriptive_summary.json`

Important row definition: this is attempt-level analysis. The same sweep can appear multiple times because the frozen top-3 variants were tested on the same sweep.

## Sample

| Scope | Trades | Wins | Losses | Win Rate |
|---|---:|---:|---:|---:|
| Full | 179 | 90 | 89 | 50.3% |
| In-sample | 115 | 63 | 52 | 54.8% |
| Holdout | 64 | 27 | 37 | 42.2% |

Beginner read: the holdout period was much weaker. Effects that only look good in the full sample are not enough. The useful question is whether the same winner-versus-loser difference appears before and after 2026-02-01.

## How To Read The Metrics

For categorical fields, `winner_minus_loser_share` means:

`share of winners in that category - share of losers in that category`

Positive means the category showed up more often in winners. Negative means it showed up more often in losers.

For categorical effect size, Cramer's V measures the strength of the relationship between the category field and win/loss outcome. Near 0 is weak.

For numeric fields:

- Median difference = winner median minus loser median.
- AUC above 0.50 means higher values leaned toward winners.
- Cliff's delta above 0 means values were generally higher in winners.
- Cliff's delta below 0 means values were generally higher in losers.

## Directionally Consistent Effects

These effects pointed the same way in both in-sample and holdout.

| Effect | IS Direction | HO Direction | IS Effect | HO Effect | Read |
|---|---|---|---:|---:|---|
| `post_5_30s_trade_events_per_second` | Higher in winners | Higher in winners | +1.92 trades/sec | +3.64 trades/sec | Best numeric holdover |
| `time_of_day_bucket=opening_drive` | More common in winners | More common in winners | +3.3 pp | +16.2 pp | Consistent, but mostly confirms existing gate |
| `opening_drive_aligned=True` | More common in winners | More common in winners | +3.3 pp | +16.2 pp | Same information as opening drive here |
| `overnight_range_location_vs_sweep=near_sweep_side` | More common in winners | More common in winners | +0.03 pp | +7.5 pp | Weak but consistent |
| `overnight_range_location=lower_third` | More common in winners | More common in winners | +0.03 pp | +7.5 pp | Same information as near sweep side for lows |

Beginner read: the only numeric feature that stayed directionally consistent was real trade activity after the sweep. Opening-drive and near-side overnight location stayed in the right direction, but their in-sample effects were small.

## Numeric Effects

| Feature | IS Winner Median | IS Loser Median | IS AUC | IS Cliff | HO Winner Median | HO Loser Median | HO AUC | HO Cliff | Direction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `post_5_30s_trade_events_per_second` | 35.88 | 33.96 | 0.527 | 0.055 | 33.32 | 29.68 | 0.581 | 0.162 | Consistent |
| `sweep_distance_pts` | 2.00 | 21.13 | 0.429 | -0.143 | 60.00 | 1.25 | 0.797 | 0.595 | Flipped |
| `sweep_minutes_after_rth_open` | 5.36 | 5.00 | 0.602 | 0.203 | 5.00 | 5.52 | 0.243 | -0.515 | Flipped |
| `time_to_reclaim_seconds` | 0.0023 | 0.0096 | 0.448 | -0.103 | 0.0383 | 0.0087 | 0.433 | -0.134 | Mixed/flipped |

The post-sweep trade activity feature is the cleanest descriptive holdover. The effect is not huge, but it survives the in-sample/holdout split in the same direction.

Sweep size looks tempting in holdout, but it flipped direction. In-sample losers had larger sweeps; holdout winners had larger sweeps. That is not stable evidence.

Exact time after RTH open also flipped. The categorical opening-drive bucket looked better than trying to interpret exact minutes.

## Categorical Effects

### Time Of Day

Opening-drive trades appeared more in winners in both samples:

- In-sample: winner share minus loser share = +3.3 percentage points
- Holdout: winner share minus loser share = +16.2 percentage points

Midday trades appeared more in losers in both samples, but the sample was tiny:

- In-sample: 3 trades
- Holdout: 6 trades

Do not turn this into a new rule yet. It is a descriptive warning, not enough evidence.

### Overnight Location

Near-sweep-side / lower-third overnight location pointed the same way in both samples:

- In-sample: +0.03 percentage points
- Holdout: +7.5 percentage points

This is directionally consistent, but weak. It says near-side location is not contradicted by holdout, not that it is a strong standalone edge.

Middle overnight location flipped:

- In-sample: higher in winners
- Holdout: higher in losers

So middle location is not stable.

### Opening Drive Alignment

`opening_drive_aligned=True` matched the opening-drive result:

- In-sample: +3.3 percentage points
- Holdout: +16.2 percentage points

This is not a new independent signal. It mostly confirms that the frozen framework's opening-drive context remained healthier than the sparse non-opening trades.

### Reclaim Behavior

Reclaim behavior was the most dramatic inconsistency.

No reclaim within 30 seconds:

- In-sample: higher in losers by 16.8 percentage points
- Holdout: higher in winners by 46.0 percentage points

Reclaim within 30 seconds:

- In-sample: higher in winners by 16.8 percentage points
- Holdout: higher in losers by 46.0 percentage points

Beginner read: this is interesting, but unstable. The holdout result is strong, but because it says the opposite of in-sample, it should be treated as a future-validation hypothesis only.

## Main Findings

1. The most consistent descriptive effect was post-sweep real trade activity.
   Winning shorts had higher `post_5_30s_trade_events_per_second` in both samples.

2. Opening-drive context stayed directionally favorable.
   This supports keeping it as context in research, but it is not a new optimized rule.

3. Near-side overnight location stayed directionally favorable, but weakly.
   The in-sample difference was almost zero, so this is only mild support.

4. Reclaim behavior did not survive directionally.
   It flipped hard between in-sample and holdout.

5. Sweep size did not survive directionally.
   It also flipped hard between in-sample and holdout.

6. Exact time of day did not survive as a numeric effect.
   The broad opening-drive bucket was more stable than exact minutes after RTH open.

## Conclusion

The descriptive study supports one practical research idea: after a prior-day low sweep, real trade activity in the 5-30 second post-sweep window is the most stable winner-versus-loser separator.

The other stable-looking categories, opening drive and near-side overnight location, are useful context but weak as independent effects.

The strongest-looking holdout observations, especially no quick reclaim and large sweep size, should not be promoted to rules because their direction did not match in-sample.

Next research should freeze any new hypothesis before testing it on future unseen data. No thresholds should be tuned from this descriptive output.
