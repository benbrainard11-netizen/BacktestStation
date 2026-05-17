# 2025 Regime Diagnostic

_Generated `2026-05-17T13:32:07.163378+00:00`._

This compares 2025 level behavior against 2023-2024 behavior.

## Interpretation

- This diagnostic compares 2025 level behavior against weighted 2023-2024 behavior.
- Large deltas mean a level family changed behavior; they do not prove a trading edge by themselves.
- Most affected families in the top drift rows: order_block (5), liquidity_sweep (4), opening_gap (1)

## Largest Level-Reaction Drifts

| Kind | Subtype | Side | Horizon | Prior rows | 2025 rows | Prior touch | 2025 touch | Touch delta | Reject delta | Break delta |
|---|---|---|---|---|---|---|---|---|---|---|
| `liquidity_sweep` | `pwl_4h` | `low` | `next_3_bars` | 139 | 64 | 59.0% | 39.1% | -19.9% | -19.8% | -6.9% |
| `order_block` | `swept_pwh_daily` | `bearish` | `next_3_bars` | 151 | 70 | 89.4% | 90.0% | 0.6% | 17.2% | -11.8% |
| `order_block` | `swept_pwl_4h` | `bullish` | `next_3_bars` | 111 | 52 | 86.5% | 86.5% | 0.1% | -8.7% | 14.6% |
| `opening_gap` | `nwog` | `gap_up` | `next_60m` | 203 | 83 | 66.5% | 53.0% | -13.5% | 6.3% | 0.1% |
| `liquidity_sweep` | `pwh_4h` | `high` | `next_3_bars` | 209 | 99 | 43.1% | 51.5% | 8.5% | 12.6% | 8.0% |
| `order_block` | `swept_pwh_4h` | `bearish` | `next_3_bars` | 159 | 79 | 87.4% | 86.1% | -1.3% | -11.2% | 11.7% |
| `liquidity_sweep` | `pwl_daily` | `low` | `next_3_bars` | 139 | 64 | 64.0% | 60.9% | -3.1% | -10.6% | -5.3% |
| `liquidity_sweep` | `asia_low_1h` | `low` | `next_3_bars` | 683 | 362 | 20.9% | 31.2% | 10.3% | 4.2% | 5.0% |
| `order_block` | `swept_asia_low_1h` | `bullish` | `next_3_bars` | 578 | 303 | 82.9% | 72.6% | -10.3% | 2.6% | -4.6% |
| `order_block` | `swept_pwl_daily` | `bullish` | `next_3_bars` | 100 | 52 | 83.0% | 73.1% | -9.9% | 4.5% | -3.2% |
| `fair_value_gap` | `daily_fvg` | `bearish` | `next_3_bars` | 187 | 90 | 63.6% | 71.1% | 7.5% | -9.4% | 5.2% |
| `swing_pivot` | `pivot_5_daily` | `high` | `next_3_bars` | 109 | 54 | 24.8% | 18.5% | -6.3% | 3.7% | -9.1% |
| `opening_gap` | `ndog` | `gap_down` | `next_60m` | 668 | 363 | 85.3% | 85.1% | -0.2% | -9.0% | 6.3% |
| `opening_gap` | `ndog` | `gap_up` | `next_60m` | 749 | 357 | 84.9% | 80.1% | -4.8% | 7.6% | -6.5% |
| `fair_value_gap` | `daily_fvg` | `bullish` | `next_3_bars` | 320 | 150 | 61.3% | 64.0% | 2.7% | 0.9% | 7.1% |
| `order_block` | `swept_pdl_1h` | `bullish` | `next_3_bars` | 891 | 428 | 84.4% | 77.3% | -7.1% | -2.5% | -2.1% |
| `swing_pivot` | `pivot_5_4h` | `high` | `next_3_bars` | 637 | 315 | 21.0% | 24.4% | 3.4% | -2.6% | 6.3% |
| `liquidity_sweep` | `ny_high_1h` | `high` | `next_3_bars` | 782 | 386 | 48.2% | 49.7% | 1.5% | 2.6% | 5.9% |
| `liquidity_sweep` | `ny_low_1h` | `low` | `next_3_bars` | 627 | 302 | 55.8% | 55.6% | -0.2% | -5.4% | -0.7% |
| `order_block` | `swept_london_low_1h` | `bullish` | `next_3_bars` | 691 | 350 | 76.4% | 71.4% | -5.0% | -5.4% | -3.8% |
| `liquidity_sweep` | `pwh_daily` | `high` | `next_3_bars` | 209 | 99 | 48.3% | 53.5% | 5.2% | 3.0% | 4.1% |
| `swing_pivot` | `pivot_5_daily` | `low` | `next_3_bars` | 112 | 54 | 14.3% | 9.3% | -5.0% | -1.7% | -2.5% |
| `equal_levels` | `eq_pivot_3_1h_5pts` | `low` | `next_5_bars` | 869 | 342 | 19.1% | 14.6% | -4.5% | -0.6% | -2.4% |
| `liquidity_sweep` | `asia_high_1h` | `high` | `next_3_bars` | 837 | 415 | 16.7% | 19.8% | 3.0% | 1.7% | 4.3% |
| `liquidity_sweep` | `pdl_4h` | `low` | `next_3_bars` | 1,019 | 501 | 44.3% | 48.5% | 4.2% | 2.5% | -0.4% |
| `swing_pivot` | `pivot_5_4h` | `low` | `next_3_bars` | 577 | 309 | 19.6% | 15.9% | -3.7% | -2.3% | -3.5% |
| `fair_value_gap` | `4h_fvg` | `bullish` | `next_3_bars` | 1,172 | 658 | 55.8% | 59.1% | 3.3% | -2.5% | 3.5% |
| `liquidity_sweep` | `pdh_4h` | `high` | `next_3_bars` | 1,167 | 571 | 35.3% | 33.1% | -2.2% | -1.8% | -3.4% |
| `order_block` | `swept_pdl_4h` | `bullish` | `next_3_bars` | 911 | 452 | 84.4% | 86.7% | 2.3% | 3.4% | -0.5% |
| `fair_value_gap` | `4h_fvg` | `bearish` | `next_3_bars` | 885 | 463 | 60.3% | 60.9% | 0.6% | -3.0% | -0.3% |

