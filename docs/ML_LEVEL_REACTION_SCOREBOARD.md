# Level Reaction Scoreboard

_Generated `2026-05-17T13:32:06.176119+00:00`._

This is the plain-English ranking layer on top of `level_reaction_leaderboard.csv`.
It ranks behavior clarity, not trade PnL.

- Source: `C:\Users\benbr\BacktestStation\data\ml\levels\level_reaction_leaderboard.csv`
- Minimum rows: `500`
- Ranked rows: `539`

## Best Families

| Kind | Best score | Best horizon | Best behavior | Median score |
|---|---|---|---|---|
| `order_block` | 0.689 | `next_50_bars` | `break` | 0.303 |
| `equal_levels` | 0.681 | `next_250_bars` | `break` | 0.221 |
| `swing_pivot` | 0.550 | `next_50_bars` | `break` | 0.136 |
| `opening_gap` | 0.450 | `next_60m` | `rejection` | 0.335 |
| `fair_value_gap` | 0.357 | `next_50_bars` | `break` | 0.139 |
| `liquidity_sweep` | 0.114 | `next_50_bars` | `rejection` | 0.032 |

## Top Overall

| Rank | Kind | Subtype | Side | Horizon | Rows | Dominant | Touch | Reject | Break | Score | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `order_block` | `swept_pdh_4h` | - | `next_50_bars` | 5,497 | `break` | 97.1% | 9.7% | 88.0% | 0.689 | `break_continuation_bias` |
| 2 | `order_block` | `swept_pdh_4h` | - | `full_horizon` | 5,497 | `break` | 97.1% | 9.7% | 88.0% | 0.689 | `break_continuation_bias` |
| 3 | `order_block` | `swept_pdh_4h` | `bearish` | `next_50_bars` | 5,497 | `break` | 97.1% | 9.7% | 88.0% | 0.689 | `break_continuation_bias` |
| 4 | `order_block` | `swept_pdh_4h` | `bearish` | `full_horizon` | 5,497 | `break` | 97.1% | 9.7% | 88.0% | 0.689 | `break_continuation_bias` |
| 5 | `equal_levels` | `eq_pivot_3_1h_5pts` | `high` | `next_250_bars` | 6,835 | `break` | 89.3% | 2.9% | 84.0% | 0.681 | `break_continuation_bias` |
| 6 | `equal_levels` | `eq_pivot_3_1h_5pts` | `high` | `full_horizon` | 6,835 | `break` | 89.3% | 2.9% | 84.0% | 0.681 | `break_continuation_bias` |
| 7 | `order_block` | `swept_asia_high_1h` | - | `next_50_bars` | 4,017 | `break` | 96.6% | 10.1% | 86.9% | 0.650 | `break_continuation_bias` |
| 8 | `order_block` | `swept_asia_high_1h` | - | `full_horizon` | 4,017 | `break` | 96.6% | 10.1% | 86.9% | 0.650 | `break_continuation_bias` |
| 9 | `order_block` | `swept_asia_high_1h` | `bearish` | `next_50_bars` | 4,017 | `break` | 96.6% | 10.1% | 86.9% | 0.650 | `break_continuation_bias` |
| 10 | `order_block` | `swept_asia_high_1h` | `bearish` | `full_horizon` | 4,017 | `break` | 96.6% | 10.1% | 86.9% | 0.650 | `break_continuation_bias` |
| 11 | `order_block` | `swept_pdh_1h` | - | `next_50_bars` | 5,541 | `break` | 95.8% | 11.1% | 85.2% | 0.632 | `break_continuation_bias` |
| 12 | `order_block` | `swept_pdh_1h` | - | `full_horizon` | 5,541 | `break` | 95.8% | 11.1% | 85.2% | 0.632 | `break_continuation_bias` |
| 13 | `order_block` | `swept_pdh_1h` | `bearish` | `next_50_bars` | 5,541 | `break` | 95.8% | 11.1% | 85.2% | 0.632 | `break_continuation_bias` |
| 14 | `order_block` | `swept_pdh_1h` | `bearish` | `full_horizon` | 5,541 | `break` | 95.8% | 11.1% | 85.2% | 0.632 | `break_continuation_bias` |
| 15 | `order_block` | `swept_pwh_daily` | - | `next_50_bars` | 856 | `break` | 97.3% | 6.0% | 91.6% | 0.622 | `break_continuation_bias` |
| 16 | `order_block` | `swept_pwh_daily` | - | `full_horizon` | 856 | `break` | 97.3% | 6.0% | 91.6% | 0.622 | `break_continuation_bias` |
| 17 | `order_block` | `swept_pwh_daily` | `bearish` | `next_50_bars` | 856 | `break` | 97.3% | 6.0% | 91.6% | 0.622 | `break_continuation_bias` |
| 18 | `order_block` | `swept_pwh_daily` | `bearish` | `full_horizon` | 856 | `break` | 97.3% | 6.0% | 91.6% | 0.622 | `break_continuation_bias` |
| 19 | `order_block` | - | `bearish` | `next_50_bars` | 24,966 | `break` | 95.2% | 11.5% | 84.1% | 0.611 | `break_continuation_bias` |
| 20 | `order_block` | - | `bearish` | `full_horizon` | 24,966 | `break` | 95.2% | 11.5% | 84.1% | 0.611 | `break_continuation_bias` |

