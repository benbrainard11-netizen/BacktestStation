# NQ Prior-Day Sweep Direction Split Analysis

## Purpose

This study splits the existing prior-day sweep framework by direction:

- Prior-day high sweeps: continuation attempt is long.
- Prior-day low sweeps: continuation attempt is short.

The goal is to determine whether prior-day low sweeps behave differently enough to justify a direction-specific strategy research path.

Important caveat: the existing fixed market continuation labels in the decision-tree file use the prior study's `label_source=bars`. The strategy validation results are MBP/event-level sequenced. For strategy conclusions, the MBP-sequenced target/stop/PnL results are the primary evidence.

## Output Files

Generated local output:

`data/backtests/nq_prior_day_sweep_direction_split_mbp_top3_2025-05-01_2026-05-23`

Key files:

- `prior_day_sweep_direction_event_continuation.csv`
- `prior_day_sweep_direction_strategy.csv`
- `prior_day_sweep_direction_variants.csv`
- `prior_day_sweep_direction_overnight_location.csv`
- `prior_day_sweep_direction_post_sweep_activity.csv`
- `prior_day_sweep_direction_time_of_day.csv`
- `prior_day_sweep_direction_comparison.csv`

## 1. Market Continuation Rates

The raw fixed 8-point continuation labels did not show a strong low-sweep advantage.

| Scope | Direction | Sweeps | Continuations | Reversals | Continuation Rate |
|---|---|---:|---:|---:|---:|
| Full | Prior-day high | 145 | 102 | 43 | 70.3% |
| Full | Prior-day low | 99 | 70 | 29 | 70.7% |
| Holdout | Prior-day high | 40 | 29 | 11 | 72.5% |
| Holdout | Prior-day low | 28 | 19 | 9 | 67.9% |

Beginner read: by simple fixed continuation labeling, high sweeps and low sweeps were almost identical in the full sample. In holdout, high sweeps actually had the better raw continuation rate.

So the prior-day low advantage is not coming from "lows continue more often" in the simple market-label study.

## 2. MBP/Event-Level Strategy Results

The MBP-sequenced strategy attempts told a very different story.

| Scope | Direction | Attempts | Fills | Target Rate | Stop Rate | Net PnL | Avg PnL / Attempt |
|---|---|---:|---:|---:|---:|---:|---:|
| Full | Prior-day high / long | 351 | 303 | 40.6% | 57.4% | -$3,737 | -$10.65 |
| Full | Prior-day low / short | 204 | 179 | 50.3% | 44.7% | +$5,084 | +$24.92 |
| Holdout | Prior-day high / long | 90 | 80 | 35.0% | 61.3% | -$2,315 | -$25.72 |
| Holdout | Prior-day low / short | 72 | 64 | 42.2% | 48.4% | +$329 | +$4.57 |

Low-minus-high comparison:

| Scope | Low - High Target Rate | Low - High Avg PnL / Attempt | Low - High Net PnL |
|---|---:|---:|---:|
| Full | +9.7 percentage points | +$35.57 | +$8,821 |
| Holdout | +7.2 percentage points | +$30.29 | +$2,644 |

This is the central result. The low-sweep/short side held up better under MBP event sequencing, including holdout, even though the raw continuation label did not favor lows.

## 3. Variant-Level Direction Split

| Scope | Direction | Variant | Net PnL | Target Rate | Read |
|---|---|---|---:|---:|---|
| Full | High | First retest 12pt | -$2,871 | 24.6% | Failed |
| Full | High | Immediate 12pt | -$868 | 39.3% | Failed |
| Full | High | Immediate 8pt | +$2 | 51.3% | Basically flat |
| Full | Low | First retest 12pt | +$1,888 | 46.5% | Positive |
| Full | Low | Immediate 12pt | +$1,903 | 47.1% | Positive |
| Full | Low | Immediate 8pt | +$1,293 | 55.9% | Positive |
| Holdout | High | All three | negative | 20.0%-43.3% | Failed |
| Holdout | Low | First retest 12pt | +$226 | 37.5% | Slightly positive |
| Holdout | Low | Immediate 12pt | +$289 | 41.7% | Slightly positive |
| Holdout | Low | Immediate 8pt | -$186 | 45.8% | Lost despite higher target rate |

Beginner read: highs were bad almost everywhere. Lows were not amazing, but they were consistently less broken.

## 4. Overnight Location Effects