## Feature Matrix Year Mix

| Matrix | Rows | 2023 | 2024 | 2025 | 2025 share |
|---|---|---|---|---|---|
| `fvg` | 209,339 | 18,955 | 19,344 | 19,519 | 9.3% |
| `swing` | 76,786 | 6,994 | 6,958 | 6,942 | 9.0% |
| `sweep` | 52,946 | 4,812 | 4,806 | 4,763 | 9.0% |
| `ob` | 46,331 | 4,129 | 4,188 | 4,091 | 8.8% |
| `fvp` | 43,150 | 3,870 | 3,885 | 3,870 | 9.0% |
| `eql` | 60,338 | 4,814 | 4,309 | 3,745 | 6.2% |
| `disp` | 38,747 | 3,611 | 3,607 | 3,390 | 8.7% |
| `itr` | 36,095 | 3,237 | 3,252 | 3,234 | 9.0% |
| `vp` | 36,095 | 3,240 | 3,252 | 3,231 | 9.0% |
| `orb` | 34,040 | 3,054 | 3,072 | 3,042 | 8.9% |
| `tp` | 19,414 | 1,743 | 1,746 | 1,740 | 9.0% |
| `psp` | 15,827 | 1,633 | 2,009 | 1,687 | 10.7% |
| `ft` | 10,373 | 930 | 936 | 930 | 9.0% |
| `ogap` | 9,438 | 844 | 872 | 867 | 9.2% |
| `macro` | 18,414 | 1,665 | 1,842 | 537 | 2.9% |
| `smt` | 2,891 | 312 | 346 | 269 | 9.3% |

## How To Use

- If a model works before 2025 and weakens in 2025, check whether its anchor family appears in the drift table.
- A large positive break delta means price accepted through that level more often in 2025.
- A large negative rejection delta means support/resistance behavior weakened in 2025.
- This is a dataset diagnostic, not a strategy report.
