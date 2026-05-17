# Level Reaction Leaderboard

_Generated `2026-05-17T04:05:14.359771+00:00`._

This ranks the combined level database by clean directional behavior.
The score rewards one-sided behavior and down-weights small samples.

- Source: `C:\Users\benbr\BacktestStation\data\ml\levels\all_level_reactions.parquet`
- CSV: `C:\Users\benbr\BacktestStation\data\ml\levels\level_reaction_leaderboard.csv`
- Parquet: `C:\Users\benbr\BacktestStation\data\ml\levels\level_reaction_leaderboard.parquet`
- Rows: `554` leaderboard segments
- Minimum report rows: `200`

## Score

`clean_signal_score = sample_weight * max(reject_rate, break_rate) * abs(reject_rate - break_rate)`

This means a level ranks highly only if rejection or break behavior clearly dominates.
A group with both rejection and break high gets penalized because it is mixed.

## Best Level Families

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind` | `order_block` | - | - | `next_50_bars` | 46,331 | `break` | 14.4% | 80.5% | 0.533 | `A` | `break_continuation_bias` |
| `kind` | `order_block` | - | - | `full_horizon` | 46,331 | `break` | 14.4% | 80.5% | 0.533 | `A` | `break_continuation_bias` |
| `kind` | `equal_levels` | - | - | `next_250_bars` | 60,338 | `break` | 4.3% | 69.2% | 0.449 | `A` | `break_continuation_bias` |
| `kind` | `equal_levels` | - | - | `full_horizon` | 60,338 | `break` | 4.3% | 69.2% | 0.449 | `A` | `break_continuation_bias` |
| `kind` | `equal_levels` | - | - | `next_100_bars` | 60,338 | `break` | 5.5% | 61.6% | 0.345 | `A` | `break_continuation_bias` |
| `kind` | `swing_pivot` | - | - | `next_50_bars` | 76,786 | `break` | 7.3% | 62.2% | 0.341 | `A` | `break_continuation_bias` |
| `kind` | `swing_pivot` | - | - | `full_horizon` | 76,786 | `break` | 7.3% | 62.2% | 0.341 | `A` | `break_continuation_bias` |
| `kind` | `opening_gap` | - | - | `next_60m` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_240m` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_1d` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_5d` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_20d` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `full_horizon` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `order_block` | - | - | `next_10_bars` | 46,331 | `break` | 24.4% | 61.9% | 0.232 | `A` | `break_continuation_bias` |
| `kind` | `fair_value_gap` | - | - | `next_50_bars` | 209,339 | `break` | 45.2% | 73.5% | 0.208 | `A` | `break_continuation_bias` |
| `kind` | `fair_value_gap` | - | - | `full_horizon` | 209,339 | `break` | 45.2% | 73.5% | 0.208 | `A` | `break_continuation_bias` |
| `kind` | `equal_levels` | - | - | `next_25_bars` | 60,338 | `break` | 7.6% | 34.5% | 0.093 | `C` | `break_continuation_bias` |
| `kind` | `swing_pivot` | - | - | `next_10_bars` | 76,786 | `break` | 8.4% | 34.9% | 0.092 | `C` | `break_continuation_bias` |
| `kind` | `order_block` | - | - | `next_3_bars` | 46,331 | `break` | 27.5% | 40.2% | 0.051 | `C` | `break_continuation_bias` |
| `kind` | `fair_value_gap` | - | - | `next_10_bars` | 209,339 | `break` | 39.4% | 49.1% | 0.047 | `D` | `mixed_or_weak` |

## Best Subtypes / Sides

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `next_50_bars` | 5,497 | `break` | 9.7% | 88.0% | 0.689 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `full_horizon` | 5,497 | `break` | 9.7% | 88.0% | 0.689 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `next_50_bars` | 4,017 | `break` | 10.1% | 86.9% | 0.650 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `full_horizon` | 4,017 | `break` | 10.1% | 86.9% | 0.650 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `next_50_bars` | 5,541 | `break` | 11.1% | 85.2% | 0.632 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `full_horizon` | 5,541 | `break` | 11.1% | 85.2% | 0.632 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `next_50_bars` | 856 | `break` | 6.0% | 91.6% | 0.622 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `full_horizon` | 856 | `break` | 6.0% | 91.6% | 0.622 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `next_250_bars` | 12,975 | `break` | 4.4% | 78.8% | 0.587 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `full_horizon` | 12,975 | `break` | 4.4% | 78.8% | 0.587 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `next_50_bars` | 917 | `break` | 8.8% | 89.3% | 0.576 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `full_horizon` | 917 | `break` | 8.8% | 89.3% | 0.576 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_london_high_1h` | - | `next_50_bars` | 4,512 | `break` | 13.3% | 80.8% | 0.539 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_london_high_1h` | - | `full_horizon` | 4,512 | `break` | 13.3% | 80.8% | 0.539 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_5_1h_5pts` | - | `next_250_bars` | 6,876 | `break` | 4.5% | 74.0% | 0.514 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_5_1h_5pts` | - | `full_horizon` | 6,876 | `break` | 4.5% | 74.0% | 0.514 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_low_1h` | - | `next_50_bars` | 3,332 | `break` | 15.3% | 80.9% | 0.505 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_low_1h` | - | `full_horizon` | 3,332 | `break` | 15.3% | 80.9% | 0.505 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `next_100_bars` | 12,975 | `break` | 5.8% | 72.4% | 0.482 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_1h` | - | `next_50_bars` | 4,908 | `break` | 17.4% | 78.2% | 0.474 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_1h` | - | `full_horizon` | 4,908 | `break` | 17.4% | 78.2% | 0.474 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_4h` | - | `next_50_bars` | 5,008 | `break` | 17.3% | 77.5% | 0.466 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_4h` | - | `full_horizon` | 5,008 | `break` | 17.3% | 77.5% | 0.466 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_15pts` | - | `next_250_bars` | 21,077 | `break` | 4.3% | 69.8% | 0.457 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_15pts` | - | `full_horizon` | 21,077 | `break` | 4.3% | 69.8% | 0.457 | `A` | `break_continuation_bias` |

## Best Short-Horizon Signals

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_60m` | 1,623 | `rejection` | 77.6% | 10.9% | 0.450 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_60m` | 4,873 | `rejection` | 67.4% | 15.0% | 0.352 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_60m` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `next_60m` | 4,565 | `rejection` | 64.7% | 15.7% | 0.313 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `ndog` | - | `next_60m` | 7,815 | `rejection` | 63.7% | 16.3% | 0.302 | `A` | `rejection_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `next_3_bars` | 856 | `break` | 25.9% | 53.5% | 0.117 | `B` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `next_3_bars` | 917 | `break` | 23.9% | 49.9% | 0.104 | `B` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `next_3_bars` | 5,497 | `break` | 29.9% | 50.5% | 0.104 | `B` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_ny_high_1h` | - | `next_3_bars` | 3,626 | `break` | 22.5% | 40.3% | 0.069 | `C` | `break_continuation_bias` |
| `kind_side` | `order_block` | - | `bearish` | `next_3_bars` | 24,966 | `break` | 27.6% | 43.0% | 0.066 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `next_3_bars` | 5,541 | `break` | 26.7% | 40.9% | 0.058 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_4h` | - | `next_3_bars` | 5,008 | `break` | 30.9% | 43.0% | 0.052 | `C` | `break_continuation_bias` |
| `kind` | `order_block` | - | - | `next_3_bars` | 46,331 | `break` | 27.5% | 40.2% | 0.051 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_ny_low_1h` | - | `next_3_bars` | 3,108 | `break` | 21.8% | 36.1% | 0.049 | `D` | `mixed_or_weak` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `next_3_bars` | 4,017 | `break` | 27.5% | 38.9% | 0.043 | `D` | `mixed_or_weak` |
| `kind_subtype` | `liquidity_sweep` | `pwh_daily` | - | `next_3_bars` | 1,112 | `break` | 49.3% | 57.4% | 0.038 | `D` | `mixed_or_weak` |
| `kind_side` | `order_block` | - | `bullish` | `next_3_bars` | 21,365 | `break` | 27.5% | 37.1% | 0.035 | `D` | `mixed_or_weak` |
| `kind_subtype` | `liquidity_sweep` | `pwl_daily` | - | `next_3_bars` | 760 | `rejection` | 57.4% | 50.3% | 0.032 | `D` | `mixed_or_weak` |
| `kind_subtype` | `order_block` | `swept_pwl_4h` | - | `next_3_bars` | 647 | `break` | 25.2% | 36.0% | 0.030 | `D` | `mixed_or_weak` |
| `kind_subtype` | `order_block` | `swept_pdl_1h` | - | `next_3_bars` | 4,908 | `break` | 26.7% | 35.0% | 0.029 | `D` | `mixed_or_weak` |
| `kind_subtype` | `liquidity_sweep` | `ny_low_1h` | - | `next_3_bars` | 3,452 | `rejection` | 42.4% | 35.2% | 0.029 | `D` | `mixed_or_weak` |
| `kind_subtype` | `order_block` | `swept_london_high_1h` | - | `next_3_bars` | 4,512 | `break` | 31.1% | 38.7% | 0.029 | `D` | `mixed_or_weak` |
| `kind_subtype` | `order_block` | `swept_pwl_daily` | - | `next_3_bars` | 623 | `break` | 27.8% | 37.2% | 0.027 | `D` | `mixed_or_weak` |
| `kind_subtype` | `liquidity_sweep` | `pdh_4h` | - | `next_3_bars` | 6,417 | `break` | 32.9% | 39.0% | 0.024 | `D` | `mixed_or_weak` |
| `kind_subtype` | `liquidity_sweep` | `pwh_4h` | - | `next_3_bars` | 1,112 | `break` | 40.5% | 46.5% | 0.023 | `D` | `mixed_or_weak` |