### Prior-Day High Sweeps

| Scope | Overnight Location vs Sweep | Trades | Win Rate | Net PnL | Stability |
|---|---|---:|---:|---:|---:|
| Full | Near sweep side | 200 | 46.5% | +$2,080 | 11 / 13 months |
| Full | Middle | 94 | 29.8% | -$5,066 | 3 / 13 months |
| Full | Away from sweep side | 9 | 22.2% | -$751 | 0 / 2 months |
| Holdout | Near sweep side | 48 | 43.8% | +$338 | 3 / 4 months |
| Holdout | Middle | 29 | 24.1% | -$2,146 | 1 / 4 months |

For high sweeps, overnight location mattered a lot. Near-side positioning was the only context that looked workable.

### Prior-Day Low Sweeps

| Scope | Overnight Location vs Sweep | Trades | Win Rate | Net PnL | Stability |
|---|---|---:|---:|---:|---:|
| Full | Near sweep side | 120 | 50.8% | +$3,990 | 7 / 13 months |
| Full | Middle | 42 | 52.4% | +$1,332 | 4 / 10 months |
| Full | Away from sweep side | 17 | 41.2% | -$238 | 2 / 6 months |
| Holdout | Near sweep side | 47 | 44.7% | +$852 | 2 / 4 months |
| Holdout | Middle | 12 | 33.3% | -$448 | 1 / 2 months |

For low sweeps, near-side positioning was still helpful, but lows were less dependent on it than highs in the full sample.

## 5. Post-Sweep Trade Activity

The most important MBP feature remains real trade activity after the sweep.

### `post_5_30s_trade_events_per_second`

| Scope | Direction | Winner Median | Loser Median | AUC | Cliff's Delta |
|---|---|---:|---:|---:|---:|
| Full | High | 30.12 | 25.16 | 0.662 | 0.324 |
| Full | Low | 34.88 | 30.44 | 0.546 | 0.093 |
| Holdout | High | 27.64 | 26.68 | 0.579 | 0.158 |
| Holdout | Low | 33.32 | 29.68 | 0.581 | 0.162 |

Both directions liked more real trade follow-through after the sweep. The separation was stronger for highs in the full sample, but lows held a similar holdout AUC.

Important nuance: raw MBP quote/event churn did not behave the same way. For lows, `post_5_30s_mbp_events_per_second` was higher in losers in the full sample. That supports the earlier idea: actual trades matter more than quote update noise.

## 6. Time-Of-Day Effects

Most attempts were opening-drive sweeps, so time-of-day is not a broad sample.

| Scope | Direction | Time Bucket | Trades | Win Rate | Net PnL |
|---|---|---|---:|---:|---:|
| Full | High | Opening drive | 291 | 41.2% | -$3,659 |
| Full | Low | Opening drive | 164 | 52.4% | +$4,834 |
| Holdout | High | Opening drive | 77 | 36.4% | -$2,193 |
| Holdout | Low | Opening drive | 58 | 46.6% | +$453 |

Sparse later buckets were mostly bad:

- High afternoon: 0 wins / 6 losses full, 0 wins / 3 losses holdout.
- Low midday: 0 wins / 9 losses full, 0 wins / 6 losses holdout.

Hypothesis: later sweeps may be dangerous, but sample sizes are too small to use this as a rule.

## 7. Holdout Validation Read

The holdout did not make lows look spectacular, but it did preserve the structural split:

- High/long attempts stayed clearly negative.
- Low/short attempts stayed slightly positive.
- Low target rate stayed better than high target rate by 7.2 percentage points.
- Low average PnL per attempt stayed about $30 better than high average PnL per attempt.

That is meaningful because holdout was generally weak for the strategy family.

## Conclusion

Yes, prior-day low sweeps appear structurally different enough to justify direction-specific strategy research.

But the reason is specific:

- It is not because raw fixed continuation labels show lows continuing more often.
- It is because the MBP/event-level execution outcomes are much healthier on the low/short side than the high/long side.

Practical conclusion:

- Do not pool prior-day highs and lows into one strategy score.
- Treat prior-day highs/longs as a separate, currently failed prototype.
- Treat prior-day lows/shorts as the only direction that currently justifies a focused prototype refinement.

This does not mean the low-sweep strategy is ready to trade. The holdout profit was small, and the sample is still modest. The next research step should freeze a direction-specific low-sweep candidate and validate it without changing thresholds inside the same test.

