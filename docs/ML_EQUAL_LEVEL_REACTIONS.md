# Equal Levels Level Reactions

_Generated `2026-05-17T04:01:56.505460+00:00`._

This maps equal-high/equal-low liquidity levels into the same `level.*`
and `lr.*` vocabulary used by the other level families.

- Source: `C:\Users\benbr\BacktestStation\data\ml\features\eql.parquet`
- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\equal_level_reactions.parquet`
- Rows: `60,338`
- Columns: `171`

## Counts

| Subtype | Side | Rows |
|---|---|---|
| `eq_pivot_3_1h_15pts` | `high` | 10,851 |
| `eq_pivot_3_1h_15pts` | `low` | 10,226 |
| `eq_pivot_3_1h_5pts` | `high` | 6,835 |
| `eq_pivot_3_1h_5pts` | `low` | 6,140 |
| `eq_pivot_3_4h_15pts` | `high` | 2,524 |
| `eq_pivot_3_4h_15pts` | `low` | 2,157 |
| `eq_pivot_5_1h_15pts` | `high` | 6,113 |
| `eq_pivot_5_1h_15pts` | `low` | 5,737 |
| `eq_pivot_5_1h_5pts` | `high` | 3,610 |
| `eq_pivot_5_1h_5pts` | `low` | 3,266 |
| `eq_pivot_5_4h_15pts` | `high` | 1,342 |
| `eq_pivot_5_4h_15pts` | `low` | 1,162 |
| `eq_pivot_5_daily_30pts` | `high` | 196 |
| `eq_pivot_5_daily_30pts` | `low` | 179 |

## Overall Reaction Rates

| Horizon | Rows | Wick Took Level | Close Past Level | Rejected | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|
| `next_5_bars` | 60,338 | 8.1% | 4.8% | 2.3% | 3.8% | 3.58x |
| `next_25_bars` | 60,338 | 48.5% | 40.2% | 7.6% | 34.5% | 7.46x |
| `next_100_bars` | 60,338 | 73.0% | 67.3% | 5.5% | 61.6% | 14.76x |
| `next_250_bars` | 60,338 | 79.6% | 75.3% | 4.3% | 69.2% | 18.36x |
| `full_horizon` | 60,338 | 79.6% | 75.3% | 4.3% | 69.2% | 18.36x |

## First-Touch Age Decay

| Subtype | Side | Age | Rows | Share | Reject | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|---|
| `eq_pivot_3_1h_15pts` | `high` | `1-3d` | 2,263 | 20.9% | 3.7% | 83.8% | 9.88x |
| `eq_pivot_3_1h_15pts` | `high` | `3-7d` | 1,019 | 9.4% | 5.7% | 75.0% | 6.19x |
| `eq_pivot_3_1h_15pts` | `high` | `4h-1d` | 6,074 | 56.0% | 2.9% | 90.1% | 14.50x |
| `eq_pivot_3_1h_15pts` | `high` | `7-20d` | 93 | 0.9% | 4.3% | 48.4% | 2.62x |
| `eq_pivot_3_1h_15pts` | `high` | `unreached_native_horizon` | 1,402 | 12.9% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_1h_15pts` | `low` | `1-3d` | 1,887 | 18.5% | 9.2% | 80.0% | 11.08x |
| `eq_pivot_3_1h_15pts` | `low` | `3-7d` | 918 | 9.0% | 9.9% | 75.2% | 6.41x |
| `eq_pivot_3_1h_15pts` | `low` | `4h-1d` | 4,935 | 48.3% | 6.2% | 86.8% | 16.22x |
| `eq_pivot_3_1h_15pts` | `low` | `7-20d` | 81 | 0.8% | 21.0% | 58.0% | 4.45x |
| `eq_pivot_3_1h_15pts` | `low` | `unreached_native_horizon` | 2,405 | 23.5% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_1h_5pts` | `high` | `1-3d` | 1,279 | 18.7% | 4.1% | 92.3% | 25.70x |
| `eq_pivot_3_1h_5pts` | `high` | `3-7d` | 522 | 7.6% | 5.2% | 88.1% | 17.32x |
| `eq_pivot_3_1h_5pts` | `high` | `4h-1d` | 4,263 | 62.4% | 2.7% | 95.3% | 33.13x |
| `eq_pivot_3_1h_5pts` | `high` | `7-20d` | 39 | 0.6% | 2.6% | 89.7% | 6.30x |
| `eq_pivot_3_1h_5pts` | `high` | `unreached_native_horizon` | 732 | 10.7% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_1h_5pts` | `low` | `1-3d` | 1,056 | 17.2% | 9.4% | 88.3% | 26.39x |
| `eq_pivot_3_1h_5pts` | `low` | `3-7d` | 511 | 8.3% | 10.4% | 86.9% | 16.89x |
| `eq_pivot_3_1h_5pts` | `low` | `4h-1d` | 3,356 | 54.7% | 6.2% | 92.0% | 35.55x |
| `eq_pivot_3_1h_5pts` | `low` | `7-20d` | 37 | 0.6% | 24.3% | 67.6% | 17.17x |
| `eq_pivot_3_1h_5pts` | `low` | `unreached_native_horizon` | 1,180 | 19.2% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_4h_15pts` | `high` | `1-3d` | 948 | 37.6% | 4.1% | 84.5% | 9.47x |
| `eq_pivot_3_4h_15pts` | `high` | `3-7d` | 449 | 17.8% | 5.6% | 73.9% | 5.35x |
| `eq_pivot_3_4h_15pts` | `high` | `4h-1d` | 493 | 19.5% | 3.0% | 88.2% | 13.41x |
| `eq_pivot_3_4h_15pts` | `high` | `7-20d` | 42 | 1.7% | 4.8% | 47.6% | 2.31x |
| `eq_pivot_3_4h_15pts` | `high` | `unreached_native_horizon` | 592 | 23.5% | 0.0% | 0.0% | nanx |
| `eq_pivot_3_4h_15pts` | `low` | `1-3d` | 660 | 30.6% | 7.0% | 84.5% | 11.93x |
| `eq_pivot_3_4h_15pts` | `low` | `3-7d` | 322 | 14.9% | 10.6% | 71.1% | 6.41x |
| `eq_pivot_3_4h_15pts` | `low` | `4h-1d` | 327 | 15.2% | 6.7% | 87.5% | 12.93x |
| `eq_pivot_3_4h_15pts` | `low` | `7-20d` | 20 | 0.9% | 10.0% | 65.0% | 1.42x |
| `eq_pivot_3_4h_15pts` | `low` | `unreached_native_horizon` | 828 | 38.4% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_1h_15pts` | `high` | `1-3d` | 1,555 | 25.4% | 3.7% | 83.9% | 9.47x |
| `eq_pivot_5_1h_15pts` | `high` | `3-7d` | 699 | 11.4% | 4.6% | 77.4% | 5.96x |
| `eq_pivot_5_1h_15pts` | `high` | `4h-1d` | 2,804 | 45.9% | 2.9% | 89.6% | 14.41x |
| `eq_pivot_5_1h_15pts` | `high` | `7-20d` | 60 | 1.0% | 3.3% | 53.3% | 2.36x |
| `eq_pivot_5_1h_15pts` | `high` | `unreached_native_horizon` | 995 | 16.3% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_1h_15pts` | `low` | `1-3d` | 1,251 | 21.8% | 9.3% | 79.6% | 10.68x |
| `eq_pivot_5_1h_15pts` | `low` | `3-7d` | 639 | 11.1% | 8.5% | 73.9% | 6.65x |
| `eq_pivot_5_1h_15pts` | `low` | `4h-1d` | 2,170 | 37.8% | 7.3% | 85.1% | 16.08x |
| `eq_pivot_5_1h_15pts` | `low` | `7-20d` | 47 | 0.8% | 19.1% | 55.3% | 3.20x |
| `eq_pivot_5_1h_15pts` | `low` | `unreached_native_horizon` | 1,630 | 28.4% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_1h_5pts` | `high` | `1-3d` | 880 | 24.4% | 3.4% | 91.9% | 24.45x |
| `eq_pivot_5_1h_5pts` | `high` | `3-7d` | 363 | 10.1% | 5.2% | 87.3% | 17.30x |
| `eq_pivot_5_1h_5pts` | `high` | `4h-1d` | 1,835 | 50.8% | 2.8% | 94.6% | 32.81x |
| `eq_pivot_5_1h_5pts` | `high` | `7-20d` | 27 | 0.7% | 0.0% | 88.9% | 5.45x |
| `eq_pivot_5_1h_5pts` | `high` | `unreached_native_horizon` | 505 | 14.0% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_1h_5pts` | `low` | `1-3d` | 695 | 21.3% | 9.4% | 88.1% | 24.23x |
| `eq_pivot_5_1h_5pts` | `low` | `3-7d` | 358 | 11.0% | 11.2% | 86.0% | 17.92x |
| `eq_pivot_5_1h_5pts` | `low` | `4h-1d` | 1,399 | 42.8% | 7.4% | 90.7% | 33.88x |
| `eq_pivot_5_1h_5pts` | `low` | `7-20d` | 19 | 0.6% | 21.1% | 68.4% | 13.85x |
| `eq_pivot_5_1h_5pts` | `low` | `unreached_native_horizon` | 795 | 24.3% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_4h_15pts` | `high` | `1-3d` | 580 | 43.2% | 4.3% | 84.8% | 9.08x |
| `eq_pivot_5_4h_15pts` | `high` | `3-7d` | 279 | 20.8% | 5.7% | 71.7% | 5.38x |
| `eq_pivot_5_4h_15pts` | `high` | `4h-1d` | 55 | 4.1% | 7.3% | 80.0% | 13.59x |
| `eq_pivot_5_4h_15pts` | `high` | `7-20d` | 33 | 2.5% | 9.1% | 48.5% | 1.92x |
| `eq_pivot_5_4h_15pts` | `high` | `unreached_native_horizon` | 395 | 29.4% | 0.0% | 0.0% | nanx |
| `eq_pivot_5_4h_15pts` | `low` | `1-3d` | 403 | 34.7% | 6.2% | 86.4% | 12.65x |
| `eq_pivot_5_4h_15pts` | `low` | `3-7d` | 199 | 17.1% | 9.5% | 74.9% | 6.54x |
| `eq_pivot_5_4h_15pts` | `low` | `4h-1d` | 26 | 2.2% | 7.7% | 88.5% | 13.77x |
| `eq_pivot_5_4h_15pts` | `low` | `7-20d` | 8 | 0.7% | 0.0% | 62.5% | 0.47x |
| `eq_pivot_5_4h_15pts` | `low` | `unreached_native_horizon` | 526 | 45.3% | 0.0% | 0.0% | nanx |

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