## Top Rejection

| Rank | Kind | Subtype | Side | Horizon | Rows | Dominant | Touch | Reject | Break | Score | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 66 | `opening_gap` | `nwog` | - | `next_60m` | 1,623 | `rejection` | 62.3% | 77.6% | 10.9% | 0.450 | `rejection_bias` |
| 67 | `opening_gap` | `nwog` | - | `next_240m` | 1,623 | `rejection` | 70.5% | 77.6% | 10.9% | 0.450 | `rejection_bias` |
| 68 | `opening_gap` | `nwog` | - | `next_1d` | 1,623 | `rejection` | 86.6% | 77.6% | 10.9% | 0.450 | `rejection_bias` |
| 69 | `opening_gap` | `nwog` | - | `next_5d` | 1,623 | `rejection` | 93.7% | 77.6% | 10.9% | 0.450 | `rejection_bias` |
| 70 | `opening_gap` | `nwog` | - | `next_20d` | 1,623 | `rejection` | 97.1% | 77.6% | 10.9% | 0.450 | `rejection_bias` |
| 71 | `opening_gap` | `nwog` | - | `full_horizon` | 1,623 | `rejection` | 97.1% | 77.6% | 10.9% | 0.450 | `rejection_bias` |
| 76 | `opening_gap` | `nwog` | `gap_up` | `next_60m` | 860 | `rejection` | 61.7% | 79.4% | 8.7% | 0.445 | `rejection_bias` |
| 77 | `opening_gap` | `nwog` | `gap_up` | `next_240m` | 860 | `rejection` | 69.5% | 79.4% | 8.7% | 0.445 | `rejection_bias` |
| 78 | `opening_gap` | `nwog` | `gap_up` | `next_1d` | 860 | `rejection` | 84.0% | 79.4% | 8.7% | 0.445 | `rejection_bias` |
| 79 | `opening_gap` | `nwog` | `gap_up` | `next_5d` | 860 | `rejection` | 91.9% | 79.4% | 8.7% | 0.445 | `rejection_bias` |
| 80 | `opening_gap` | `nwog` | `gap_up` | `next_20d` | 860 | `rejection` | 96.0% | 79.4% | 8.7% | 0.445 | `rejection_bias` |
| 81 | `opening_gap` | `nwog` | `gap_up` | `full_horizon` | 860 | `rejection` | 96.0% | 79.4% | 8.7% | 0.445 | `rejection_bias` |
| 109 | `opening_gap` | `nwog` | `gap_down` | `next_60m` | 763 | `rejection` | 62.9% | 75.6% | 13.4% | 0.367 | `rejection_bias` |
| 110 | `opening_gap` | `nwog` | `gap_down` | `next_240m` | 763 | `rejection` | 71.6% | 75.6% | 13.4% | 0.367 | `rejection_bias` |
| 111 | `opening_gap` | `nwog` | `gap_down` | `next_1d` | 763 | `rejection` | 89.6% | 75.6% | 13.4% | 0.367 | `rejection_bias` |
| 112 | `opening_gap` | `nwog` | `gap_down` | `next_5d` | 763 | `rejection` | 95.7% | 75.6% | 13.4% | 0.367 | `rejection_bias` |
| 113 | `opening_gap` | `nwog` | `gap_down` | `next_20d` | 763 | `rejection` | 98.3% | 75.6% | 13.4% | 0.367 | `rejection_bias` |
| 114 | `opening_gap` | `nwog` | `gap_down` | `full_horizon` | 763 | `rejection` | 98.3% | 75.6% | 13.4% | 0.367 | `rejection_bias` |
| 124 | `opening_gap` | - | `gap_down` | `next_60m` | 4,873 | `rejection` | 79.1% | 67.4% | 15.0% | 0.352 | `rejection_bias` |
| 125 | `opening_gap` | - | `gap_down` | `next_240m` | 4,873 | `rejection` | 86.6% | 67.4% | 15.0% | 0.352 | `rejection_bias` |

