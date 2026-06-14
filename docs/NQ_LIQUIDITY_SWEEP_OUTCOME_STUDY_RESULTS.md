# NQ Liquidity Sweep Outcome Study Results

## Status

Implemented and rerun as an in-sample discovery study with a reserved holdout.

This is still research only. No thresholds were optimized, no entry/stop/target rules were created, and no strategy was built from these results.

The earlier `2026-03-02` to `2026-05-01` run should be treated as a pilot only. It was too narrow and it touched data that we now want to reserve for validation.

## Data Split

R2 coverage checked directly:

| Dataset | Coverage |
|---|---|
| NQ MBP-1 partitions | `2025-05-01` through `2026-05-27` |
| NQ 1-minute bars | `2015-01-01` through `2026-05-22` |
| Usable overlap for this study | `2025-05-01` through `2026-05-22` |

Study split:

| Split | Date window | Purpose | Used in this report? |
|---|---|---|---|
| In-sample discovery | `2025-05-01` through `2026-02-01` half-open | Find/rank features | Yes |
| Reserved holdout | `2026-02-01` through `2026-05-23` half-open | Later out-of-sample validation | No |

Important honesty note: March/April 2026 were seen in the earlier pilot run, so the holdout is not perfectly unseen from a human-memory standpoint. But the corrected feature rankings and conclusions below do not use any February-May 2026 data.

## Where The Outputs Are

Combined in-sample export folder:

```text
data/backtests/nq_liquidity_sweep_outcomes_insample_discovery_2025-05-01_2026-02-01/
```

Monthly shard folders:

```text
data/backtests/nq_liquidity_sweep_outcomes_insample_2025-05-01_2025-06-01/
data/backtests/nq_liquidity_sweep_outcomes_insample_2025-06-01_2025-07-01/
data/backtests/nq_liquidity_sweep_outcomes_insample_2025-07-01_2025-08-01/
data/backtests/nq_liquidity_sweep_outcomes_insample_2025-08-01_2025-09-01/
data/backtests/nq_liquidity_sweep_outcomes_insample_2025-09-01_2025-10-01/
data/backtests/nq_liquidity_sweep_outcomes_insample_2025-10-01_2025-11-01/
data/backtests/nq_liquidity_sweep_outcomes_insample_2025-11-01_2025-12-01/
data/backtests/nq_liquidity_sweep_outcomes_insample_2025-12-01_2026-01-01/
data/backtests/nq_liquidity_sweep_outcomes_insample_2026-01-01_2026-02-01/
```

Exported files include:

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

The `data/` folder is intentionally gitignored because it can contain local/generated market data. This report records the important results in git without committing raw exports.

## Beginner Summary

A liquidity sweep is when price trades just beyond an obvious high or low where stops and breakout orders may sit.

This study asked:

```text
After NQ sweeps an important level, can MBP-1 order book behavior help separate continuation sweeps from failed/reversal sweeps?
```

The study looked at four level types:

| Level type | Beginner meaning |
|---|---|
| `prior_day_high` | Yesterday's regular-session high |
| `prior_day_low` | Yesterday's regular-session low |
| `overnight_high` | The high made before the 09:30 ET open |
| `overnight_low` | The low made before the 09:30 ET open |

The corrected in-sample result is much more useful than the pilot because it covers 9 months instead of 2 months.

## In-Sample Sample Size

| Item | Value |
|---|---:|
| Symbol | `NQ.c.0` |
| In-sample window | `2025-05-01` through `2026-02-01` half-open |
| Total sweep events | 400 |
| Non-ambiguous labeled sweeps | 383 |
| Continuation breakouts | 225 |
| Failed breakout / reversals | 158 |
| Ambiguous | 17 |
| Calendar months represented | 9 |

This meets the original minimum sample guideline:

```text
at least 100 non-ambiguous sweeps
at least 30 continuation examples
at least 30 reversal examples
at least 3 calendar months
```

## Leakage Safety

The study keeps the timing clean:

- Prior-day levels use only the previous completed RTH session.
- Overnight levels freeze at 09:30 ET.
- Sweeps are detected from MBP-1 trade prints.
- Sweep detection starts at 09:35 ET.
- Feature windows finish before the outcome window starts.
- Outcome labels are not used inside features.
- The February-May 2026 holdout was not used for feature ranking.
- No thresholds were optimized.

Beginner translation: the research does not let itself cheat by using the answer before the decision point.

## Level Type Results

