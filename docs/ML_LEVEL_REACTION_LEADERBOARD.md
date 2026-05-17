# Level Reaction Leaderboard

_Generated `2026-05-17T16:43:24.235261+00:00`._

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
| `kind` | `order_block` | - | - | `next_50_bars` | 198,069 | `break` | 14.0% | 80.7% | 0.539 | `A` | `break_continuation_bias` |
| `kind` | `order_block` | - | - | `full_horizon` | 198,069 | `break` | 14.0% | 80.7% | 0.539 | `A` | `break_continuation_bias` |
| `kind` | `equal_levels` | - | - | `next_250_bars` | 61,185 | `break` | 3.5% | 73.5% | 0.514 | `A` | `break_continuation_bias` |
| `kind` | `equal_levels` | - | - | `full_horizon` | 61,185 | `break` | 3.5% | 73.5% | 0.514 | `A` | `break_continuation_bias` |
| `kind` | `swing_pivot` | - | - | `next_50_bars` | 345,702 | `break` | 6.4% | 64.5% | 0.374 | `A` | `break_continuation_bias` |
| `kind` | `swing_pivot` | - | - | `full_horizon` | 345,702 | `break` | 6.4% | 64.5% | 0.374 | `A` | `break_continuation_bias` |
| `kind` | `equal_levels` | - | - | `next_100_bars` | 61,185 | `break` | 5.3% | 61.4% | 0.345 | `A` | `break_continuation_bias` |
| `kind` | `opening_gap` | - | - | `next_5d` | 36,944 | `rejection` | 64.1% | 10.4% | 0.345 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_20d` | 36,944 | `rejection` | 64.1% | 10.4% | 0.345 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `full_horizon` | 36,944 | `rejection` | 64.1% | 10.4% | 0.345 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_1d` | 36,944 | `rejection` | 64.1% | 10.4% | 0.344 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_240m` | 36,944 | `rejection` | 62.5% | 10.4% | 0.326 | `A` | `rejection_bias` |
| `kind` | `fair_value_gap` | - | - | `next_50_bars` | 1,243,757 | `break` | 33.5% | 74.0% | 0.300 | `A` | `break_continuation_bias` |
| `kind` | `fair_value_gap` | - | - | `full_horizon` | 1,243,757 | `break` | 33.5% | 74.0% | 0.300 | `A` | `break_continuation_bias` |
| `kind` | `opening_gap` | - | - | `next_60m` | 36,944 | `rejection` | 59.1% | 10.3% | 0.289 | `A` | `rejection_bias` |
| `kind` | `order_block` | - | - | `next_10_bars` | 198,069 | `break` | 23.8% | 61.4% | 0.231 | `A` | `break_continuation_bias` |
| `kind` | `fair_value_gap` | - | - | `next_10_bars` | 1,243,757 | `break` | 29.4% | 51.3% | 0.113 | `B` | `break_continuation_bias` |
| `kind` | `swing_pivot` | - | - | `next_10_bars` | 345,702 | `break` | 7.4% | 34.7% | 0.095 | `C` | `break_continuation_bias` |
| `kind` | `equal_levels` | - | - | `next_25_bars` | 61,185 | `break` | 7.5% | 33.8% | 0.089 | `C` | `break_continuation_bias` |
| `kind` | `order_block` | - | - | `next_3_bars` | 198,069 | `break` | 24.7% | 39.5% | 0.058 | `C` | `break_continuation_bias` |

## Best Subtypes / Sides

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `next_250_bars` | 13,268 | `break` | 3.6% | 82.3% | 0.647 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `full_horizon` | 13,268 | `break` | 3.6% | 82.3% | 0.647 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `next_50_bars` | 17,596 | `break` | 11.4% | 84.4% | 0.616 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `full_horizon` | 17,596 | `break` | 11.4% | 84.4% | 0.616 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `next_50_bars` | 19,237 | `break` | 12.6% | 83.5% | 0.592 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `full_horizon` | 19,237 | `break` | 12.6% | 83.5% | 0.592 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `next_50_bars` | 3,899 | `break` | 12.3% | 84.4% | 0.591 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `full_horizon` | 3,899 | `break` | 12.3% | 84.4% | 0.591 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `next_50_bars` | 4,158 | `break` | 12.7% | 84.0% | 0.586 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `full_horizon` | 4,158 | `break` | 12.7% | 84.0% | 0.586 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_5_1h_5pts` | - | `next_250_bars` | 7,115 | `break` | 3.6% | 78.2% | 0.584 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_5_1h_5pts` | - | `full_horizon` | 7,115 | `break` | 3.6% | 78.2% | 0.584 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_low_1h` | - | `next_50_bars` | 17,250 | `break` | 12.5% | 82.5% | 0.577 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_low_1h` | - | `full_horizon` | 17,250 | `break` | 12.5% | 82.5% | 0.577 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `next_50_bars` | 18,509 | `break` | 13.7% | 81.8% | 0.556 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `full_horizon` | 18,509 | `break` | 13.7% | 81.8% | 0.556 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_4h` | - | `next_50_bars` | 18,572 | `break` | 14.3% | 81.6% | 0.548 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_4h` | - | `full_horizon` | 18,572 | `break` | 14.3% | 81.6% | 0.548 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwl_daily` | - | `next_50_bars` | 3,690 | `break` | 14.0% | 81.7% | 0.533 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwl_daily` | - | `full_horizon` | 3,690 | `break` | 14.0% | 81.7% | 0.533 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_london_high_1h` | - | `next_50_bars` | 19,171 | `break` | 13.6% | 80.0% | 0.532 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_london_high_1h` | - | `full_horizon` | 19,171 | `break` | 13.6% | 80.0% | 0.532 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_15pts` | - | `next_250_bars` | 21,051 | `break` | 3.6% | 73.7% | 0.516 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_15pts` | - | `full_horizon` | 21,051 | `break` | 3.6% | 73.7% | 0.516 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_1h` | - | `next_50_bars` | 17,832 | `break` | 15.5% | 79.9% | 0.514 | `A` | `break_continuation_bias` |

