# All Level Reactions

_Generated `2026-05-17T16:36:17.533029+00:00`._

This is the combined level database. It stacks the existing per-concept
universal level-reaction tables into one parquet so dashboards and notebooks
can compare level families directly.

- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\all_level_reactions.parquet`
- Rows: `2,123,226`
- Columns: `461`

## Sources

| Source | Artifact | Horizon Style | Note |
|---|---|---|---|
| `opening_gap` | `opening_gap_level_reactions.parquet` | `clock_time` | NDOG/NWOG clock-time forward windows. |
| `fair_value_gap` | `fvg_level_reactions.parquet` | `native_bars` | FVG native-candle mitigation windows. |
| `order_block` | `ob_level_reactions.parquet` | `native_bars` | Order-block native-candle retest windows. |
| `liquidity_sweep` | `sweep_level_reactions.parquet` | `native_bars` | Sweep native-candle recovery/continuation windows. |
| `swing_pivot` | `swing_level_reactions.parquet` | `native_bars` | Swing-pivot native-candle hold/break windows. |
| `equal_levels` | `equal_level_reactions.parquet` | `native_bars_1h` | Equal-high/low 1h take/reaction windows. |

## Counts

| Kind | Side | Rows |
|---|---|---|
| `equal_levels` | `high` | 31,735 |
| `equal_levels` | `low` | 29,450 |
| `fair_value_gap` | `bearish` | 613,224 |
| `fair_value_gap` | `bullish` | 630,533 |
| `liquidity_sweep` | `high` | 120,981 |
| `liquidity_sweep` | `low` | 116,588 |
| `opening_gap` | `gap_down` | 18,074 |
| `opening_gap` | `gap_up` | 18,870 |
| `order_block` | `bearish` | 100,646 |
| `order_block` | `bullish` | 97,423 |
| `swing_pivot` | `high` | 174,574 |
| `swing_pivot` | `low` | 171,128 |

## Horizon Availability

| Kind | Horizon | Rows | Available |
|---|---|---|---|
| `equal_levels` | `next_5_bars` | 61,185 | 100.0% |
| `equal_levels` | `next_25_bars` | 61,185 | 100.0% |
| `equal_levels` | `next_100_bars` | 61,185 | 100.0% |
| `equal_levels` | `next_250_bars` | 61,185 | 100.0% |
| `equal_levels` | `full_horizon` | 61,185 | 100.0% |
| `fair_value_gap` | `next_3_bars` | 1,243,757 | 100.0% |
| `fair_value_gap` | `next_10_bars` | 1,243,757 | 100.0% |
| `fair_value_gap` | `next_50_bars` | 1,243,757 | 100.0% |
| `fair_value_gap` | `full_horizon` | 1,243,757 | 100.0% |
| `liquidity_sweep` | `next_3_bars` | 237,569 | 100.0% |
| `liquidity_sweep` | `next_10_bars` | 237,569 | 100.0% |
| `liquidity_sweep` | `next_50_bars` | 237,569 | 100.0% |
| `liquidity_sweep` | `full_horizon` | 237,569 | 100.0% |
| `opening_gap` | `next_60m` | 36,944 | 100.0% |
| `opening_gap` | `next_240m` | 36,944 | 100.0% |
| `opening_gap` | `next_1d` | 36,944 | 100.0% |
| `opening_gap` | `next_5d` | 36,944 | 100.0% |
| `opening_gap` | `next_20d` | 36,944 | 100.0% |
| `opening_gap` | `full_horizon` | 36,944 | 100.0% |
| `order_block` | `next_3_bars` | 198,069 | 100.0% |
| `order_block` | `next_10_bars` | 198,069 | 100.0% |
| `order_block` | `next_50_bars` | 198,069 | 100.0% |
| `order_block` | `full_horizon` | 198,069 | 100.0% |
| `swing_pivot` | `next_3_bars` | 345,702 | 100.0% |
| `swing_pivot` | `next_10_bars` | 345,702 | 100.0% |
| `swing_pivot` | `next_50_bars` | 345,702 | 100.0% |
| `swing_pivot` | `full_horizon` | 345,702 | 100.0% |

## Full-Horizon Comparison

| Kind | Rows | Meaningful | Reject | Break | Clean Through | Avg Thesis / Size |
|---|---|---|---|---|---|---|
| `equal_levels` | 61,185 | 82.1% | 3.5% | 73.5% | 73.5% | 20.06x |
| `fair_value_gap` | 1,243,757 | 90.2% | 33.5% | 74.0% | 74.0% | 21.68x |
| `liquidity_sweep` | 237,569 | 77.4% | 75.5% | 76.4% | 58.4% | 14.95x |
| `opening_gap` | 36,944 | 98.2% | 64.1% | 10.4% | 95.7% | - |
| `order_block` | 198,069 | 93.8% | 14.0% | 80.7% | 80.7% | 16.64x |
| `swing_pivot` | 345,702 | 71.0% | 6.4% | 64.5% | 64.5% | 13.98x |

## Short-Horizon Comparison

| Kind | Horizon | Rows | Meaningful | Reject | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|
| `equal_levels` | `next_5_bars` | 61,185 | 7.6% | 2.0% | 3.5% | 3.24x |
| `fair_value_gap` | `next_3_bars` | 1,243,757 | 66.9% | 24.0% | 28.3% | 4.15x |
| `liquidity_sweep` | `next_3_bars` | 237,569 | 44.6% | 39.2% | 38.8% | 3.31x |
| `opening_gap` | `next_60m` | 36,944 | 70.6% | 59.1% | 10.3% | - |
| `order_block` | `next_3_bars` | 198,069 | 78.7% | 24.7% | 39.5% | 3.39x |
| `swing_pivot` | `next_3_bars` | 345,702 | 21.2% | 5.0% | 14.1% | 5.41x |

## Interpretation Notes

- Opening gaps use clock-time horizons; FVG, OB, sweep, and swing use native-bar horizons.
- Equal levels use 1h native-bar take/reaction horizons.
- `full_horizon` is comparable as a broad outcome bucket, but each concept's source horizon differs.
- Sweep `touched` is always true by definition because a sweep event only exists after the level was swept.
- `level.source_*` columns preserve where each row came from.
- Concept-specific extras are preserved; missing columns are null for concepts that do not define them.
- `lr.*` columns are labels/outcomes, not model inputs.