| Level type | Continuations | Reversals | Ambiguous | Non-ambiguous | Continuation rate |
|---|---:|---:|---:|---:|---:|
| `prior_day_low` | 49 | 24 | 2 | 73 | 67.1% |
| `prior_day_high` | 70 | 35 | 6 | 105 | 66.7% |
| `overnight_low` | 54 | 44 | 2 | 98 | 55.1% |
| `overnight_high` | 52 | 55 | 7 | 107 | 48.6% |

The most useful level-type behavior was at prior-day levels. Both `prior_day_high` and `prior_day_low` leaned continuation in-sample.

Overnight levels were less useful by themselves. `overnight_low` leaned mildly continuation, while `overnight_high` was almost balanced.

This does not mean "buy/sell every prior-day sweep." It means prior-day levels are better context candidates than overnight levels in this sample.

## Feature Group Results

| Feature group | Best rank | Best separation AUC | Median separation AUC | Beginner read |
|---|---:|---:|---:|---|
| `event_intensity` | 1 | 0.616 | 0.580 | Best ranked group. More book activity after the sweep leaned continuation. |
| `size_changes` | 3 | 0.600 | 0.552 | Some signal, but not very strong. |
| `trade_activity` | 4 | 0.643 | 0.529 | Best single AUC came from post-sweep directional trading, but group median was weak. |
| `imbalance` | 7 | 0.615 | 0.544 | Some post-sweep/at-sweep signal, not broad dominance. |
| `spread` | 17 | 0.582 | 0.551 | Weakest practical group in this run. |

Separation AUC:

```text
0.50 = no separation
0.60 = mild separation
0.70 = useful-looking separation
```

The important read: the effects are real enough to validate on holdout, but they are mild. Nothing here is a slam-dunk edge yet.

## Exported Top 5 Eligible Features

These are the exact top 5 from `liquidity_sweep_top5_features.csv`.

All are leakage-eligible, but all five require waiting until after the sweep. None of the exported top 5 are pure pre-sweep signals.

| Rank | Feature | Group | Timing | Sample | Separation AUC | Cliff's delta | Permutation p | Stability | Beginner meaning |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | `post_5_30s_mbp_event_count` | `event_intensity` | `post_sweep_confirmation` | 383 | 0.616 | 0.233 | 0.0066 | 1.00 | Continuations had more MBP updates after the sweep. |
| 2 | `post_5_30s_mbp_events_per_second` | `event_intensity` | `post_sweep_confirmation` | 383 | 0.616 | 0.233 | 0.0066 | 1.00 | Same signal as rank 1, normalized by time. |
| 3 | `sweep_0_5s_directional_size_change` | `size_changes` | `post_sweep_confirmation` | 383 | 0.590 | -0.181 | 0.9203 | 1.00 | Directionally stable, but the permutation test does not support it well. |
| 4 | `post_5_30s_trade_count` | `trade_activity` | `post_sweep_confirmation` | 383 | 0.620 | 0.240 | 0.0033 | 0.89 | Continuations had more trades after the sweep. |
| 5 | `post_5_30s_trade_events_per_second` | `trade_activity` | `post_sweep_confirmation` | 383 | 0.620 | 0.240 | 0.0033 | 0.89 | Same signal as rank 4, normalized by time. |

Two pairs are duplicates in meaning:

- `post_5_30s_mbp_event_count` and `post_5_30s_mbp_events_per_second`
- `post_5_30s_trade_count` and `post_5_30s_trade_events_per_second`

So the best independent idea is not five separate ideas. It is mostly:

```text
After the sweep, continuations tend to have more MBP/book activity and more actual trade activity.
```

## Evidence-Backed Carry-Forward Features

If we freeze a small list for later OOS validation, these are cleaner than blindly taking the raw top 5:

| Feature | Why it is worth carrying forward |
|---|---|
| `post_5_30s_trade_count` | Mild separation, good p-value, stable in 8 of 9 months. |
| `post_5_30s_mbp_event_count` | Mild separation, good p-value, stable direction in all 9 months. |
| `post_5_30s_directional_aggressive_trade_ratio` | Highest single separation AUC in the trade-activity group, but less stable. |
| `post_5_30s_directional_top_book_imbalance` | Mild imbalance signal with good p-value, but one month disagreed. |
| `pre_10s_mean_bid_size` | Best pre-sweep signal; weak but stable and knowable before the sweep. |

This is the list I would freeze for holdout validation. It avoids treating duplicate count/rate columns as separate discoveries.

## Pre-Sweep-Only Findings

The strongest pure pre-sweep feature was:

| Feature | Rank | Separation AUC | Cliff's delta | Permutation p | Direction |
|---|---:|---:|---:|---:|---|
| `pre_10s_mean_bid_size` | 6 | 0.585 | -0.169 | 0.010 | Reversals had higher values |

