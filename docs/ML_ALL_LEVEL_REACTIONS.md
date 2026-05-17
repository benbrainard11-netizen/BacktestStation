# All Level Reactions

_Generated `2026-05-17T04:04:03.484186+00:00`._

This is the combined level database. It stacks the existing per-concept
universal level-reaction tables into one parquet so dashboards and notebooks
can compare level families directly.

- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\all_level_reactions.parquet`
- Rows: `455,178`
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
| `equal_levels` | `high` | 31,471 |
| `equal_levels` | `low` | 28,867 |
| `fair_value_gap` | `bearish` | 96,037 |
| `fair_value_gap` | `bullish` | 113,302 |
| `liquidity_sweep` | `high` | 28,934 |
| `liquidity_sweep` | `low` | 24,012 |
| `opening_gap` | `gap_down` | 4,873 |
| `opening_gap` | `gap_up` | 4,565 |
| `order_block` | `bearish` | 24,966 |
| `order_block` | `bullish` | 21,365 |
| `swing_pivot` | `high` | 38,657 |
| `swing_pivot` | `low` | 38,129 |

## Horizon Availability

| Kind | Horizon | Rows | Available |
|---|---|---|---|
| `equal_levels` | `next_5_bars` | 60,338 | 100.0% |
| `equal_levels` | `next_25_bars` | 60,338 | 100.0% |
| `equal_levels` | `next_100_bars` | 60,338 | 100.0% |
| `equal_levels` | `next_250_bars` | 60,338 | 100.0% |
| `equal_levels` | `full_horizon` | 60,338 | 100.0% |
| `fair_value_gap` | `next_3_bars` | 209,339 | 100.0% |
| `fair_value_gap` | `next_10_bars` | 209,339 | 100.0% |
| `fair_value_gap` | `next_50_bars` | 209,339 | 100.0% |
| `fair_value_gap` | `full_horizon` | 209,339 | 100.0% |
| `liquidity_sweep` | `next_3_bars` | 52,946 | 100.0% |
| `liquidity_sweep` | `next_10_bars` | 52,946 | 100.0% |
| `liquidity_sweep` | `next_50_bars` | 52,946 | 100.0% |
| `liquidity_sweep` | `full_horizon` | 52,946 | 100.0% |
| `opening_gap` | `next_60m` | 9,438 | 100.0% |
| `opening_gap` | `next_240m` | 9,438 | 100.0% |
| `opening_gap` | `next_1d` | 9,438 | 100.0% |
| `opening_gap` | `next_5d` | 9,438 | 100.0% |
| `opening_gap` | `next_20d` | 9,438 | 100.0% |
| `opening_gap` | `full_horizon` | 9,438 | 100.0% |
| `order_block` | `next_3_bars` | 46,331 | 100.0% |
| `order_block` | `next_10_bars` | 46,331 | 100.0% |
| `order_block` | `next_50_bars` | 46,331 | 100.0% |
| `order_block` | `full_horizon` | 46,331 | 100.0% |
| `swing_pivot` | `next_3_bars` | 76,786 | 100.0% |
| `swing_pivot` | `next_10_bars` | 76,786 | 100.0% |
| `swing_pivot` | `next_50_bars` | 76,786 | 100.0% |
| `swing_pivot` | `full_horizon` | 76,786 | 100.0% |

## Full-Horizon Comparison

| Kind | Rows | Meaningful | Reject | Break | Clean Through | Avg Thesis / Size |
|---|---|---|---|---|---|---|
| `equal_levels` | 60,338 | 79.6% | 4.3% | 69.2% | 69.2% | 18.36x |
| `fair_value_gap` | 209,339 | 89.3% | 45.2% | 73.5% | 73.5% | 31.77x |
| `liquidity_sweep` | 52,946 | 72.0% | 70.3% | 72.6% | 51.6% | 14.56x |
| `opening_gap` | 9,438 | 98.7% | 66.1% | 15.4% | 96.5% | 164.96x |
| `order_block` | 46,331 | 94.5% | 14.4% | 80.5% | 80.5% | 22.92x |
| `swing_pivot` | 76,786 | 69.8% | 7.3% | 62.2% | 62.2% | 12.93x |

## Short-Horizon Comparison

| Kind | Horizon | Rows | Meaningful | Reject | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|
| `equal_levels` | `next_5_bars` | 60,338 | 8.1% | 2.3% | 3.8% | 3.58x |
| `fair_value_gap` | `next_3_bars` | 209,339 | 63.3% | 31.7% | 25.9% | 6.37x |
| `liquidity_sweep` | `next_3_bars` | 52,946 | 36.1% | 31.4% | 31.6% | 3.15x |
| `opening_gap` | `next_60m` | 9,438 | 79.3% | 66.1% | 15.4% | 5.15x |
| `order_block` | `next_3_bars` | 46,331 | 80.9% | 27.5% | 40.2% | 5.00x |
| `swing_pivot` | `next_3_bars` | 76,786 | 23.8% | 6.1% | 15.1% | 5.09x |

## Interpretation Notes

- Opening gaps use clock-time horizons; FVG, OB, sweep, and swing use native-bar horizons.
- Equal levels use 1h native-bar take/reaction horizons.
- `full_horizon` is comparable as a broad outcome bucket, but each concept's source horizon differs.
- Sweep `touched` is always true by definition because a sweep event only exists after the level was swept.
- `level.source_*` columns preserve where each row came from.
- Concept-specific extras are preserved; missing columns are null for concepts that do not define them.
- `lr.*` columns are labels/outcomes, not model inputs.
