# Swing Pivot Level Reactions

_Generated `2026-05-17T04:01:55.907492+00:00`._

This maps swing-pivot point levels into the same `level.*` and `lr.*`
vocabulary used by opening gaps, FVGs, order blocks, and sweeps.

- Source: `C:\Users\benbr\BacktestStation\data\ml\features\swing.parquet`
- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\swing_level_reactions.parquet`
- Rows: `76,786`
- Columns: `134`

## Counts

| Subtype | Side | Rows |
|---|---|---|
| `pivot_3_1h` | `high` | 18,063 |
| `pivot_3_1h` | `low` | 17,857 |
| `pivot_3_4h` | `high` | 5,468 |
| `pivot_3_4h` | `low` | 5,223 |
| `pivot_5_1h` | `high` | 11,205 |
| `pivot_5_1h` | `low` | 11,219 |
| `pivot_5_4h` | `high` | 3,336 |
| `pivot_5_4h` | `low` | 3,249 |
| `pivot_5_daily` | `high` | 585 |
| `pivot_5_daily` | `low` | 581 |

## Overall Reaction Rates

| Horizon | Rows | Wick Took Pivot | Close Broke Pivot | Rejected | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|
| `next_3_bars` | 76,786 | 23.8% | 15.1% | 6.1% | 15.1% | 5.09x |
| `next_10_bars` | 76,786 | 44.8% | 34.9% | 8.4% | 34.9% | 7.44x |
| `next_50_bars` | 76,786 | 69.8% | 62.2% | 7.3% | 62.2% | 12.93x |
| `full_horizon` | 76,786 | 69.8% | 62.2% | 7.3% | 62.2% | 12.93x |

## First-Touch Age Decay

| Subtype | Side | Age | Rows | Share | Reject | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|---|
| `pivot_3_1h` | `high` | `1-3d` | 1,327 | 7.3% | 16.0% | 83.7% | 14.01x |
| `pivot_3_1h` | `high` | `1-4h` | 5,114 | 28.3% | 7.1% | 92.3% | 12.17x |
| `pivot_3_1h` | `high` | `4h-1d` | 7,086 | 39.2% | 8.7% | 91.0% | 12.40x |
| `pivot_3_1h` | `high` | `unreached_native_horizon` | 4,536 | 25.1% | 0.0% | 0.0% | 20.61x |
| `pivot_3_1h` | `low` | `1-3d` | 1,230 | 6.9% | 19.4% | 80.1% | 9.82x |
| `pivot_3_1h` | `low` | `1-4h` | 4,571 | 25.6% | 11.5% | 88.1% | 10.27x |
| `pivot_3_1h` | `low` | `4h-1d` | 6,312 | 35.3% | 12.3% | 87.2% | 9.35x |
| `pivot_3_1h` | `low` | `unreached_native_horizon` | 5,744 | 32.2% | 0.0% | 0.0% | 13.09x |
| `pivot_3_4h` | `high` | `1-3d` | 1,340 | 24.5% | 5.5% | 94.5% | 11.45x |
| `pivot_3_4h` | `high` | `3-7d` | 733 | 13.4% | 6.0% | 93.6% | 14.08x |
| `pivot_3_4h` | `high` | `4h-1d` | 2,287 | 41.8% | 5.9% | 94.1% | 11.65x |
| `pivot_3_4h` | `high` | `7-20d` | 132 | 2.4% | 26.5% | 72.7% | 20.25x |
| `pivot_3_4h` | `high` | `unreached_native_horizon` | 976 | 17.8% | 0.0% | 0.0% | 30.54x |
| `pivot_3_4h` | `low` | `1-3d` | 1,065 | 20.4% | 12.2% | 87.8% | 8.19x |
| `pivot_3_4h` | `low` | `3-7d` | 648 | 12.4% | 17.7% | 81.5% | 8.50x |
| `pivot_3_4h` | `low` | `4h-1d` | 1,814 | 34.7% | 11.0% | 88.8% | 9.29x |
| `pivot_3_4h` | `low` | `7-20d` | 105 | 2.0% | 37.1% | 62.9% | 10.96x |
| `pivot_3_4h` | `low` | `unreached_native_horizon` | 1,591 | 30.5% | 0.0% | 0.0% | 15.11x |
| `pivot_5_1h` | `high` | `1-3d` | 974 | 8.7% | 15.5% | 84.2% | 14.22x |
| `pivot_5_1h` | `high` | `1-4h` | 2,249 | 20.1% | 8.4% | 90.9% | 13.23x |
| `pivot_5_1h` | `high` | `4h-1d` | 4,433 | 39.6% | 8.5% | 91.1% | 11.20x |
| `pivot_5_1h` | `high` | `unreached_native_horizon` | 3,549 | 31.7% | 0.0% | 0.0% | 21.01x |
| `pivot_5_1h` | `low` | `1-3d` | 886 | 7.9% | 18.3% | 81.2% | 9.38x |
| `pivot_5_1h` | `low` | `1-4h` | 1,986 | 17.7% | 12.7% | 86.8% | 9.69x |
| `pivot_5_1h` | `low` | `4h-1d` | 3,850 | 34.3% | 12.3% | 87.2% | 8.41x |
| `pivot_5_1h` | `low` | `unreached_native_horizon` | 4,497 | 40.1% | 0.0% | 0.0% | 12.72x |
| `pivot_5_4h` | `high` | `1-3d` | 915 | 27.4% | 5.1% | 94.9% | 11.34x |
| `pivot_5_4h` | `high` | `3-7d` | 549 | 16.5% | 6.0% | 93.4% | 14.42x |
| `pivot_5_4h` | `high` | `4h-1d` | 1,021 | 30.6% | 5.6% | 94.4% | 11.64x |
| `pivot_5_4h` | `high` | `7-20d` | 111 | 3.3% | 22.5% | 77.5% | 20.37x |
| `pivot_5_4h` | `high` | `unreached_native_horizon` | 740 | 22.2% | 0.0% | 0.0% | 32.46x |
| `pivot_5_4h` | `low` | `1-3d` | 722 | 22.2% | 12.7% | 87.3% | 8.35x |
| `pivot_5_4h` | `low` | `3-7d` | 459 | 14.1% | 17.2% | 82.1% | 8.34x |
| `pivot_5_4h` | `low` | `4h-1d` | 762 | 23.5% | 9.3% | 90.6% | 8.34x |
| `pivot_5_4h` | `low` | `7-20d` | 92 | 2.8% | 33.7% | 66.3% | 11.71x |
| `pivot_5_4h` | `low` | `unreached_native_horizon` | 1,214 | 37.4% | 0.0% | 0.0% | 15.09x |
| `pivot_5_daily` | `high` | `1-3d` | 65 | 11.1% | 1.5% | 98.5% | 8.93x |
| `pivot_5_daily` | `high` | `20d+` | 84 | 14.4% | 7.1% | 92.9% | 22.14x |
| `pivot_5_daily` | `high` | `3-7d` | 153 | 26.2% | 3.3% | 96.7% | 24.94x |
| `pivot_5_daily` | `high` | `7-20d` | 175 | 29.9% | 3.4% | 96.6% | 13.49x |
| `pivot_5_daily` | `high` | `unreached_native_horizon` | 108 | 18.5% | 0.0% | 0.0% | 27.40x |
| `pivot_5_daily` | `low` | `1-3d` | 35 | 6.0% | 2.9% | 97.1% | 4.39x |
| `pivot_5_daily` | `low` | `20d+` | 87 | 15.0% | 13.8% | 86.2% | 19.17x |
| `pivot_5_daily` | `low` | `3-7d` | 84 | 14.5% | 17.9% | 82.1% | 8.97x |
| `pivot_5_daily` | `low` | `7-20d` | 104 | 17.9% | 14.4% | 85.6% | 14.78x |
| `pivot_5_daily` | `low` | `unreached_native_horizon` | 271 | 46.6% | 0.0% | 0.0% | 12.51x |

## Notes

- `level.created_ts_utc` is the first knowable timestamp after right-side pivot confirmation.
- `level.price_low/high/mid` are all the pivot price because swing pivots are point levels.
- `level.size_pts` is a scale value from pivot price to pivot close, with a 1-point fallback.
- `meaningful_touch` means a future wick traded beyond the pivot.
- `full_touch` and `closed_through` mean a future close accepted beyond the pivot.
- `directional_rejection` means the pivot was wicked, not closed through, and price moved at least one scale unit in the thesis direction.
- `unreached_native_horizon` means no pivot take inside the 50-native-candle source horizon.
- `lr.*` columns are labels/outcomes, not model inputs.
