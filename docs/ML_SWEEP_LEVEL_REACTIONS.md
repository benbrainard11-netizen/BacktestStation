# Liquidity Sweep Level Reactions

_Generated `2026-05-17T03:23:08.217927+00:00`._

This maps swept reference levels into the same `level.*` and `lr.*`
vocabulary used by opening gaps, FVGs, and order blocks.
Sweep horizons are native-candle windows because the source outcome computer is native-timeframe based.

- Source: `C:\Users\benbr\BacktestStation\data\ml\features\sweep.parquet`
- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\sweep_level_reactions.parquet`
- Rows: `52,946`
- Columns: `152`

## Counts

| Subtype | Side | Rows |
|---|---|---|
| `asia_high_1h` | `high` | 4,619 |
| `asia_low_1h` | `low` | 3,816 |
| `london_high_1h` | `high` | 4,972 |
| `london_low_1h` | `low` | 4,029 |
| `ny_high_1h` | `high` | 4,286 |
| `ny_low_1h` | `low` | 3,452 |
| `pdh_1h` | `high` | 6,416 |
| `pdh_4h` | `high` | 6,417 |
| `pdl_1h` | `low` | 5,604 |
| `pdl_4h` | `low` | 5,591 |
| `pwh_4h` | `high` | 1,112 |
| `pwh_daily` | `high` | 1,112 |
| `pwl_4h` | `low` | 760 |
| `pwl_daily` | `low` | 760 |

## Overall Reaction Rates

| Horizon | Rows | Recovered | Reject | Break | Continued | OB Confirmed | Avg Thesis / Depth |
|---|---|---|---|---|---|---|---|
| `next_3_bars` | 52,946 | 36.1% | 31.4% | 31.6% | 66.0% | 74.5% | 3.15x |
| `next_10_bars` | 52,946 | 50.4% | 46.9% | 48.6% | 80.3% | 87.2% | 6.14x |
| `next_50_bars` | 52,946 | 72.0% | 70.3% | 72.6% | 91.5% | 97.1% | 14.56x |
| `full_horizon` | 52,946 | 72.0% | 70.3% | 72.6% | 91.5% | 97.2% | 14.56x |

## Recovery Age Decay

| Subtype | Side | Age | Rows | Share | Reject | Break | OB Confirmed | Avg Thesis / Depth |
|---|---|---|---|---|---|---|---|---|
| `asia_high_1h` | `high` | `1-3d` | 463 | 10.0% | 98.1% | 43.2% | 92.4% | 2.77x |
| `asia_high_1h` | `high` | `1-4h` | 947 | 20.5% | 97.8% | 86.9% | 96.3% | 33.03x |
| `asia_high_1h` | `high` | `4h-1d` | 1,382 | 29.9% | 98.5% | 59.6% | 98.0% | 10.25x |
| `asia_high_1h` | `high` | `unreached_native_horizon` | 1,827 | 39.6% | 0.0% | 64.1% | 94.7% | 0.54x |
| `asia_low_1h` | `low` | `1-3d` | 385 | 10.1% | 91.9% | 48.6% | 91.4% | 2.15x |
| `asia_low_1h` | `low` | `1-4h` | 979 | 25.7% | 98.7% | 82.2% | 95.8% | 27.76x |
| `asia_low_1h` | `low` | `4h-1d` | 1,309 | 34.3% | 98.2% | 57.1% | 95.2% | 6.87x |
| `asia_low_1h` | `low` | `unreached_native_horizon` | 1,143 | 30.0% | 0.0% | 69.5% | 95.3% | 0.55x |
| `london_high_1h` | `high` | `1-3d` | 434 | 8.7% | 98.4% | 56.7% | 98.2% | 3.69x |
| `london_high_1h` | `high` | `1-4h` | 1,456 | 29.3% | 98.8% | 82.6% | 99.4% | 34.68x |
| `london_high_1h` | `high` | `4h-1d` | 1,353 | 27.2% | 99.0% | 60.2% | 99.0% | 8.06x |
| `london_high_1h` | `high` | `unreached_native_horizon` | 1,729 | 34.8% | 0.0% | 73.5% | 93.9% | 0.71x |
| `london_low_1h` | `low` | `1-3d` | 403 | 10.0% | 94.0% | 63.3% | 98.3% | 2.88x |
| `london_low_1h` | `low` | `1-4h` | 1,386 | 34.4% | 99.0% | 78.3% | 99.2% | 26.85x |
| `london_low_1h` | `low` | `4h-1d` | 1,180 | 29.3% | 98.7% | 60.0% | 98.4% | 6.94x |
| `london_low_1h` | `low` | `unreached_native_horizon` | 1,060 | 26.3% | 0.0% | 74.5% | 93.3% | 0.80x |
| `ny_high_1h` | `high` | `1-3d` | 306 | 7.1% | 90.8% | 64.4% | 95.8% | 4.87x |
| `ny_high_1h` | `high` | `1-4h` | 1,925 | 44.9% | 95.3% | 73.3% | 99.1% | 22.01x |
| `ny_high_1h` | `high` | `4h-1d` | 779 | 18.2% | 95.9% | 67.7% | 94.0% | 10.04x |
| `ny_high_1h` | `high` | `unreached_native_horizon` | 1,276 | 29.8% | 0.0% | 78.1% | 78.8% | 0.67x |
| `ny_low_1h` | `low` | `1-3d` | 258 | 7.5% | 88.8% | 60.9% | 96.5% | 2.61x |
| `ny_low_1h` | `low` | `1-4h` | 1,873 | 54.3% | 95.5% | 67.4% | 98.7% | 15.80x |
| `ny_low_1h` | `low` | `4h-1d` | 664 | 19.2% | 92.2% | 65.7% | 95.2% | 6.90x |
| `ny_low_1h` | `low` | `unreached_native_horizon` | 657 | 19.0% | 0.0% | 81.3% | 82.6% | 0.60x |
| `pdh_1h` | `high` | `1-3d` | 581 | 9.1% | 98.1% | 44.6% | 99.0% | 3.90x |
| `pdh_1h` | `high` | `1-4h` | 1,801 | 28.1% | 97.4% | 85.6% | 99.4% | 37.72x |
| `pdh_1h` | `high` | `4h-1d` | 1,691 | 26.4% | 98.3% | 63.9% | 99.2% | 10.58x |
| `pdh_1h` | `high` | `unreached_native_horizon` | 2,343 | 36.5% | 0.0% | 63.2% | 96.9% | 0.58x |
| `pdh_4h` | `high` | `1-3d` | 1,064 | 16.6% | 99.2% | 69.6% | 100.0% | 12.15x |
| `pdh_4h` | `high` | `3-7d` | 665 | 10.4% | 99.2% | 77.9% | 100.0% | 6.61x |
| `pdh_4h` | `high` | `4h-1d` | 2,774 | 43.2% | 98.5% | 83.2% | 100.0% | 36.30x |
| `pdh_4h` | `high` | `7-20d` | 129 | 2.0% | 98.4% | 75.2% | 100.0% | 3.27x |
| `pdh_4h` | `high` | `unreached_native_horizon` | 1,785 | 27.8% | 0.0% | 91.8% | 99.8% | 0.89x |
| `pdl_1h` | `low` | `1-3d` | 516 | 9.2% | 93.6% | 52.1% | 98.1% | 2.82x |
| `pdl_1h` | `low` | `1-4h` | 1,902 | 33.9% | 97.9% | 79.8% | 98.5% | 29.04x |
| `pdl_1h` | `low` | `4h-1d` | 1,649 | 29.4% | 97.6% | 59.8% | 98.7% | 7.49x |
| `pdl_1h` | `low` | `unreached_native_horizon` | 1,537 | 27.4% | 0.0% | 68.5% | 96.5% | 0.68x |
| `pdl_4h` | `low` | `1-3d` | 1,001 | 17.9% | 99.0% | 67.3% | 100.0% | 7.49x |
| `pdl_4h` | `low` | `3-7d` | 604 | 10.8% | 96.5% | 75.0% | 100.0% | 5.33x |
| `pdl_4h` | `low` | `4h-1d` | 3,007 | 53.8% | 98.4% | 75.7% | 99.9% | 27.04x |
| `pdl_4h` | `low` | `7-20d` | 105 | 1.9% | 88.6% | 90.5% | 100.0% | 2.13x |
| `pdl_4h` | `low` | `unreached_native_horizon` | 874 | 15.6% | 0.0% | 92.1% | 100.0% | 0.87x |
| `pwh_4h` | `high` | `1-3d` | 190 | 17.1% | 100.0% | 75.3% | 95.3% | 15.15x |
| `pwh_4h` | `high` | `3-7d` | 89 | 8.0% | 97.8% | 84.3% | 98.9% | 10.82x |
| `pwh_4h` | `high` | `4h-1d` | 561 | 50.4% | 97.5% | 87.7% | 97.5% | 46.58x |
| `pwh_4h` | `high` | `7-20d` | 17 | 1.5% | 100.0% | 94.1% | 94.1% | 5.46x |
| `pwh_4h` | `high` | `unreached_native_horizon` | 255 | 22.9% | 0.0% | 94.5% | 92.9% | 1.42x |
| `pwh_daily` | `high` | `1-3d` | 519 | 46.7% | 99.0% | 91.1% | 100.0% | 66.70x |
| `pwh_daily` | `high` | `20d+` | 86 | 7.7% | 97.7% | 97.7% | 100.0% | 13.86x |
| `pwh_daily` | `high` | `3-7d` | 140 | 12.6% | 99.3% | 91.4% | 100.0% | 32.10x |
| `pwh_daily` | `high` | `7-20d` | 169 | 15.2% | 98.8% | 92.3% | 99.4% | 18.01x |
| `pwh_daily` | `high` | `unreached_native_horizon` | 198 | 17.8% | 0.0% | 100.0% | 100.0% | 3.54x |
| `pwl_4h` | `low` | `1-3d` | 125 | 16.4% | 99.2% | 76.0% | 98.4% | 10.65x |
| `pwl_4h` | `low` | `3-7d` | 70 | 9.2% | 92.9% | 78.6% | 95.7% | 3.81x |
| `pwl_4h` | `low` | `4h-1d` | 471 | 62.0% | 97.9% | 76.6% | 94.5% | 31.22x |
| `pwl_4h` | `low` | `7-20d` | 9 | 1.2% | 88.9% | 100.0% | 88.9% | 3.11x |
| `pwl_4h` | `low` | `unreached_native_horizon` | 85 | 11.2% | 0.0% | 90.6% | 91.8% | 0.73x |
| `pwl_daily` | `low` | `1-3d` | 469 | 61.7% | 98.3% | 70.4% | 99.4% | 38.74x |
| `pwl_daily` | `low` | `20d+` | 54 | 7.1% | 90.7% | 83.3% | 100.0% | 24.70x |
| `pwl_daily` | `low` | `3-7d` | 102 | 13.4% | 98.0% | 82.4% | 100.0% | 17.80x |
| `pwl_daily` | `low` | `7-20d` | 93 | 12.2% | 97.8% | 87.1% | 100.0% | 11.74x |
| `pwl_daily` | `low` | `unreached_native_horizon` | 42 | 5.5% | 0.0% | 95.2% | 100.0% | 0.80x |

## Notes

- `level.price_low/high` are both the swept reference price; sweeps are point-level events.
- `level.size_pts` is sweep depth from reference level to manipulation extreme.
- `touched` is always true because a sweep event is created only after the level is swept.
- `meaningful_touch` means price closed back through the swept level in the rejection thesis direction.
- `directional_rejection` means recovery plus at least 1x sweep-depth thesis movement.
- `directional_break_acceptance` means continuation beyond the manipulation extreme plus at least 1x adverse movement.
- Extra columns include `lr.<horizon>.ob_confirmed`, `sweep_held_rejection`, and `sweep_extended_continuation`.
- `unreached_native_horizon` means no recovery inside the 50-native-candle source horizon.
- `lr.*` columns are labels/outcomes, not model inputs.
