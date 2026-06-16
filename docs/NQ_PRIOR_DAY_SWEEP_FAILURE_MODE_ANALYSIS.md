# NQ Prior-Day Sweep Failure-Mode Analysis

## Purpose

This analysis uses the full MBP validation results for the frozen top-3 prior-day sweep strategy variants. The goal is diagnosis, not optimization.

Every observation below is a hypothesis for future validation, not a new trading rule.

## Data Used

- Strategy attempt source: `data/backtests/nq_prior_day_sweep_strategy_prototype_mbp_top3_combined_2025-05-01_2026-05-23/prior_day_sweep_strategy_attempts.csv`
- Event/context source: `data/backtests/nq_prior_day_sweep_decision_tree_full_2025-05-01_2026-05-23/prior_day_sweep_decision_tree_events.csv`
- Failure-mode output: `data/backtests/nq_prior_day_sweep_failure_modes_mbp_top3_2025-05-01_2026-05-23`
- Full window: 2025-05-01 through 2026-05-23
- Holdout window: 2026-02-01 through 2026-05-23

Important row definition: this is attempt-level analysis, not unique-event analysis. The same market sweep can appear more than once because three frozen variants were tested on the same sweep.

## Baseline

| Scope | Attempts | Filled Win/Loss Trades | Wins | Losses | Win Rate |
|---|---:|---:|---:|---:|---:|
| Full sample | 555 | 482 | 213 | 269 | 44.2% |
| Holdout | 162 attempts / 144 trades | 144 | 55 | 89 | 38.2% |

The holdout period was genuinely weaker, so patterns that survive there are more interesting than patterns that only show in the full sample.

## Strongest Structural Hint

The cleanest separator was post-sweep trade activity, especially `post_5_30s_trade_events_per_second`.

| Scope | Winner Median | Loser Median | AUC | Cliff's Delta | Month Consistency |
|---|---:|---:|---:|---:|---:|
| Full | 31.08 trades/sec | 26.72 trades/sec | 0.623 | 0.246 | 12 / 13 months |
| Holdout | 28.32 trades/sec | 27.56 trades/sec | 0.584 | 0.167 | 4 / 4 months |

Beginner read: after the sweep, winning trades tended to have more actual trade prints in the next 5-30 seconds. That looks like real follow-through. This was the most stable finding.

Important nuance: raw MBP event intensity did not show the same clean behavior. In holdout, `post_5_30s_mbp_events_per_second` was higher in losers, while actual trade events were higher in winners. That suggests quote churn alone may not be bullish/bearish enough. Real trades after the sweep looked more useful than quote update volume.

## Context Findings

### Overnight Range Location

The strongest context pattern was where RTH opened inside the overnight range relative to the sweep side.

| Category | Full Win Rate | Full PnL | Full Monthly Direction | Holdout Win Rate | Holdout PnL | Holdout Monthly Direction |
|---|---:|---:|---:|---:|---:|---:|
| Near sweep side | 48.1% | +$6,070 | 11 / 13 | 44.2% | +$1,190 | 4 / 4 |
| Middle | 36.8% | -$3,734 | 4 / 13 | 26.8% | -$2,594 | 1 / 4 |
| Away from sweep side | 34.6% | -$989 | 2 / 6 | 25.0% | -$582 | 1 / 2 |

Hypothesis: continuation attempts worked better when the market was already positioned near the side being swept. Middle/away locations were more failure-prone.

### Prior-Day High vs Prior-Day Low

| Level Type | Full Win Rate | Full PnL | Full Monthly Direction | Holdout Win Rate | Holdout PnL |
|---|---:|---:|---:|---:|---:|
| Prior-day high / long | 40.6% | -$3,737 | 4 / 13 | 35.0% | -$2,315 |
| Prior-day low / short | 50.3% | +$5,084 | 9 / 13 | 42.2% | +$329 |

Hypothesis: in this sample, short continuation after prior-day low sweeps was healthier than long continuation after prior-day high sweeps. Holdout still favored lows/shorts, but only mildly and with weak month stability.

### RTH Gap Direction

This factor was mostly unavailable as a separator because the strategy context gate already forced almost everything into `with_sweep`.

- Full: 479 of 482 filled trades were `with_sweep`.
- Holdout: 144 of 144 filled trades were `with_sweep`.

Conclusion: RTH gap direction cannot explain winners versus losers in this validation run because there was almost no variation left after filtering.

### Opening Drive / Time Of Day

Most trades happened during the opening-drive bucket:

- Full opening-drive trades: 455 of 482
- Holdout opening-drive trades: 135 of 144

Opening drive was slightly better than the full baseline, but not a strong separator. Non-opening trades were sparse and poor in holdout:

- Holdout midday: 0 wins / 6 losses
- Holdout afternoon: 0 wins / 3 losses

Hypothesis: later sweeps were failure-prone in holdout, but sample size is too small to trust as a rule.

