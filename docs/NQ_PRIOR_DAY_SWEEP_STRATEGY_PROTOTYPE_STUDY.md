# NQ Prior-Day Sweep Strategy Prototype Study

## Status

Implemented and run as a strategy prototype study.

This is still research. It is not ready for live trading.

The goal was:

```text
Take the prior-day sweep contexts that survived the decision-tree study
and test whether a simple continuation strategy has positive expectancy
after realistic trading costs.
```

## Frozen Setup

Trade only prior-day sweeps:

```text
prior_day_high sweep -> continuation long
prior_day_low sweep  -> continuation short
```

Require at least 2 of these 3 context flags:

| Context | Frozen rule |
|---|---|
| Overnight location aligned | `overnight_range_location_vs_sweep == near_sweep_side` |
| RTH gap aligned | `rth_gap_vs_sweep == with_sweep` |
| Opening drive aligned | `time_of_day_bucket == opening_drive` |

No thresholds were optimized for this prototype.

## Candidate Entries

| Entry method | Beginner meaning |
|---|---|
| `immediate_sweep` | Enter continuation as soon as possible after the sweep is detected. |
| `first_retest` | Wait for price to come back and retest the swept prior-day level. |
| `delay_30s` | Wait 30 seconds after the sweep, then enter only if price still holds beyond the level. |

## Candidate Stops

| Stop method | Beginner meaning |
|---|---|
| `fixed_8` | Fixed 8-point stop from entry. |
| `level_reversal_8` | Stop 8 points beyond the wrong side of the swept prior-day level. |
| `sweep_extreme` | Stop beyond the adverse extreme between sweep and entry, with fixed min/max guardrails. |

## Candidate Targets

| Target method | Beginner meaning |
|---|---|
| `fixed_8` | Take profit 8 points from entry. |
| `fixed_12` | Take profit 12 points from entry. |
| `r_1_5` | Take profit at 1.5 times the stop risk. |

This creates:

```text
3 entry methods x 3 stop methods x 3 target methods = 27 fixed variants
```

## Execution Assumptions

Costs:

```text
1 NQ contract
$20 per point
$2 commission per side
1 tick slippage per side
```

Full-window run:

```text
sequencing source = 1-minute bars
same-bar stop and target conflict = stop wins
```

MBP/event-sequenced support was implemented too. A smaller May 2026 MBP verification slice was run because a full MBP pass over R2 is slow.

## Output Folders

Full bar-sequenced run:

```text
data/backtests/nq_prior_day_sweep_strategy_prototype_bars_2025-05-01_2026-05-23/
```

MBP/event-sequenced May verification:

```text
data/backtests/nq_prior_day_sweep_strategy_prototype_mbp_2026-05-01_2026-05-23/
```

Exported files:

```text
prior_day_sweep_strategy_qualified_events.csv
prior_day_sweep_strategy_attempts.csv
prior_day_sweep_strategy_trades.csv
prior_day_sweep_strategy_variants.csv
prior_day_sweep_strategy_variant_summary.csv
prior_day_sweep_strategy_monthly_summary.csv
prior_day_sweep_strategy_walk_forward.csv
prior_day_sweep_strategy_summary.json
prior_day_sweep_strategy_config.json
```

## Full Bar-Sequenced Results

| Item | Value |
|---|---:|
| Qualified sweeps | 185 |
| Variants tested | 27 |
| Variant attempts | 4,995 |
| Costs included | Yes |

Top variants by average PnL per qualifying signal:

| Rank | Variant | Trades | Net PnL | Avg/signal | Win rate | Profit factor | Max DD |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `first_retest__sweep_extreme__fixed_12` | 98 | $11,153 | $60.29 | 73.5% | 2.41 | -$822 |
| 2 | `immediate_sweep__sweep_extreme__fixed_12` | 168 | $10,078 | $54.48 | 63.7% | 1.59 | -$1,876 |
| 3 | `immediate_sweep__sweep_extreme__fixed_8` | 168 | $9,258 | $50.04 | 75.0% | 1.74 | -$1,238 |
| 4 | `delay_30s__sweep_extreme__fixed_12` | 139 | $8,939 | $48.32 | 65.5% | 1.62 | -$1,912 |
| 5 | `delay_30s__sweep_extreme__fixed_8` | 139 | $8,504 | $45.97 | 77.0% | 1.82 | -$1,830 |

The best bar-sequenced variant:

```text
entry  = first retest
stop   = sweep extreme
target = fixed 12 points
```

Monthly behavior for the best bar variant:

```text
Positive months: 12 of 13
Negative month: 2025-09
Walk-forward positive test folds: 9 of 10
```

## What Separated Good From Bad

Stop choice mattered most.

| Stop family | Net PnL across all entries/targets | Read |
|---|---:|---|
| `sweep_extreme` | +$74,290 | Only broadly strong stop family in the bar run. |
| `fixed_8` | -$31,347 | Too blunt. |
| `level_reversal_8` | -$124,940 | Often carried too much risk or bad trade location. |

Within the `sweep_extreme` stop family:

| Entry family | Net PnL | Read |
|---|---:|---|
| `first_retest` | +$27,419 | Best average quality, fewer trades. |
| `immediate_sweep` | +$24,681 | More trades, more drawdown. |
| `delay_30s` | +$22,190 | Still positive, but weaker. |

Within the `sweep_extreme` stop family:

| Target family | Net PnL | Read |
|---|---:|---|
| `fixed_12` | +$30,170 | Best fixed target in bar run. |
| `fixed_8` | +$26,065 | Better win rate, lower payoff. |
| `r_1_5` | +$18,055 | Positive but weaker. |

## MBP/Event-Sequenced Verification Slice

Because the full MBP run over R2 is slow, I ran a May 2026 MBP/event-sequenced slice:

```text
2026-05-01 through 2026-05-23
10 qualified sweeps
270 variant attempts
```

Important result:

```text
The bar-leading variant did not confirm in the MBP slice.
```

Comparison:

| Variant | Bar May PnL | MBP May PnL | Read |
|---|---:|---:|---|
| `first_retest__sweep_extreme__fixed_12` | +$1,180 | -$84 | Did not confirm in MBP slice. |
| `immediate_sweep__sweep_extreme__fixed_12` | +$1,888 | -$475 | Did not confirm in MBP slice. |
| `delay_30s__sweep_extreme__fixed_12` | +$1,888 | -$452 | Did not confirm in MBP slice. |
| `immediate_sweep__level_reversal_8__fixed_12` | +$855 | +$1,350 | Small MBP slice looked better, but full bar run was poor. |

Beginner translation:

```text
The fast bar test says the idea is promising.
The MBP spot check says we should not trust the bar result yet.
```

## Current Verdict

There is evidence worth continuing:

```text
The frozen prior-day sweep context gate produced positive bar-sequenced results.
The best bar variants were stable by month and walk-forward fold.
```

But there is not enough evidence yet to say the strategy has proven positive expectancy:

```text
The MBP/event-sequenced May slice did not confirm the bar-leading variants.
```

The correct conclusion is:

```text
Build the next study around MBP/event-sequenced execution for a much narrower candidate set.
Do not optimize thresholds.
Do not trade this yet.
```

## Recommended Next Step

Freeze a smaller candidate set for full MBP validation:

```text
1. first_retest + sweep_extreme + fixed_12
2. immediate_sweep + sweep_extreme + fixed_12
3. delay_30s + sweep_extreme + fixed_12
4. immediate_sweep + level_reversal_8 + fixed_12 as a May-slice challenger
```

Then run a slower MBP/event-sequenced validation across the full window or in monthly overnight batches.

The research question becomes:

```text
Does the edge survive true event sequencing, or was the bar run too optimistic?
```
