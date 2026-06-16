# NQ Prior-Day Sweep Strategy Prototype: MBP Top-3 Validation

## Bottom Line

This run validated the top 3 bar-based variants with MBP-1/event-level sequencing across the full available MBP window:

- Data window: 2025-05-01 through 2026-05-23
- Qualified prior-day sweep events: 185
- Variant attempts: 555
- Sequencing source: MBP-1 event stream
- Frozen variants only: no thresholds, stops, targets, context gates, or timing parameters were optimized

Result: two immediate-entry variants stayed technically profitable over the full sample, but the edge became very small after realistic execution assumptions. The first-retest variant failed outright. The recent holdout period was negative for all three variants, so none of these should be treated as a validated strategy yet.

Beginner translation: the bar test made these variants look strong, but the more realistic event-level test removed most of the edge. There may still be something worth researching, especially around immediate sweep continuation, but this is not yet strong enough to trust as a standalone strategy.

## Frozen Variants Tested

These were the top 3 variants from the existing bar-based strategy prototype run:

| Variant | Entry | Stop | Target |
|---|---|---|---|
| `first_retest__sweep_extreme__fixed_12` | Wait for first retest of prior-day level | Sweep extreme stop | 12-point target |
| `immediate_sweep__sweep_extreme__fixed_12` | Enter immediately after sweep | Sweep extreme stop | 12-point target |
| `immediate_sweep__sweep_extreme__fixed_8` | Enter immediately after sweep | Sweep extreme stop | 8-point target |

The context gate stayed frozen:

- Prior-day high or prior-day low sweep only
- Requires at least 2 of 3 context flags:
  - overnight location aligned
  - RTH gap aligned
  - opening-drive timing

## Realistic Execution Assumptions

The MBP version simulates fills from event sequencing instead of 1-minute bar highs/lows.

- Long immediate entry: first valid quote after the sweep, filled at ask plus 1 tick slippage
- Short immediate entry: first valid quote after the sweep, filled at bid minus 1 tick slippage
- Retest entry: first MBP trade back to the prior-day level inside the retest window, filled at level plus/minus slippage
- Stop: sweep extreme from actual trade prints between sweep and entry, plus 0.50 point buffer
- Minimum sweep-extreme stop: 6 points
- Maximum sweep-extreme stop: 30 points
- Target: unchanged fixed 8 or 12 points
- Exit: walks MBP trade events after entry and exits when the stop or target is actually touched
- Forced flat: noon ET or 60 minutes after sweep, whichever comes first
- Costs: 1 NQ contract, $20 per point, $2 commission per side, 1 tick slippage per side

This is stricter than the bar version because it uses the order of MBP events instead of assuming a favorable path inside each candle.

## Output Files

Combined validation output:

`data/backtests/nq_prior_day_sweep_strategy_prototype_mbp_top3_combined_2025-05-01_2026-05-23`

Important files in that folder:

- `prior_day_sweep_strategy_summary.json`
- `prior_day_sweep_strategy_variant_summary.csv`
- `prior_day_sweep_strategy_monthly_summary.csv`
- `prior_day_sweep_strategy_walk_forward.csv`
- `prior_day_sweep_strategy_attempts.csv`
- `prior_day_sweep_strategy_trades.csv`
- `prior_day_sweep_strategy_qualified_events.csv`

## Full MBP Validation Results

| Variant | Signals | Trades | Skips | Net PnL | Avg PnL / Signal | Win Rate | Profit Factor | Max Drawdown | Validation Read |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `immediate_sweep__sweep_extreme__fixed_8` | 185 | 185 | 0 | $1,295 | $7.00 | 52.97% | 1.09 | -$1,638 | Technically profitable, but thin |
| `immediate_sweep__sweep_extreme__fixed_12` | 185 | 185 | 0 | $1,035 | $5.59 | 42.16% | 1.06 | -$1,390 | Technically profitable, but thin |
| `first_retest__sweep_extreme__fixed_12` | 185 | 112 | 73 | -$983 | -$5.31 | 33.04% | 0.90 | -$1,882 | Failed validation |

The best variant, `immediate_sweep__sweep_extreme__fixed_8`, averaged only $7 per signal after modeled costs. That is less than the modeled round-trip cost cushion. One extra tick of slippage on each side would likely erase it.

## Bar Test vs MBP Validation

| Variant | Bar Net PnL | MBP Net PnL | Change | Read |
|---|---:|---:|---:|---|
| `first_retest__sweep_extreme__fixed_12` | $11,153 | -$983 | -$12,136 | Bar edge did not survive |
| `immediate_sweep__sweep_extreme__fixed_12` | $10,078 | $1,035 | -$9,043 | Mostly disappeared |
| `immediate_sweep__sweep_extreme__fixed_8` | $9,258 | $1,295 | -$7,963 | Survived only weakly |

This is the key validation result. The bar-based version was probably too generous about entries, retests, stop/target ordering, or the path inside candles.

## Stability Checks

| Variant | Positive Months | Walk-Forward Positive Test Folds | 2026-02 to 2026-05 Holdout PnL | Best Month | Worst Month |
|---|---:|---:|---:|---:|---:|
| `immediate_sweep__sweep_extreme__fixed_8` | 8 / 13 | 6 / 10 | -$906 | $1,235 | -$1,248 |
| `immediate_sweep__sweep_extreme__fixed_12` | 8 / 13 | 5 / 10 | -$201 | $1,145 | -$982 |
| `first_retest__sweep_extreme__fixed_12` | 7 / 13 | 5 / 10 | -$879 | $664 | -$1,410 |

The full-period positives are heavily helped by a few strong months, especially December 2025. The recent untouched holdout window was negative for all three variants, which weakens the evidence.

## Variant Read

### `immediate_sweep__sweep_extreme__fixed_8`

This is the best practical survivor, but only as a research candidate. It had the highest MBP net PnL and best walk-forward positive fold count, but the average profit per signal was very small and April/May 2026 were poor.

### `immediate_sweep__sweep_extreme__fixed_12`

This also stayed positive over the full window, but the lower win rate and weak profit factor make it fragile. It performed less badly than fixed-8 during the 2026-02 to 2026-05 holdout, but it still did not prove robust.

### `first_retest__sweep_extreme__fixed_12`

This failed validation. The bar version likely overestimated retest fills or favorable sequencing. In the MBP version it skipped many events and lost money on the fills it did get.

## Conclusion

No variant is strong enough to call validated.

Two immediate-entry variants remain nominally profitable over the full available MBP dataset, but the edge is too thin and not stable enough. The recent holdout period is negative, the profit factors are close to 1.0, and the bar-to-MBP drop is large.

The core prior-day sweep continuation idea is not dead, but the current simple prototype is not ready for strategy promotion. The next responsible step is diagnostic replay and error analysis, not parameter optimization.

Recommended next research questions:

- Which April and May 2026 trades caused the breakdown?
- Are losses concentrated by time of day, prior-day high vs low, or long vs short?
- Are poor trades preceded by spread widening, quote instability, or weak aggressive trade follow-through?
- Does the immediate-entry idea need a confirmation filter that is known before entry, without changing target/stop thresholds yet?

