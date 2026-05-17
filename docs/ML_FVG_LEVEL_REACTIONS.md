# FVG Level Reactions

_Generated `2026-05-17T01:22:41.520753+00:00`._

This maps fair-value-gap zones into the same `level.*` and `lr.*`
vocabulary used by opening gaps. FVG horizons are native-candle
windows because the source outcome computer is native-timeframe based.

- Source: `C:\Users\benbr\BacktestStation\data\ml\features\fvg.parquet`
- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\fvg_level_reactions.parquet`
- Rows: `209,339`
- Columns: `119`

## Counts

| Subtype | Side | Rows |
|---|---|---|
| `15m_fvg` | `bearish` | 72,077 |
| `15m_fvg` | `bullish` | 82,384 |
| `1h_fvg` | `bearish` | 17,894 |
| `1h_fvg` | `bullish` | 22,313 |
| `4h_fvg` | `bearish` | 5,020 |
| `4h_fvg` | `bullish` | 6,863 |
| `daily_fvg` | `bearish` | 1,046 |
| `daily_fvg` | `bullish` | 1,742 |

## Overall Reaction Rates

| Horizon | Rows | Touch | Mid Fill | Full Fill | Wick Reject | Close Through | Avg Thesis / Size |
|---|---|---|---|---|---|---|---|
| `next_3_bars` | 209,339 | 63.3% | 50.5% | 42.3% | 31.7% | 25.9% | 6.37x |
| `next_10_bars` | 209,339 | 78.1% | 69.7% | 63.3% | 39.4% | 49.1% | 12.63x |
| `next_50_bars` | 209,339 | 89.3% | 85.2% | 81.8% | 45.2% | 73.5% | 31.77x |
| `full_horizon` | 209,339 | 89.3% | 85.2% | 81.8% | 45.2% | 73.5% | 31.77x |

## First-Touch Age Decay

| Subtype | Side | Age | Rows | Share | Reject | Break | Avg Thesis / Size |
|---|---|---|---|---|---|---|---|
| `15m_fvg` | `bearish` | `0-1h` | 46,789 | 64.9% | 48.6% | 85.7% | 29.40x |
| `15m_fvg` | `bearish` | `1-4h` | 12,940 | 18.0% | 50.3% | 83.2% | 29.93x |
| `15m_fvg` | `bearish` | `4h-1d` | 5,143 | 7.1% | 51.6% | 72.9% | 33.24x |
| `15m_fvg` | `bearish` | `unreached_native_horizon` | 7,205 | 10.0% | 0.0% | 0.0% | 44.29x |
| `15m_fvg` | `bullish` | `0-1h` | 52,050 | 63.2% | 50.8% | 81.9% | 26.89x |
| `15m_fvg` | `bullish` | `1-4h` | 14,718 | 17.9% | 52.7% | 80.0% | 27.12x |
| `15m_fvg` | `bullish` | `4h-1d` | 6,110 | 7.4% | 52.8% | 73.4% | 30.13x |
| `15m_fvg` | `bullish` | `unreached_native_horizon` | 9,506 | 11.5% | 0.0% | 0.0% | 36.64x |
| `1h_fvg` | `bearish` | `1-3d` | 663 | 3.7% | 46.0% | 65.2% | 39.17x |
| `1h_fvg` | `bearish` | `1-4h` | 11,329 | 63.3% | 49.5% | 86.9% | 34.92x |
| `1h_fvg` | `bearish` | `4h-1d` | 4,206 | 23.5% | 50.8% | 82.3% | 31.72x |
| `1h_fvg` | `bearish` | `unreached_native_horizon` | 1,696 | 9.5% | 0.0% | 0.0% | 68.38x |
| `1h_fvg` | `bullish` | `1-3d` | 845 | 3.8% | 52.5% | 62.6% | 32.96x |
| `1h_fvg` | `bullish` | `1-4h` | 13,458 | 60.3% | 53.2% | 82.2% | 36.28x |
| `1h_fvg` | `bullish` | `4h-1d` | 5,421 | 24.3% | 54.9% | 77.7% | 32.60x |
| `1h_fvg` | `bullish` | `unreached_native_horizon` | 2,589 | 11.6% | 0.0% | 0.0% | 49.62x |
| `4h_fvg` | `bearish` | `1-3d` | 644 | 12.8% | 49.4% | 85.9% | 38.36x |
| `4h_fvg` | `bearish` | `3-7d` | 319 | 6.4% | 42.3% | 82.4% | 48.38x |
| `4h_fvg` | `bearish` | `4h-1d` | 3,652 | 72.7% | 50.3% | 88.6% | 33.63x |
| `4h_fvg` | `bearish` | `7-20d` | 54 | 1.1% | 38.9% | 70.4% | 38.91x |
| `4h_fvg` | `bearish` | `unreached_native_horizon` | 351 | 7.0% | 0.0% | 0.0% | 96.78x |
| `4h_fvg` | `bullish` | `1-3d` | 862 | 12.6% | 54.1% | 76.1% | 28.73x |
| `4h_fvg` | `bullish` | `3-7d` | 410 | 6.0% | 51.7% | 72.9% | 26.68x |
| `4h_fvg` | `bullish` | `4h-1d` | 4,663 | 67.9% | 53.5% | 79.2% | 36.78x |
| `4h_fvg` | `bullish` | `7-20d` | 69 | 1.0% | 59.4% | 46.4% | 39.27x |
| `4h_fvg` | `bullish` | `unreached_native_horizon` | 859 | 12.5% | 0.0% | 0.0% | 57.19x |
| `daily_fvg` | `bearish` | `1-3d` | 688 | 65.8% | 41.1% | 93.9% | 34.31x |
| `daily_fvg` | `bearish` | `20d+` | 45 | 4.3% | 42.2% | 84.4% | 42.57x |
| `daily_fvg` | `bearish` | `3-7d` | 154 | 14.7% | 37.0% | 94.2% | 28.22x |
| `daily_fvg` | `bearish` | `7-20d` | 93 | 8.9% | 36.6% | 93.5% | 60.41x |
| `daily_fvg` | `bearish` | `unreached_native_horizon` | 66 | 6.3% | 0.0% | 0.0% | 103.58x |
| `daily_fvg` | `bullish` | `1-3d` | 968 | 55.6% | 53.4% | 79.1% | 44.89x |
| `daily_fvg` | `bullish` | `20d+` | 100 | 5.7% | 43.0% | 80.0% | 32.25x |
| `daily_fvg` | `bullish` | `3-7d` | 254 | 14.6% | 54.7% | 79.5% | 26.24x |
| `daily_fvg` | `bullish` | `7-20d` | 193 | 11.1% | 51.3% | 78.8% | 29.95x |
| `daily_fvg` | `bullish` | `unreached_native_horizon` | 227 | 13.0% | 0.0% | 0.0% | 77.07x |

## Notes

- `level.created_ts_utc` is the first knowable timestamp, not the candle-3 start.
- `lr.next_3_bars.*`, `lr.next_10_bars.*`, and `lr.next_50_bars.*` are native-candle horizons.
- `lr.full_horizon.*` matches the mitigation horizon from the FVG outcome computer.
- `unreached_native_horizon` means no touch/fill inside the 50-native-candle source horizon.
- `lr.*` columns are labels/outcomes, not model inputs.