## Rejection Bias Leaders

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_60m` | 1,623 | `rejection` | 77.6% | 10.9% | 0.450 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_1d` | 1,623 | `rejection` | 77.6% | 10.9% | 0.450 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_20d` | 1,623 | `rejection` | 77.6% | 10.9% | 0.450 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `full_horizon` | 1,623 | `rejection` | 77.6% | 10.9% | 0.450 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_5d` | 1,623 | `rejection` | 77.6% | 10.9% | 0.450 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_240m` | 1,623 | `rejection` | 77.6% | 10.9% | 0.450 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_5d` | 4,873 | `rejection` | 67.4% | 15.0% | 0.352 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_60m` | 4,873 | `rejection` | 67.4% | 15.0% | 0.352 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_240m` | 4,873 | `rejection` | 67.4% | 15.0% | 0.352 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `full_horizon` | 4,873 | `rejection` | 67.4% | 15.0% | 0.352 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_1d` | 4,873 | `rejection` | 67.4% | 15.0% | 0.352 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_20d` | 4,873 | `rejection` | 67.4% | 15.0% | 0.352 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_240m` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_60m` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_1d` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_20d` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `full_horizon` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_5d` | 9,438 | `rejection` | 66.1% | 15.4% | 0.335 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `full_horizon` | 4,565 | `rejection` | 64.7% | 15.7% | 0.313 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `next_1d` | 4,565 | `rejection` | 64.7% | 15.7% | 0.313 | `A` | `rejection_bias` |

## Break / Continuation Bias Leaders

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `full_horizon` | 5,497 | `break` | 9.7% | 88.0% | 0.689 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `next_50_bars` | 5,497 | `break` | 9.7% | 88.0% | 0.689 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `full_horizon` | 4,017 | `break` | 10.1% | 86.9% | 0.650 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `next_50_bars` | 4,017 | `break` | 10.1% | 86.9% | 0.650 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `full_horizon` | 5,541 | `break` | 11.1% | 85.2% | 0.632 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `next_50_bars` | 5,541 | `break` | 11.1% | 85.2% | 0.632 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `full_horizon` | 856 | `break` | 6.0% | 91.6% | 0.622 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `next_50_bars` | 856 | `break` | 6.0% | 91.6% | 0.622 | `A` | `break_continuation_bias` |
| `kind_side` | `order_block` | - | `bearish` | `full_horizon` | 24,966 | `break` | 11.5% | 84.1% | 0.611 | `A` | `break_continuation_bias` |
| `kind_side` | `order_block` | - | `bearish` | `next_50_bars` | 24,966 | `break` | 11.5% | 84.1% | 0.611 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `full_horizon` | 12,975 | `break` | 4.4% | 78.8% | 0.587 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `next_250_bars` | 12,975 | `break` | 4.4% | 78.8% | 0.587 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `full_horizon` | 917 | `break` | 8.8% | 89.3% | 0.576 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `next_50_bars` | 917 | `break` | 8.8% | 89.3% | 0.576 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_london_high_1h` | - | `full_horizon` | 4,512 | `break` | 13.3% | 80.8% | 0.539 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_london_high_1h` | - | `next_50_bars` | 4,512 | `break` | 13.3% | 80.8% | 0.539 | `A` | `break_continuation_bias` |
| `kind_side` | `equal_levels` | - | `high` | `full_horizon` | 31,471 | `break` | 2.9% | 74.9% | 0.538 | `A` | `break_continuation_bias` |
| `kind_side` | `equal_levels` | - | `high` | `next_250_bars` | 31,471 | `break` | 2.9% | 74.9% | 0.538 | `A` | `break_continuation_bias` |
| `kind` | `order_block` | - | - | `next_50_bars` | 46,331 | `break` | 14.4% | 80.5% | 0.533 | `A` | `break_continuation_bias` |
| `kind` | `order_block` | - | - | `full_horizon` | 46,331 | `break` | 14.4% | 80.5% | 0.533 | `A` | `break_continuation_bias` |

## Notes

- This is an outcome/label leaderboard, not a trading system.
- The markdown report hides `kind_subtype_side` duplicates; the CSV/parquet keep every segment.
- `rejection_bias` means rejection dominates break behavior for that segment/horizon.
- `break_continuation_bias` means break/continuation dominates rejection behavior.
- Opening gaps use clock-time horizons; FVG, OB, sweep, and swing use native-bar horizons.
- Equal levels use 1h native-bar take/reaction horizons.
- Use short-horizon rows for cleaner behavior comparisons; full horizon can become too broad.
- `lr.*` columns remain future outcomes and must not be used as model inputs unless selecting targets.
