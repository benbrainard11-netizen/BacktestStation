# Equal Levels Level Reactions

_Generated `2026-05-17T15:59:50.322481+00:00`._

This maps equal-high/equal-low liquidity levels into the same `level.*`
and `lr.*` vocabulary used by the other level families.

- Source: `C:\Users\benbr\BacktestStation\data\ml\features\eql.parquet`
- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\equal_level_reactions.parquet`
- Rows: `61,185`
- Columns: `171`

## Counts

| Subtype | Side | Rows |
|---|---|---|
| `eq_pivot_3_1h_15pts` | `high` | 10,821 |
| `eq_pivot_3_1h_15pts` | `low` | 10,230 |
| `eq_pivot_3_1h_5pts` | `high` | 6,944 |
| `eq_pivot_3_1h_5pts` | `low` | 6,324 |
| `eq_pivot_3_4h_15pts` | `high` | 2,584 |
| `eq_pivot_3_4h_15pts` | `low` | 2,178 |
| `eq_pivot_5_1h_15pts` | `high` | 6,126 |
| `eq_pivot_5_1h_15pts` | `low` | 5,873 |
| `eq_pivot_5_1h_5pts` | `high` | 3,684 |
| `eq_pivot_5_1h_5pts` | `low` | 3,431 |
| `eq_pivot_5_4h_15pts` | `high` | 1,372 |
| `eq_pivot_5_4h_15pts` | `low` | 1,217 |
| `eq_pivot_5_daily_30pts` | `high` | 204 |
| `eq_pivot_5_daily_30pts` | `low` | 197 |

## Overall Reaction Rates

| Horizon | Rows | Wick Took Level | Close Past Level | Rejected | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|
| `next_5_bars` | 61,185 | 7.6% | 4.6% | 2.0% | 3.5% | 3.24x |
| `next_25_bars` | 61,185 | 48.4% | 40.0% | 7.5% | 33.8% | 6.72x |
| `next_100_bars` | 61,185 | 72.3% | 67.0% | 5.3% | 61.4% | 13.49x |
| `next_250_bars` | 61,185 | 82.1% | 78.5% | 3.5% | 73.5% | 20.06x |
| `full_horizon` | 61,185 | 82.1% | 78.5% | 3.5% | 73.5% | 20.06x |

## First-Touch Age Decay

| Subtype | Side | Age | Rows | Share | Reject | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|---|
| `eq_pivot_3_1h_15pts` | `high` | `1-3d` | 2,217 | 20.5% | 3.3% | 88.2% | 11.14x |
| `eq_pivot_3_1h_15pts` | `high` | `3-7d` | 1,064 | 9.8% | 2.7% | 87.2% | 8.56x |
| `eq_pivot_3_1h_15pts` | `high` | `4h-1d` | 5,883 | 54.4% | 2.8% | 91.5% | 16.35x |
| `eq_pivot_3_1h_15pts` | `high` | `7-20d` | 360 | 3.3% | 8.6% | 63.9% | 4.28x |
| `eq_pivot_3_1h_15pts` | `high` | `unreached_native_horizon` | 1,297 | 12.0% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_1h_15pts` | `low` | `1-3d` | 1,906 | 18.6% | 5.9% | 84.1% | 12.31x |
| `eq_pivot_3_1h_15pts` | `low` | `3-7d` | 946 | 9.2% | 6.3% | 82.9% | 9.22x |
| `eq_pivot_3_1h_15pts` | `low` | `4h-1d` | 4,969 | 48.6% | 4.8% | 88.0% | 17.67x |
| `eq_pivot_3_1h_15pts` | `low` | `7-20d` | 377 | 3.7% | 10.9% | 66.0% | 4.60x |
| `eq_pivot_3_1h_15pts` | `low` | `unreached_native_horizon` | 2,032 | 19.9% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_1h_5pts` | `high` | `1-3d` | 1,216 | 17.5% | 2.4% | 95.7% | 30.72x |
| `eq_pivot_3_1h_5pts` | `high` | `3-7d` | 554 | 8.0% | 1.8% | 96.9% | 21.66x |
| `eq_pivot_3_1h_5pts` | `high` | `4h-1d` | 4,321 | 62.2% | 2.8% | 95.8% | 34.94x |
| `eq_pivot_3_1h_5pts` | `high` | `7-20d` | 167 | 2.4% | 12.0% | 82.6% | 9.29x |
| `eq_pivot_3_1h_5pts` | `high` | `unreached_native_horizon` | 686 | 9.9% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_1h_5pts` | `low` | `1-3d` | 1,061 | 16.8% | 5.7% | 92.2% | 30.12x |
| `eq_pivot_3_1h_5pts` | `low` | `3-7d` | 515 | 8.1% | 4.3% | 94.6% | 25.48x |
| `eq_pivot_3_1h_5pts` | `low` | `4h-1d` | 3,558 | 56.3% | 5.5% | 93.2% | 38.02x |
| `eq_pivot_3_1h_5pts` | `low` | `7-20d` | 191 | 3.0% | 14.1% | 81.2% | 12.98x |
| `eq_pivot_3_1h_5pts` | `low` | `unreached_native_horizon` | 999 | 15.8% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_4h_15pts` | `high` | `1-3d` | 946 | 36.6% | 3.2% | 89.2% | 10.92x |
| `eq_pivot_3_4h_15pts` | `high` | `3-7d` | 443 | 17.1% | 4.1% | 85.1% | 6.28x |
| `eq_pivot_3_4h_15pts` | `high` | `4h-1d` | 504 | 19.5% | 3.0% | 91.3% | 14.60x |
| `eq_pivot_3_4h_15pts` | `high` | `7-20d` | 144 | 5.6% | 6.2% | 63.9% | 3.71x |
| `eq_pivot_3_4h_15pts` | `high` | `unreached_native_horizon` | 547 | 21.2% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_4h_15pts` | `low` | `1-3d` | 676 | 31.0% | 5.0% | 84.9% | 12.95x |
| `eq_pivot_3_4h_15pts` | `low` | `3-7d` | 319 | 14.6% | 8.5% | 81.8% | 9.71x |
| `eq_pivot_3_4h_15pts` | `low` | `4h-1d` | 348 | 16.0% | 5.7% | 87.6% | 13.09x |
| `eq_pivot_3_4h_15pts` | `low` | `7-20d` | 123 | 5.6% | 9.8% | 69.1% | 4.53x |
| `eq_pivot_3_4h_15pts` | `low` | `unreached_native_horizon` | 712 | 32.7% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_1h_15pts` | `high` | `1-3d` | 1,501 | 24.5% | 2.9% | 89.7% | 10.91x |
| `eq_pivot_5_1h_15pts` | `high` | `3-7d` | 696 | 11.4% | 3.2% | 87.9% | 7.68x |
| `eq_pivot_5_1h_15pts` | `high` | `4h-1d` | 2,730 | 44.6% | 2.6% | 91.6% | 16.23x |
| `eq_pivot_5_1h_15pts` | `high` | `7-20d` | 239 | 3.9% | 7.1% | 64.4% | 3.68x |
| `eq_pivot_5_1h_15pts` | `high` | `unreached_native_horizon` | 960 | 15.7% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_1h_15pts` | `low` | `1-3d` | 1,295 | 22.1% | 5.3% | 84.9% | 11.85x |
| `eq_pivot_5_1h_15pts` | `low` | `3-7d` | 676 | 11.5% | 5.9% | 83.7% | 9.30x |
| `eq_pivot_5_1h_15pts` | `low` | `4h-1d` | 2,245 | 38.2% | 5.7% | 87.1% | 17.26x |
| `eq_pivot_5_1h_15pts` | `low` | `7-20d` | 272 | 4.6% | 9.2% | 68.4% | 4.80x |
| `eq_pivot_5_1h_15pts` | `low` | `unreached_native_horizon` | 1,385 | 23.6% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_1h_5pts` | `high` | `1-3d` | 826 | 22.4% | 2.3% | 95.8% | 29.05x |
| `eq_pivot_5_1h_5pts` | `high` | `3-7d` | 360 | 9.8% | 1.7% | 96.7% | 20.55x |
| `eq_pivot_5_1h_5pts` | `high` | `4h-1d` | 1,881 | 51.1% | 2.7% | 95.6% | 36.15x |
| `eq_pivot_5_1h_5pts` | `high` | `7-20d` | 121 | 3.3% | 11.6% | 83.5% | 8.13x |
| `eq_pivot_5_1h_5pts` | `high` | `unreached_native_horizon` | 496 | 13.5% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_1h_5pts` | `low` | `1-3d` | 728 | 21.2% | 4.4% | 93.4% | 28.08x |
| `eq_pivot_5_1h_5pts` | `low` | `3-7d` | 355 | 10.3% | 4.8% | 94.4% | 25.46x |
| `eq_pivot_5_1h_5pts` | `low` | `4h-1d` | 1,505 | 43.9% | 6.4% | 92.6% | 35.50x |
| `eq_pivot_5_1h_5pts` | `low` | `7-20d` | 143 | 4.2% | 14.0% | 83.9% | 13.52x |
| `eq_pivot_5_1h_5pts` | `low` | `unreached_native_horizon` | 700 | 20.4% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_4h_15pts` | `high` | `1-3d` | 583 | 42.5% | 3.6% | 89.0% | 10.48x |
| `eq_pivot_5_4h_15pts` | `high` | `3-7d` | 274 | 20.0% | 4.4% | 84.3% | 6.82x |
| `eq_pivot_5_4h_15pts` | `high` | `4h-1d` | 59 | 4.3% | 5.1% | 86.4% | 13.31x |
| `eq_pivot_5_4h_15pts` | `high` | `7-20d` | 103 | 7.5% | 3.9% | 68.0% | 3.52x |
| `eq_pivot_5_4h_15pts` | `high` | `unreached_native_horizon` | 353 | 25.7% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_4h_15pts` | `low` | `1-3d` | 430 | 35.3% | 5.3% | 87.0% | 13.25x |
| `eq_pivot_5_4h_15pts` | `low` | `3-7d` | 202 | 16.6% | 8.9% | 83.2% | 10.15x |
| `eq_pivot_5_4h_15pts` | `low` | `4h-1d` | 42 | 3.5% | 7.1% | 85.7% | 11.65x |
| `eq_pivot_5_4h_15pts` | `low` | `7-20d` | 71 | 5.8% | 14.1% | 67.6% | 4.03x |
| `eq_pivot_5_4h_15pts` | `low` | `unreached_native_horizon` | 472 | 38.8% | 0.0% | 0.0% | nanx |

## Notes

- `level.created_ts_utc` adds the parent swing confirmation lag to the second pivot timestamp.
- Equal-level reaction horizons are 1h native bars: 5, 25, 100, and 250 bars.
- `level.price_low/high` preserves the cluster band when available; `level.take_price` is the exact liquidity price.
- `meaningful_touch` means a future wick took the equal high/low.
- `full_touch` and `closed_through` mean a future close accepted past the level.
- `directional_rejection` means first take reversed, did not close past, and moved at least one level-size in thesis direction after take.
- `directional_break_acceptance` means price closed past and extended through by at least one level-size.
- `unreached_native_horizon` means no take inside the 250-hour source horizon.
- `lr.*` columns are labels/outcomes, not model inputs.