## Top Break / Continuation

| Rank | Kind | Subtype | Side | Horizon | Rows | Dominant | Touch | Reject | Break | Score | Hint |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `order_block` | `swept_pdh_4h` | - | `next_50_bars` | 5,497 | `break` | 97.1% | 9.7% | 88.0% | 0.689 | `break_continuation_bias` |
| 2 | `order_block` | `swept_pdh_4h` | - | `full_horizon` | 5,497 | `break` | 97.1% | 9.7% | 88.0% | 0.689 | `break_continuation_bias` |
| 3 | `order_block` | `swept_pdh_4h` | `bearish` | `next_50_bars` | 5,497 | `break` | 97.1% | 9.7% | 88.0% | 0.689 | `break_continuation_bias` |
| 4 | `order_block` | `swept_pdh_4h` | `bearish` | `full_horizon` | 5,497 | `break` | 97.1% | 9.7% | 88.0% | 0.689 | `break_continuation_bias` |
| 5 | `equal_levels` | `eq_pivot_3_1h_5pts` | `high` | `next_250_bars` | 6,835 | `break` | 89.3% | 2.9% | 84.0% | 0.681 | `break_continuation_bias` |
| 6 | `equal_levels` | `eq_pivot_3_1h_5pts` | `high` | `full_horizon` | 6,835 | `break` | 89.3% | 2.9% | 84.0% | 0.681 | `break_continuation_bias` |
| 7 | `order_block` | `swept_asia_high_1h` | - | `next_50_bars` | 4,017 | `break` | 96.6% | 10.1% | 86.9% | 0.650 | `break_continuation_bias` |
| 8 | `order_block` | `swept_asia_high_1h` | - | `full_horizon` | 4,017 | `break` | 96.6% | 10.1% | 86.9% | 0.650 | `break_continuation_bias` |
| 9 | `order_block` | `swept_asia_high_1h` | `bearish` | `next_50_bars` | 4,017 | `break` | 96.6% | 10.1% | 86.9% | 0.650 | `break_continuation_bias` |
| 10 | `order_block` | `swept_asia_high_1h` | `bearish` | `full_horizon` | 4,017 | `break` | 96.6% | 10.1% | 86.9% | 0.650 | `break_continuation_bias` |
| 11 | `order_block` | `swept_pdh_1h` | - | `next_50_bars` | 5,541 | `break` | 95.8% | 11.1% | 85.2% | 0.632 | `break_continuation_bias` |
| 12 | `order_block` | `swept_pdh_1h` | - | `full_horizon` | 5,541 | `break` | 95.8% | 11.1% | 85.2% | 0.632 | `break_continuation_bias` |
| 13 | `order_block` | `swept_pdh_1h` | `bearish` | `next_50_bars` | 5,541 | `break` | 95.8% | 11.1% | 85.2% | 0.632 | `break_continuation_bias` |
| 14 | `order_block` | `swept_pdh_1h` | `bearish` | `full_horizon` | 5,541 | `break` | 95.8% | 11.1% | 85.2% | 0.632 | `break_continuation_bias` |
| 15 | `order_block` | `swept_pwh_daily` | - | `next_50_bars` | 856 | `break` | 97.3% | 6.0% | 91.6% | 0.622 | `break_continuation_bias` |
| 16 | `order_block` | `swept_pwh_daily` | - | `full_horizon` | 856 | `break` | 97.3% | 6.0% | 91.6% | 0.622 | `break_continuation_bias` |
| 17 | `order_block` | `swept_pwh_daily` | `bearish` | `next_50_bars` | 856 | `break` | 97.3% | 6.0% | 91.6% | 0.622 | `break_continuation_bias` |
| 18 | `order_block` | `swept_pwh_daily` | `bearish` | `full_horizon` | 856 | `break` | 97.3% | 6.0% | 91.6% | 0.622 | `break_continuation_bias` |
| 19 | `order_block` | - | `bearish` | `next_50_bars` | 24,966 | `break` | 95.2% | 11.5% | 84.1% | 0.611 | `break_continuation_bias` |
| 20 | `order_block` | - | `bearish` | `full_horizon` | 24,966 | `break` | 95.2% | 11.5% | 84.1% | 0.611 | `break_continuation_bias` |

## Practical Read

- High `break` rows mean the level is usually not support/resistance; it is often a draw-through or continuation area.
- High `rejection` rows mean the level more often acts as support/resistance.
- `full_horizon` can overstate usefulness because it gives price more time; short horizons are cleaner for execution research.