## MBP Feature Findings

### Sweep Distance Beyond Level

| Scope | Winner Median | Loser Median | AUC | Read |
|---|---:|---:|---:|---|
| Full | 10.25 pts | 11.75 pts | 0.507 | No real separation |
| Holdout | 34.25 pts | 4.75 pts | 0.565 | Larger sweeps helped in holdout only |

The full sample says sweep distance was basically noise. The holdout says bigger sweeps worked better, but that direction did not hold over the full year. Treat this as a holdout-specific hypothesis, not evidence.

### Time-To-Reclaim

`reclaimed_0_30s` means price traded back to the swept level within 30 seconds.

| Category | Full Win Rate | Full PnL | Holdout Win Rate | Holdout PnL | Holdout Monthly Direction |
|---|---:|---:|---:|---:|---:|
| No reclaim within 30s | 45.1% | -$13 | 44.0% | -$190 | 4 / 4 |
| Reclaimed within 30s | 43.1% | +$1,360 | 31.9% | -$1,796 | 0 / 4 |

In the holdout, reclaiming the swept level quickly was associated with losing trades. The full sample was mixed, so this is a good diagnostic hypothesis but not yet a rule.

Among only trades that did reclaim, the exact reclaim speed was not reliable:

- Full: winners reclaimed faster, AUC 0.432 because lower time favored winners.
- Holdout: winner and loser medians were identical at 0.00838 seconds.

### Pre-Sweep Aggressive Trade Ratio

| Scope | Winner Median | Loser Median | AUC | Month Consistency |
|---|---:|---:|---:|---:|
| Full | 0.0294 | 0.0114 | 0.548 | 11 / 13 |
| Holdout | -0.0012 | 0.0150 | 0.422 | 2 / 4 |

This looked encouraging in the full sample but reversed in holdout. The categorical band view also became messy:

- Full `mild_with_sweep`: 51.7% win rate, +$5,148
- Holdout `mild_with_sweep`: 34.4% win rate, -$318
- Holdout `mild_against_sweep`: 51.7% win rate, +$734

Conclusion: pre-sweep aggressive ratio did not survive as a stable separator.

### Post-Sweep Event Intensity

The useful version was trade activity, not total MBP event churn.

- `post_5_30s_trade_events_per_second`: strongest and most stable numeric separator.
- `sweep_0_5s_trade_events_per_second`: mild positive separator, but less stable.
- `post_5_30s_mbp_events_per_second`: weak and opposite in holdout.
- `sweep_0_5s_mbp_events_per_second`: higher in losers in holdout.

Hypothesis: continuation needs real executed trade follow-through after the sweep. High quote/event churn without trade follow-through may be a warning sign.

## Variant-Specific Failure Modes

| Variant | Full Win Rate | Full PnL | Holdout Win Rate | Holdout PnL | Read |
|---|---:|---:|---:|---:|---|
| `immediate_sweep__sweep_extreme__fixed_8` | 53.0% | +$1,295 | 44.4% | -$906 | Best win rate, still failed holdout PnL |
| `immediate_sweep__sweep_extreme__fixed_12` | 42.2% | +$1,035 | 38.9% | -$201 | More resilient PnL in holdout, still negative |
| `first_retest__sweep_extreme__fixed_12` | 33.0% | -$983 | 27.8% | -$879 | Structural loser |

The first-retest variant remains the clearest failure mode. It skipped 73 attempts and performed poorly when it did fill.

## Practical Hypotheses To Carry Forward

1. Post-sweep trade follow-through matters.
   The most stable distinction was more trade prints 5-30 seconds after the sweep in winners.

2. Overnight location near the sweep side may be important.
   Near-side overnight location held up in full sample and holdout.

3. Middle/away overnight positioning is a warning sign.
   These contexts had lower win rates and worse PnL, especially in holdout.

4. Quick reclaim may be dangerous for continuation, especially recently.
   In holdout, reclaim within 30 seconds was clearly worse.

5. Prior-day high/long attempts were weaker than prior-day low/short attempts.
   This was visible in full sample and holdout, but should be retested at event level before becoming a filter.

6. Pre-sweep aggressive ratio is not robust yet.
   It looked useful in the full sample but reversed in holdout.

7. Sweep distance is not proven.
   The full sample showed no separation; the holdout showed a large-sweep advantage that may be regime-specific.

## What Not To Do Yet

Do not turn these directly into optimized thresholds. The right next step is a validation design that freezes simple diagnostic hypotheses before testing them:

- Compare high post-sweep trade activity versus low post-sweep trade activity using pre-declared buckets.
- Test near-sweep-side overnight location as a context filter.
- Test whether reclaim-within-30s should invalidate continuation attempts.
- Keep prior-day high and prior-day low separated in reporting.
- Retest on future unseen data before promoting anything into a strategy rule.

