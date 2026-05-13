# Database coverage audit

_Generated `2026-05-10T21:37:14.223282+00:00`._

**Total events:** 603,127

**With outcomes (any):** 603,127 (100.0%)

**JSON-null bug rows:** 9

**Real outcomes:** 195,842 (32.5%)

## Per detector × event_type

| feature | event_type | n_total | n_real | json_null | pct_real | status |
|---|---|---|---|---|---|---|
| displacement_candle | 1h_disp | 29,664 | 29,664 | 0 | 100.0% | OK |
| displacement_candle | 4h_disp | 7,471 | 7,471 | 0 | 100.0% | OK |
| displacement_candle | daily_disp | 1,612 | 1,612 | 0 | 100.0% | OK |
| equal_levels | eq_pivot_3_1h_15pts | 21,077 | 21,077 | 0 | 100.0% | OK |
| equal_levels | eq_pivot_3_1h_5pts | 12,975 | 12,975 | 0 | 100.0% | OK |
| equal_levels | eq_pivot_3_4h_15pts | 4,681 | 4,681 | 0 | 100.0% | OK |
| equal_levels | eq_pivot_5_1h_15pts | 11,850 | 11,850 | 0 | 100.0% | OK |
| equal_levels | eq_pivot_5_1h_5pts | 6,876 | 6,876 | 0 | 100.0% | OK |
| equal_levels | eq_pivot_5_4h_15pts | 2,504 | 2,504 | 0 | 100.0% | OK |
| equal_levels | eq_pivot_5_daily_30pts | 375 | 375 | 0 | 100.0% | OK |
| first_third_range | first_third_daily | 8,630 | 8,621 | 9 | 99.9% | OK |
| first_third_range | first_third_weekly | 1,743 | 1,743 | 0 | 100.0% | OK |
| fvg_formation | 15m_fvg | 154,461 | 154,228 | 233 | 99.8% | OK |
| fvg_formation | 1h_fvg | 40,207 | 40,206 | 1 | 100.0% | OK |
| fvg_formation | 4h_fvg | 11,883 | 11,879 | 4 | 100.0% | OK |
| fvg_formation | daily_fvg | 2,788 | 2,785 | 3 | 99.9% | OK |
| liquidity_sweep | asia_high_1h | 4,619 | 4,619 | 0 | 100.0% | OK |
| liquidity_sweep | asia_low_1h | 3,816 | 3,813 | 3 | 99.9% | OK |
| liquidity_sweep | london_high_1h | 4,972 | 4,972 | 0 | 100.0% | OK |
| liquidity_sweep | london_low_1h | 4,029 | 4,029 | 0 | 100.0% | OK |
| liquidity_sweep | ny_high_1h | 4,286 | 4,286 | 0 | 100.0% | OK |
| liquidity_sweep | ny_low_1h | 3,452 | 3,452 | 0 | 100.0% | OK |
| liquidity_sweep | pdh_1h | 6,416 | 6,416 | 0 | 100.0% | OK |
| liquidity_sweep | pdh_4h | 6,417 | 6,417 | 0 | 100.0% | OK |
| liquidity_sweep | pdl_1h | 5,604 | 5,601 | 3 | 99.9% | OK |
| liquidity_sweep | pdl_4h | 5,591 | 5,591 | 0 | 100.0% | OK |
| liquidity_sweep | pwh_4h | 1,112 | 1,112 | 0 | 100.0% | OK |
| liquidity_sweep | pwh_daily | 1,112 | 1,112 | 0 | 100.0% | OK |
| liquidity_sweep | pwl_4h | 760 | 760 | 0 | 100.0% | OK |
| liquidity_sweep | pwl_daily | 760 | 760 | 0 | 100.0% | OK |
| opening_range_breakout | asia_60m | 8,618 | 8,614 | 4 | 100.0% | OK |
| opening_range_breakout | ny_15m | 8,474 | 8,468 | 6 | 99.9% | OK |
| opening_range_breakout | ny_30m | 8,474 | 8,471 | 3 | 100.0% | OK |
| opening_range_breakout | ny_5m | 8,474 | 8,468 | 6 | 99.9% | OK |
| order_block | swept_asia_high_1h | 4,017 | 4,017 | 0 | 100.0% | OK |
| order_block | swept_asia_low_1h | 3,332 | 3,332 | 0 | 100.0% | OK |
| order_block | swept_london_high_1h | 4,512 | 4,512 | 0 | 100.0% | OK |
| order_block | swept_london_low_1h | 3,739 | 3,739 | 0 | 100.0% | OK |
| order_block | swept_ny_high_1h | 3,626 | 3,626 | 0 | 100.0% | OK |
| order_block | swept_ny_low_1h | 3,108 | 3,108 | 0 | 100.0% | OK |
| order_block | swept_pdh_1h | 5,541 | 5,541 | 0 | 100.0% | OK |
| order_block | swept_pdh_4h | 5,497 | 5,497 | 0 | 100.0% | OK |
| order_block | swept_pdl_1h | 4,908 | 4,908 | 0 | 100.0% | OK |
| order_block | swept_pdl_4h | 5,008 | 5,008 | 0 | 100.0% | OK |
| order_block | swept_pwh_4h | 917 | 917 | 0 | 100.0% | OK |
| order_block | swept_pwh_daily | 856 | 856 | 0 | 100.0% | OK |
| order_block | swept_pwl_4h | 647 | 647 | 0 | 100.0% | OK |
| order_block | swept_pwl_daily | 623 | 623 | 0 | 100.0% | OK |
| psp_candle_divergence | 1h_psp | 11,641 | 11,513 | 128 | 98.9% | JSON_NULL |
| psp_candle_divergence | 4h_psp | 3,373 | 3,368 | 5 | 99.9% | OK |
| psp_candle_divergence | daily_psp | 813 | 813 | 0 | 100.0% | OK |
| smt_htf_reference_divergence | previous_day_smt | 2,360 | 2,360 | 0 | 100.0% | OK |
| smt_htf_reference_divergence | weekly_smt | 531 | 531 | 0 | 100.0% | OK |
| swing_pivot | pivot_3_1h | 35,920 | 35,919 | 1 | 100.0% | OK |
| swing_pivot | pivot_3_4h | 10,691 | 10,689 | 2 | 100.0% | OK |
| swing_pivot | pivot_5_1h | 22,424 | 22,424 | 0 | 100.0% | OK |
| swing_pivot | pivot_5_4h | 6,585 | 6,581 | 4 | 99.9% | OK |
| swing_pivot | pivot_5_daily | 1,166 | 1,166 | 0 | 100.0% | OK |
| time_profile | daily_3session | 8,630 | 8,621 | 9 | 99.9% | OK |
| time_profile | daily_4session | 8,630 | 8,621 | 9 | 99.9% | OK |
| time_profile | monthly | 405 | 399 | 6 | 98.5% | JSON_NULL |
| time_profile | weekly | 1,749 | 1,740 | 9 | 99.5% | JSON_NULL |
| volume_profile | asia_volume_profile | 8,630 | 8,624 | 6 | 99.9% | OK |
| volume_profile | daily_volume_profile | 8,630 | 8,536 | 94 | 98.9% | JSON_NULL |
| volume_profile | london_volume_profile | 8,615 | 8,474 | 141 | 98.4% | JSON_NULL |
| volume_profile | ny_volume_profile | 8,471 | 6,976 | 1,495 | 82.4% | JSON_NULL |
| volume_profile | weekly_volume_profile | 1,749 | 1,740 | 9 | 99.5% | JSON_NULL |

## Issues

- psp_candle_divergence/1h_psp: 128 JSON-null outcomes
- time_profile/monthly: 6 JSON-null outcomes
- time_profile/weekly: 9 JSON-null outcomes
- volume_profile/daily_volume_profile: 94 JSON-null outcomes
- volume_profile/london_volume_profile: 141 JSON-null outcomes
- volume_profile/ny_volume_profile: 1495 JSON-null outcomes
- volume_profile/weekly_volume_profile: 9 JSON-null outcomes