## Best Short-Horizon Signals

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_60m` | 6,687 | `rejection` | 69.1% | 8.6% | 0.419 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `next_60m` | 18,870 | `rejection` | 60.0% | 10.2% | 0.298 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_60m` | 36,944 | `rejection` | 59.1% | 10.3% | 0.289 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_60m` | 18,074 | `rejection` | 58.3% | 10.4% | 0.279 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `ndog` | - | `next_60m` | 30,257 | `rejection` | 56.9% | 10.7% | 0.263 | `A` | `rejection_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `next_3_bars` | 3,899 | `break` | 27.0% | 45.9% | 0.084 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `next_3_bars` | 4,158 | `break` | 22.5% | 42.2% | 0.081 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `next_3_bars` | 19,237 | `break` | 25.1% | 43.2% | 0.078 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `next_3_bars` | 18,509 | `break` | 24.9% | 42.1% | 0.072 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_4h` | - | `next_3_bars` | 18,572 | `break` | 25.1% | 42.2% | 0.072 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwl_4h` | - | `next_3_bars` | 3,901 | `break` | 22.9% | 40.8% | 0.071 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdl_1h` | - | `next_3_bars` | 17,832 | `break` | 24.1% | 40.7% | 0.068 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwl_daily` | - | `next_3_bars` | 3,690 | `break` | 26.8% | 43.1% | 0.068 | `C` | `break_continuation_bias` |
| `kind_side` | `order_block` | - | `bearish` | `next_3_bars` | 100,646 | `break` | 25.0% | 39.9% | 0.060 | `C` | `break_continuation_bias` |
| `kind` | `order_block` | - | - | `next_3_bars` | 198,069 | `break` | 24.7% | 39.5% | 0.058 | `C` | `break_continuation_bias` |
| `kind_side` | `order_block` | - | `bullish` | `next_3_bars` | 97,423 | `break` | 24.4% | 39.0% | 0.057 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_ny_low_1h` | - | `next_3_bars` | 17,481 | `break` | 20.2% | 35.5% | 0.055 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_ny_high_1h` | - | `next_3_bars` | 18,076 | `break` | 20.5% | 35.3% | 0.052 | `C` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_london_low_1h` | - | `next_3_bars` | 18,697 | `break` | 27.2% | 38.9% | 0.045 | `D` | `mixed_or_weak` |
| `kind_subtype` | `order_block` | `swept_london_high_1h` | - | `next_3_bars` | 19,171 | `break` | 27.9% | 39.1% | 0.044 | `D` | `mixed_or_weak` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `next_3_bars` | 17,596 | `break` | 26.5% | 37.8% | 0.043 | `D` | `mixed_or_weak` |
| `kind_subtype` | `order_block` | `swept_asia_low_1h` | - | `next_3_bars` | 17,250 | `break` | 25.1% | 36.0% | 0.039 | `D` | `mixed_or_weak` |
| `kind_subtype` | `swing_pivot` | `pivot_3_4h` | - | `next_3_bars` | 51,376 | `break` | 5.8% | 16.4% | 0.018 | `D` | `mixed_or_weak` |
| `kind_subtype` | `swing_pivot` | `pivot_3_1h` | - | `next_3_bars` | 156,806 | `break` | 5.7% | 16.2% | 0.017 | `D` | `mixed_or_weak` |
| `kind_subtype` | `liquidity_sweep` | `pwl_daily` | - | `next_3_bars` | 4,505 | `rejection` | 58.4% | 55.6% | 0.016 | `D` | `mixed_or_weak` |

## Rejection Bias Leaders

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_5d` | 6,687 | `rejection` | 74.6% | 8.7% | 0.492 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_20d` | 6,687 | `rejection` | 74.6% | 8.7% | 0.492 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `full_horizon` | 6,687 | `rejection` | 74.6% | 8.7% | 0.492 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_1d` | 6,687 | `rejection` | 74.5% | 8.7% | 0.491 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_240m` | 6,687 | `rejection` | 72.6% | 8.6% | 0.464 | `A` | `rejection_bias` |
| `kind_subtype` | `opening_gap` | `nwog` | - | `next_60m` | 6,687 | `rejection` | 69.1% | 8.6% | 0.419 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `next_5d` | 18,870 | `rejection` | 64.7% | 10.3% | 0.352 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `full_horizon` | 18,870 | `rejection` | 64.7% | 10.3% | 0.352 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `next_20d` | 18,870 | `rejection` | 64.7% | 10.3% | 0.352 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `next_1d` | 18,870 | `rejection` | 64.7% | 10.3% | 0.351 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `full_horizon` | 36,944 | `rejection` | 64.1% | 10.4% | 0.345 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_5d` | 36,944 | `rejection` | 64.1% | 10.4% | 0.345 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_20d` | 36,944 | `rejection` | 64.1% | 10.4% | 0.345 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_1d` | 36,944 | `rejection` | 64.1% | 10.4% | 0.344 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `full_horizon` | 18,074 | `rejection` | 63.6% | 10.4% | 0.338 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_20d` | 18,074 | `rejection` | 63.6% | 10.4% | 0.338 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_5d` | 18,074 | `rejection` | 63.6% | 10.4% | 0.338 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_down` | `next_1d` | 18,074 | `rejection` | 63.5% | 10.4% | 0.337 | `A` | `rejection_bias` |
| `kind_side` | `opening_gap` | - | `gap_up` | `next_240m` | 18,870 | `rejection` | 63.2% | 10.3% | 0.334 | `A` | `rejection_bias` |
| `kind` | `opening_gap` | - | - | `next_240m` | 36,944 | `rejection` | 62.5% | 10.4% | 0.326 | `A` | `rejection_bias` |

## Break / Continuation Bias Leaders

| Segment | Kind | Subtype | Side | Horizon | Rows | Dominant | Reject | Break | Score | Tier | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `full_horizon` | 13,268 | `break` | 3.6% | 82.3% | 0.647 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_3_1h_5pts` | - | `next_250_bars` | 13,268 | `break` | 3.6% | 82.3% | 0.647 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `full_horizon` | 17,596 | `break` | 11.4% | 84.4% | 0.616 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_high_1h` | - | `next_50_bars` | 17,596 | `break` | 11.4% | 84.4% | 0.616 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `full_horizon` | 19,237 | `break` | 12.6% | 83.5% | 0.592 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_4h` | - | `next_50_bars` | 19,237 | `break` | 12.6% | 83.5% | 0.592 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `full_horizon` | 3,899 | `break` | 12.3% | 84.4% | 0.591 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_daily` | - | `next_50_bars` | 3,899 | `break` | 12.3% | 84.4% | 0.591 | `A` | `break_continuation_bias` |
| `kind_side` | `equal_levels` | - | `high` | `full_horizon` | 31,735 | `break` | 2.6% | 78.2% | 0.591 | `A` | `break_continuation_bias` |
| `kind_side` | `equal_levels` | - | `high` | `next_250_bars` | 31,735 | `break` | 2.6% | 78.2% | 0.591 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `full_horizon` | 4,158 | `break` | 12.7% | 84.0% | 0.586 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pwh_4h` | - | `next_50_bars` | 4,158 | `break` | 12.7% | 84.0% | 0.586 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_5_1h_5pts` | - | `full_horizon` | 7,115 | `break` | 3.6% | 78.2% | 0.584 | `A` | `break_continuation_bias` |
| `kind_subtype` | `equal_levels` | `eq_pivot_5_1h_5pts` | - | `next_250_bars` | 7,115 | `break` | 3.6% | 78.2% | 0.584 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_low_1h` | - | `full_horizon` | 17,250 | `break` | 12.5% | 82.5% | 0.577 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_asia_low_1h` | - | `next_50_bars` | 17,250 | `break` | 12.5% | 82.5% | 0.577 | `A` | `break_continuation_bias` |
| `kind_side` | `order_block` | - | `bearish` | `next_50_bars` | 100,646 | `break` | 13.2% | 81.6% | 0.557 | `A` | `break_continuation_bias` |
| `kind_side` | `order_block` | - | `bearish` | `full_horizon` | 100,646 | `break` | 13.2% | 81.6% | 0.557 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `next_50_bars` | 18,509 | `break` | 13.7% | 81.8% | 0.556 | `A` | `break_continuation_bias` |
| `kind_subtype` | `order_block` | `swept_pdh_1h` | - | `full_horizon` | 18,509 | `break` | 13.7% | 81.8% | 0.556 | `A` | `break_continuation_bias` |

## Notes

- This is an outcome/label leaderboard, not a trading system.
- The markdown report hides `kind_subtype_side` duplicates; the CSV/parquet keep every segment.
- `rejection_bias` means rejection dominates break behavior for that segment/horizon.
- `break_continuation_bias` means break/continuation dominates rejection behavior.
- Opening gaps use clock-time horizons; FVG, OB, sweep, and swing use native-bar horizons.
- Equal levels use 1h native-bar take/reaction horizons.
- Use short-horizon rows for cleaner behavior comparisons; full horizon can become too broad.
- `lr.*` columns remain future outcomes and must not be used as model inputs unless selecting targets.
