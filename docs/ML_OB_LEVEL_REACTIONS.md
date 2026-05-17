# Order Block Level Reactions

_Generated `2026-05-17T02:56:41.570763+00:00`._

This maps order-block body zones into the same `level.*` and `lr.*`
vocabulary used by opening gaps and FVGs. OB horizons are native-candle
windows because the source outcome computer is native-timeframe based.

- Source: `C:\Users\benbr\BacktestStation\data\ml\features\ob.parquet`
- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\ob_level_reactions.parquet`
- Rows: `46,331`
- Columns: `143`

## Counts

| Subtype | Side | Rows |
|---|---|---|
| `swept_asia_high_1h` | `bearish` | 4,017 |
| `swept_asia_low_1h` | `bullish` | 3,332 |
| `swept_london_high_1h` | `bearish` | 4,512 |
| `swept_london_low_1h` | `bullish` | 3,739 |
| `swept_ny_high_1h` | `bearish` | 3,626 |
| `swept_ny_low_1h` | `bullish` | 3,108 |
| `swept_pdh_1h` | `bearish` | 5,541 |
| `swept_pdh_4h` | `bearish` | 5,497 |
| `swept_pdl_1h` | `bullish` | 4,908 |
| `swept_pdl_4h` | `bullish` | 5,008 |
| `swept_pwh_4h` | `bearish` | 917 |
| `swept_pwh_daily` | `bearish` | 856 |
| `swept_pwl_4h` | `bullish` | 647 |
| `swept_pwl_daily` | `bullish` | 623 |

## Overall Reaction Rates

| Horizon | Rows | Meaningful Test | Mid Test | Full Body Test | Reject | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|---|
| `next_3_bars` | 46,331 | 80.9% | 76.9% | 61.9% | 27.5% | 40.2% | 5.00x |
| `next_10_bars` | 46,331 | 88.9% | 86.6% | 77.5% | 24.4% | 61.9% | 9.91x |
| `next_50_bars` | 46,331 | 94.5% | 93.3% | 89.0% | 14.4% | 80.5% | 22.92x |
| `full_horizon` | 46,331 | 94.5% | 93.3% | 89.0% | 14.4% | 80.5% | 22.92x |

## First-Meaningful-Test Age Decay

| Subtype | Side | Age | Rows | Share | Reject | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|---|
| `swept_asia_high_1h` | `bearish` | `1-3d` | 36 | 0.9% | 30.6% | 69.4% | 55.62x |
| `swept_asia_high_1h` | `bearish` | `1-4h` | 3,247 | 80.8% | 9.5% | 90.5% | 20.66x |
| `swept_asia_high_1h` | `bearish` | `4h-1d` | 599 | 14.9% | 11.7% | 88.1% | 41.33x |
| `swept_asia_high_1h` | `bearish` | `unreached_native_horizon` | 135 | 3.4% | 14.1% | 0.0% | 65.01x |
| `swept_asia_low_1h` | `bullish` | `1-3d` | 32 | 1.0% | 40.6% | 59.4% | 26.57x |
| `swept_asia_low_1h` | `bullish` | `1-4h` | 2,637 | 79.1% | 14.7% | 85.2% | 15.92x |
| `swept_asia_low_1h` | `bullish` | `4h-1d` | 510 | 15.3% | 15.9% | 84.1% | 40.11x |
| `swept_asia_low_1h` | `bullish` | `unreached_native_horizon` | 153 | 4.6% | 19.6% | 0.0% | 51.53x |
| `swept_london_high_1h` | `bearish` | `1-3d` | 94 | 2.1% | 27.7% | 72.3% | 42.54x |
| `swept_london_high_1h` | `bearish` | `1-4h` | 3,395 | 75.2% | 12.1% | 87.5% | 21.81x |
| `swept_london_high_1h` | `bearish` | `4h-1d` | 719 | 15.9% | 15.9% | 84.1% | 34.39x |
| `swept_london_high_1h` | `bearish` | `unreached_native_horizon` | 304 | 6.7% | 15.5% | 0.0% | 78.30x |
| `swept_london_low_1h` | `bullish` | `1-3d` | 74 | 2.0% | 31.1% | 68.9% | 25.97x |
| `swept_london_low_1h` | `bullish` | `1-4h` | 2,776 | 74.2% | 17.4% | 82.4% | 18.97x |
| `swept_london_low_1h` | `bullish` | `4h-1d` | 595 | 15.9% | 18.3% | 81.5% | 30.35x |
| `swept_london_low_1h` | `bullish` | `unreached_native_horizon` | 294 | 7.9% | 12.2% | 0.0% | 58.31x |
| `swept_ny_high_1h` | `bearish` | `1-3d` | 100 | 2.8% | 22.0% | 78.0% | 21.00x |
| `swept_ny_high_1h` | `bearish` | `1-4h` | 2,862 | 78.9% | 16.1% | 82.3% | 7.21x |
| `swept_ny_high_1h` | `bearish` | `4h-1d` | 347 | 9.6% | 18.2% | 79.8% | 13.91x |
| `swept_ny_high_1h` | `bearish` | `unreached_native_horizon` | 317 | 8.7% | 14.2% | 0.0% | 34.30x |
| `swept_ny_low_1h` | `bullish` | `1-3d` | 51 | 1.6% | 33.3% | 62.7% | 7.84x |
| `swept_ny_low_1h` | `bullish` | `1-4h` | 2,518 | 81.0% | 20.6% | 76.2% | 5.74x |
| `swept_ny_low_1h` | `bullish` | `4h-1d` | 251 | 8.1% | 27.5% | 68.1% | 15.53x |
| `swept_ny_low_1h` | `bullish` | `unreached_native_horizon` | 288 | 9.3% | 14.2% | 0.0% | 26.51x |
| `swept_pdh_1h` | `bearish` | `1-3d` | 61 | 1.1% | 34.4% | 65.6% | 44.29x |
| `swept_pdh_1h` | `bearish` | `1-4h` | 4,520 | 81.6% | 10.1% | 89.6% | 17.92x |
| `swept_pdh_1h` | `bearish` | `4h-1d` | 730 | 13.2% | 13.2% | 86.7% | 38.22x |
| `swept_pdh_1h` | `bearish` | `unreached_native_horizon` | 230 | 4.2% | 18.3% | 0.0% | 62.09x |
| `swept_pdh_4h` | `bearish` | `1-3d` | 302 | 5.5% | 11.9% | 87.7% | 54.68x |
| `swept_pdh_4h` | `bearish` | `3-7d` | 127 | 2.3% | 11.0% | 89.0% | 53.32x |
| `swept_pdh_4h` | `bearish` | `4h-1d` | 4,885 | 88.9% | 9.1% | 90.9% | 29.41x |
| `swept_pdh_4h` | `bearish` | `7-20d` | 22 | 0.4% | 13.6% | 86.4% | 49.00x |
| `swept_pdh_4h` | `bearish` | `unreached_native_horizon` | 161 | 2.9% | 22.4% | 0.0% | 112.38x |
| `swept_pdl_1h` | `bullish` | `1-3d` | 56 | 1.1% | 33.9% | 66.1% | 24.51x |
| `swept_pdl_1h` | `bullish` | `1-4h` | 3,992 | 81.3% | 17.1% | 82.3% | 13.42x |
| `swept_pdl_1h` | `bullish` | `4h-1d` | 625 | 12.7% | 17.4% | 82.2% | 36.41x |
| `swept_pdl_1h` | `bullish` | `unreached_native_horizon` | 235 | 4.8% | 18.7% | 0.0% | 44.79x |
| `swept_pdl_4h` | `bullish` | `1-3d` | 252 | 5.0% | 18.3% | 81.7% | 48.43x |
| `swept_pdl_4h` | `bullish` | `3-7d` | 112 | 2.2% | 21.4% | 78.6% | 33.58x |
| `swept_pdl_4h` | `bullish` | `4h-1d` | 4,315 | 86.2% | 17.1% | 82.9% | 21.74x |
| `swept_pdl_4h` | `bullish` | `7-20d` | 18 | 0.4% | 44.4% | 55.6% | 51.79x |
| `swept_pdl_4h` | `bullish` | `unreached_native_horizon` | 311 | 6.2% | 16.4% | 0.0% | 68.13x |
| `swept_pwh_4h` | `bearish` | `1-3d` | 49 | 5.3% | 8.2% | 91.8% | 80.33x |
| `swept_pwh_4h` | `bearish` | `3-7d` | 19 | 2.1% | 26.3% | 73.7% | 19.24x |
| `swept_pwh_4h` | `bearish` | `4h-1d` | 824 | 89.9% | 8.0% | 92.0% | 20.86x |
| `swept_pwh_4h` | `bearish` | `7-20d` | 4 | 0.4% | 50.0% | 50.0% | 8.75x |
| `swept_pwh_4h` | `bearish` | `unreached_native_horizon` | 21 | 2.3% | 19.0% | 0.0% | 63.94x |
| `swept_pwh_daily` | `bearish` | `1-3d` | 726 | 84.8% | 6.1% | 93.8% | 22.28x |
| `swept_pwh_daily` | `bearish` | `20d+` | 15 | 1.8% | 20.0% | 80.0% | 34.75x |
| `swept_pwh_daily` | `bearish` | `3-7d` | 58 | 6.8% | 0.0% | 100.0% | 22.72x |
| `swept_pwh_daily` | `bearish` | `7-20d` | 34 | 4.0% | 2.9% | 97.1% | 28.71x |
| `swept_pwh_daily` | `bearish` | `unreached_native_horizon` | 23 | 2.7% | 13.0% | 0.0% | 309.97x |
| `swept_pwl_4h` | `bullish` | `1-3d` | 23 | 3.6% | 21.7% | 78.3% | 53.47x |
| `swept_pwl_4h` | `bullish` | `3-7d` | 12 | 1.9% | 25.0% | 75.0% | 181.79x |
| `swept_pwl_4h` | `bullish` | `4h-1d` | 567 | 87.6% | 18.0% | 81.8% | 11.62x |
| `swept_pwl_4h` | `bullish` | `7-20d` | 3 | 0.5% | 0.0% | 100.0% | 158.04x |
| `swept_pwl_4h` | `bullish` | `unreached_native_horizon` | 42 | 6.5% | 9.5% | 0.0% | 32.87x |
| `swept_pwl_daily` | `bullish` | `1-3d` | 476 | 76.4% | 21.4% | 78.6% | 18.38x |
| `swept_pwl_daily` | `bullish` | `20d+` | 22 | 3.5% | 18.2% | 81.8% | 24.09x |
| `swept_pwl_daily` | `bullish` | `3-7d` | 37 | 5.9% | 29.7% | 67.6% | 20.44x |

## Notes

- `level.price_low/high` are the OB body bounds.
- `level.range_low/high` preserve the full wick range of the OB candle.
- `meaningful_touch` means price reached at least q25 into the body.
- `full_touch` means price reached the far body edge.
- `closed_through` means OB invalidation by close through the far body edge.
- `directional_rejection` is broad: touched entry, avoided invalidation, and moved at least one body size in thesis direction inside the native horizon.
- `unreached_native_horizon` means no meaningful test inside the 50-native-candle source horizon.
- `lr.*` columns are labels/outcomes, not model inputs.
