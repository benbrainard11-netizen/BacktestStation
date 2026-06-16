# NQ Prior-Day Low Sweep Forward Validation Workflow

## Purpose

This workflow freezes the exact prior-day low sweep definitions, labels, and MBP execution sequencing used in the latest validated prior-day-low study.

It is not an optimizer. It does not change thresholds, stops, targets, context gates, variants, slippage, commission, or labels.

The goal is to collect the next 100 prior-day low sweep events after 2026-05-23 and report whether the previously observed effects remain directionally consistent on truly unseen data.

## Frozen Definitions

The workflow audits the input configs against the frozen validated run:

- Symbol: `NQ.c.0`
- Event type: `prior_day_low`
- Cutoff: session dates after `2026-05-23`
- Decision-tree labels: bar-based fixed 8-point continuation/reversal labels
- Feature window: 30 seconds after the sweep
- Outcome window: 60 minutes
- Strategy sequencing: MBP-1
- Commission: `$2.00` per contract per side assumption from the frozen run
- Slippage: 1 tick
- Context score minimum: 2 of 3 existing contexts
- Frozen variants:
  - `first_retest__sweep_extreme__fixed_12`
  - `immediate_sweep__sweep_extreme__fixed_12`
  - `immediate_sweep__sweep_extreme__fixed_8`

## Output Files

Generated local output:

`data/backtests/nq_prior_day_low_forward_validation_after_2026-05-23`

Files:

- `prior_day_low_forward_events.csv`
- `prior_day_low_forward_execution.csv`
- `prior_day_low_forward_cumulative_25.csv`
- `prior_day_low_forward_effect_consistency.csv`
- `prior_day_low_forward_definition_audit.csv`
- `prior_day_low_forward_summary.json`

## What Gets Exported Per Event

Each event row includes:

- event number from 1 to 100
- `event_id`
- session date
- sweep timestamp
- prior-day low level and sweep price
- fixed outcome label
- `post_5_30s_trade_events_per_second`
- opening-drive context
- overnight-location context
- number of frozen execution attempts attached to that event
- filled trade count
- total event PnL across frozen variants

Execution rows keep the variant-level results, including status, entry, stop, target, exit, PnL, and fill confidence.

## Current Run Result

Current input files only cover through the validated window ending 2026-05-23.

| Metric | Value |
|---|---:|
| Forward events collected | 0 |
| Events remaining to 100 | 100 |
| Execution rows | 0 |
| Definition audit passed | Yes |

Beginner read: the workflow is ready, but there is no truly unseen post-2026-05-23 prior-day-low sweep sample in the current validated files yet.

## Cumulative Reporting

When future events exist, `prior_day_low_forward_cumulative_25.csv` reports performance at:

- 25 events
- 50 events
- 75 events
- 100 events

For each checkpoint, it reports:

- all frozen variants combined
- each frozen variant separately
- unique events
- attempts
- fills
- skips
- wins
- losses
- win rate
- net PnL
- average PnL per event
- average PnL per attempt

## Directional Consistency Checks

The workflow checks whether these previously observed effects still point the same way:

- `post_5_30s_trade_events_per_second`: expected higher in winners
- `time_of_day_bucket=opening_drive`: expected higher in winners
- `opening_drive_aligned=True`: expected higher in winners
- `overnight_range_location_vs_sweep=near_sweep_side`: expected higher in winners
- `overnight_range_location=lower_third`: expected higher in winners

Current read: not evaluable yet because there are zero post-cutoff execution rows.

## How To Use It Later

After new post-2026-05-23 data has been processed through the existing prior-day sweep decision-tree and MBP strategy prototype pipeline, rerun:

```powershell
python -m app.cli.nq_prior_day_low_forward_validation `
  --events-path data/backtests/<future-decision-tree>/prior_day_sweep_decision_tree_events.csv `
  --attempts-path data/backtests/<future-mbp-top3>/prior_day_sweep_strategy_attempts.csv `
  --output-dir data/backtests/nq_prior_day_low_forward_validation_after_2026-05-23 `
  --cutoff 2026-05-23 `
  --max-events 100 `
  --strategy-config-path data/backtests/<future-mbp-top3>/prior_day_sweep_strategy_config.json `
  --decision-tree-config-path data/backtests/<future-decision-tree>/prior_day_sweep_decision_tree_config.json
```

The workflow will automatically take only the first 100 prior-day low sweep events after the cutoff.

## Interpretation Rule

Do not judge the frozen hypothesis until there are enough truly unseen events.

The first meaningful checkpoints are:

- 25 events: early warning only
- 50 events: preliminary read
- 75 events: stronger read
- 100 events: first complete forward-validation report

No rule changes should be made inside this forward-validation window.
