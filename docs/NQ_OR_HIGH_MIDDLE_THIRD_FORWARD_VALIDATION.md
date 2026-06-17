# NQ OR-High Middle-Third Forward Validation

## Purpose

This freezes the OR-high middle-third MBP prototype exactly as validated in commit `d28781e`.

It does not optimize:

- entries
- stops
- targets
- commissions
- slippage
- thresholds
- filters

The workflow is for validation only. Future results must be kept separate from historical research.

## Frozen Prototype

Prototype id:

`nq_or_high_middle_third_mbp_d28781e`

Frozen rules:

- Symbol: `NQ.c.0`
- Opening range: 09:30-10:00 ET
- Context: opening-range close in the middle third
- Prototype event: MBP-confirmed first break of the OR high after 10:00 ET
- Continuation target: `OR high + OR range`
- Reversal target: `OR low`
- Execution stop: `OR low`
- Execution target: `OR high + OR range`
- Entry styles: immediate break, first retest, 30-second confirmation
- Slippage: 1 tick
- Commission: $2.00 per side
- Quantity: 1 NQ contract
- Forced flat: 16:00 ET

## Forward Start

Forward validation starts after:

`2026-05-23`

That means historical research samples through 2026-05-23 are not mixed into forward validation results.

## Dormant Status

Current output folder:

`data/backtests/nq_or_high_middle_third_forward_validation`

Current state:

- Status: `dormant_no_forward_or_high_events`
- Current forward OR-high events: 0
- Current labeled events: 0
- Next report: when 25 new OR-high events have accumulated
- Monitoring milestones: 25, 50, 75, and 100 new OR-high events

Beginner read: there is no future MBP data after the research window yet, so the framework is waiting. Once new opening-range events and MBP data exist, rerunning the CLI will append/recompute the future-only validation set and create milestone reports.

## Output Files

The forward validator writes:

- `or_high_forward_source_events.csv`
- `or_high_forward_mbp_events.csv`
- `or_high_forward_attempts.csv`
- `or_high_forward_trades.csv`
- `or_high_forward_outcomes.csv`
- `or_high_forward_variant_summary.csv`
- `or_high_forward_monthly.csv`
- `or_high_forward_walk_forward.csv`
- `or_high_forward_milestones.csv`
- `or_high_forward_summary.json`
- `or_high_forward_config.json`
- `reports/or_high_forward_0025.md`, then `0050`, `0075`, and so on once milestones exist

Append-only monitoring files:

- `or_high_forward_cumulative_events.csv`
- `or_high_forward_cumulative_attempts.csv`
- `or_high_forward_cumulative_trades.csv`
- `or_high_forward_cumulative_equity.csv`
- `or_high_forward_monitor_milestones.csv`
- `or_high_forward_monitor_summary.json`
- `reports/or_high_forward_monitor_0025.md`
- `reports/or_high_forward_monitor_0025_equity.csv`
- `reports/or_high_forward_monitor_0050.md`
- `reports/or_high_forward_monitor_0050_equity.csv`
- `reports/or_high_forward_monitor_0075.md`
- `reports/or_high_forward_monitor_0075_equity.csv`
- `reports/or_high_forward_monitor_0100.md`
- `reports/or_high_forward_monitor_0100_equity.csv`

Each 25-event milestone reports:

- continuation rate
- continuation-rate confidence interval
- trade count
- holdout net PnL
- average PnL per trade
- win rate
- rolling 25-event win rate
- profit factor
- cumulative equity
- max drawdown
- walk-forward fold count
- walk-forward net PnL

The monitor keeps prior cumulative rows first and appends only new `event_id` values. If the same event appears again on a later run, the existing recorded outcome is retained instead of being silently overwritten.

## How To Run

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli.nq_or_high_middle_third_forward --events-path ..\data\backtests\nq_opening_range_descriptive_2025-05-01_2026-05-23\opening_range_descriptive_events.csv --output-dir ..\data\backtests\nq_or_high_middle_third_forward_validation
```

In the future, point `--events-path` at the updated opening-range descriptive events file that includes sessions after 2026-05-23.

## Live Monitor Command

The live monitor is a one-command wrapper around the frozen workflow. It:

- rebuilds the post-2026-05-23 opening-range descriptive event file from available 1m bars
- runs the frozen OR-high middle-third MBP validator
- appends only new OR-high event ids to the cumulative monitor files
- writes a lightweight live run summary and run history

It does not change strategy rules, thresholds, entries, stops, targets, commissions, slippage, or filters.

Default output paths:

- live OR event file: `data/backtests/nq_opening_range_descriptive_forward_live/opening_range_descriptive_events.csv`
- cumulative monitor: `data/backtests/nq_or_high_middle_third_forward_validation`
- live summary: `data/backtests/nq_or_high_middle_third_forward_validation/or_high_live_monitor_summary.json`
- live run history: `data/backtests/nq_or_high_middle_third_forward_validation/or_high_live_monitor_runs.csv`

Run it manually:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli.nq_or_high_middle_third_live
```

To consume R2, the shell or scheduled job must already have:

```powershell
$env:BS_DATA_BACKEND="r2"
$env:BS_R2_BUCKET="bsdata-prod"
$env:BS_R2_ENDPOINT="<cloudflare-r2-endpoint>"
$env:BS_R2_ACCESS_KEY="<access-key>"
$env:BS_R2_SECRET="<secret>"
```

The command defaults to completed sessions only. If today is June 17 ET, it uses `end=2026-06-17`, which includes sessions through June 16 and avoids scoring a partially finished current session. To include a later finalized date, pass `--end YYYY-MM-DD`.

Beginner read: this is live validation, not live trading. The command checks for new market data, refreshes the input events, and appends unseen OR-high outcomes. If R2 has no new bars or no new MBP-1 partitions yet, the monitor remains dormant.

## Regime Analysis

A descriptive regime analysis was run on the frozen historical OR-high sample.

Output folder:

`data/backtests/nq_or_high_middle_third_regime_analysis`

Files:

- `or_high_regime_event_context.csv`
- `or_high_regime_continuation.csv`
- `or_high_regime_execution.csv`
- `or_high_regime_summary.json`

VIX source:

- Official Cboe daily VIX history CSV downloaded to `data/backtests/vix_history_cboe.csv`
- Source URL: `https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv`
- The analysis uses prior trading-day VIX close so the VIX value is pre-session context.

Important: these regime splits are not new filters. They are descriptive hypotheses only.

## VIX Regimes

VIX was split into sample quartiles using prior trading-day VIX close.

| VIX Regime | Events | Labeled | Continuations | Continuation Rate | 95% CI |
|---|---:|---:|---:|---:|---:|
| Q1 low | 9 | 6 | 5 | 83.3% | 43.6% to 97.0% |
| Q2 | 9 | 6 | 4 | 66.7% | 30.0% to 90.3% |
| Q3 | 9 | 7 | 5 | 71.4% | 35.9% to 91.8% |
| Q4 high | 9 | 5 | 5 | 100.0% | 56.6% to 100.0% |

Descriptive read:

- The effect did not disappear in high-VIX conditions.
- High-VIX Q4 looked strongest, but only 5 labeled events were available.
- This is a hypothesis, not a tradable VIX filter.

## Trend Regimes

Overnight trend:

| Overnight Trend | Events | Labeled | Continuations | Continuation Rate |
|---|---:|---:|---:|---:|
| Down | 15 | 10 | 7 | 70.0% |
| Flat | 2 | 1 | 1 | 100.0% |
| Up | 19 | 13 | 11 | 84.6% |

RTH gap:

| RTH Gap | Events | Labeled | Continuations | Continuation Rate |
|---|---:|---:|---:|---:|
| Down | 16 | 10 | 7 | 70.0% |
| Flat | 1 | 0 | 0 | unavailable |
| Up | 19 | 14 | 12 | 85.7% |

Opening drive:

| Opening Drive | Events | Labeled | Continuations | Continuation Rate |
|---|---:|---:|---:|---:|
| Down | 13 | 7 | 5 | 71.4% |
| Flat | 9 | 9 | 7 | 77.8% |
| Up | 14 | 8 | 7 | 87.5% |

Descriptive read:

- Up overnight trend, up RTH gap, and up opening drive all looked better than their down counterparts.
- That makes intuitive sense for an OR-high continuation idea.
- The sample is too small to promote these into filters.

## Volatility Quartiles

OR range quartiles:

| OR Range Quartile | Events | Labeled | Continuations | Continuation Rate |
|---|---:|---:|---:|---:|
| Q1 low | 9 | 9 | 7 | 77.8% |
| Q2 | 9 | 7 | 5 | 71.4% |
| Q3 | 9 | 5 | 4 | 80.0% |
| Q4 high | 9 | 3 | 3 | 100.0% |

Overnight range quartiles:

| Overnight Range Quartile | Events | Labeled | Continuations | Continuation Rate |
|---|---:|---:|---:|---:|
| Q1 low | 9 | 5 | 4 | 80.0% |
| Q2 | 9 | 9 | 6 | 66.7% |
| Q3 | 9 | 4 | 3 | 75.0% |
| Q4 high | 9 | 6 | 6 | 100.0% |

Descriptive read:

- The continuation label was positive across all OR range quartiles.
- Wider overnight range Q4 looked strongest.
- Overnight range Q3 had weak immediate-break execution PnL despite a positive continuation rate, so path quality may matter.

## Regime Conclusion

The regime analysis does not invalidate the frozen OR-high middle-third prototype.

The most interesting descriptive hypotheses:

- OR-high continuation may be stronger when prior VIX is in the highest sample quartile.
- OR-high continuation may be stronger when overnight trend, RTH gap, or opening drive points up.
- Very wide overnight ranges may be favorable, but this needs more data.

The main warning:

- Every split is small. Most labeled subgroups have fewer than 15 observations.
- These findings must not be used as filters yet.

Best next step:

- Keep the forward validator dormant and let it collect truly unseen OR-high events.
- Review the first 25-event forward report before making any prototype changes.