Beginner meaning: before the sweep, reversal examples tended to show slightly more bid size at the top of book.

This is interesting because it is known before the sweep completes, but the effect is weak. It is not enough by itself to build a strategy.

Other pre-sweep features were weaker or less stable.

## Monthly Stability

Best stability:

- `post_5_30s_mbp_event_count`: same direction in all 9 months.
- `post_5_30s_mbp_events_per_second`: same direction in all 9 months.
- `pre_10s_mean_bid_size`: same direction in all 9 months.
- `post_5_30s_trade_count`: same direction in 8 of 9 months.
- `post_5_30s_trade_events_per_second`: same direction in 8 of 9 months.

Weakness:

- The best AUC values are only around 0.58 to 0.64.
- Some early months were flat or slightly opposite for the post-sweep count features.
- `sweep_0_5s_directional_size_change` ranked highly due to stability/sample scoring, but its permutation p-value was poor.

The monthly stability is good enough to justify OOS validation. It is not strong enough to claim a tradable edge yet.

## Likely Real Versus Likely Noise

Likely real enough to validate:

- Prior-day high/low sweeps leaned continuation.
- Post-sweep MBP event intensity leaned continuation.
- Post-sweep trade activity leaned continuation.
- A weak pre-sweep size/liquidity signal exists, especially `pre_10s_mean_bid_size`.

Likely noise or not yet proven:

- Spread features were not compelling.
- Many imbalance features were inconsistent month to month.
- `sweep_0_5s_directional_size_change` should not be trusted despite ranking third because the permutation test was weak.
- The exact thresholds are unknown and must not be tuned on this in-sample data.

## Strategy Prototype Decision

Answer: not yet.

There is enough evidence to justify an out-of-sample validation pass, but not enough to build a strategy prototype.

Why:

- The best signals are mostly early-confirmation signals, meaning a future setup would need to wait after the sweep.
- The effects are statistically meaningful in some places but still mild.
- The top raw features contain duplicate count/rate versions of the same idea.
- We intentionally preserved February-May 2026 for validation, and that validation has not been run yet.

The correct next step is:

```text
Freeze the carry-forward features, run them once on the reserved holdout, and check whether the same relationships survive.
```

Only if the holdout confirms the same direction and similar effect size should we move toward a simple strategy prototype.

## Implementation Map

| Area | File |
|---|---|
| CLI runner for one study window | `backend/app/cli/nq_liquidity_sweep_outcomes.py` |
| CLI combiner for shard outputs | `backend/app/cli/combine_nq_liquidity_sweep_outcomes.py` |
| Config and result types | `backend/app/research/nq_liquidity_sweep_outcomes_types.py` |
| Session levels and time windows | `backend/app/research/nq_liquidity_sweep_outcomes_sessions.py` |
| Feature definitions and timing tags | `backend/app/research/nq_liquidity_sweep_outcomes_feature_defs.py` |
| Sweep detection, labels, features | `backend/app/research/nq_liquidity_sweep_outcomes_features.py` |
| Chunked data loading and study orchestration | `backend/app/research/nq_liquidity_sweep_outcomes_chunked.py` |
| Statistical ranking | `backend/app/research/nq_liquidity_sweep_outcomes_stats.py` |
| AUC, effect size, bootstrap, permutation helpers | `backend/app/research/nq_liquidity_sweep_outcomes_stats_metrics.py` |
| Summary and examples output helpers | `backend/app/research/nq_liquidity_sweep_outcomes_stats_outputs.py` |
| Tests | `backend/tests/test_nq_liquidity_sweep_outcomes.py` |

## Reproduction Notes

The corrected in-sample study was run as monthly shards from `2025-05-01` through `2026-02-01`, then combined.

The final combine used:

```powershell
backend\.venv\Scripts\python.exe -m app.cli.combine_nq_liquidity_sweep_outcomes `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2025-05-01_2025-06-01 `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2025-06-01_2025-07-01 `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2025-07-01_2025-08-01 `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2025-08-01_2025-09-01 `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2025-09-01_2025-10-01 `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2025-10-01_2025-11-01 `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2025-11-01_2025-12-01 `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2025-12-01_2026-01-01 `
  --input-dir data\backtests\nq_liquidity_sweep_outcomes_insample_2026-01-01_2026-02-01 `
  --bootstrap-iterations 300 `
  --permutation-iterations 300 `
  --output-dir data\backtests\nq_liquidity_sweep_outcomes_insample_discovery_2025-05-01_2026-02-01
```

The reserved OOS period was not run:

```text
2026-02-01 through 2026-05-23 half-open
```
