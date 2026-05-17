# Look-ahead audit

_Generated `2026-05-17T19:46:44.299589+00:00`._

Verifies that outcomes were computed only from bars at or after `event.bar_end_utc + bucket_minutes` (the detector confirmation lag).

Sampled up to 200 events per (feature × event_type) class. 69 classes audited.

## Per-class summary

| feature | event_type | sampled | violations | pct | event_data_flags | status |
|---|---|---|---|---|---|---|
| displacement_candle | 1h_disp | 200 | 0 | 0.0% | 0 | OK |
| displacement_candle | 4h_disp | 200 | 0 | 0.0% | 0 | OK |
| displacement_candle | daily_disp | 200 | 0 | 0.0% | 0 | OK |
| first_third_range | first_third_daily | 200 | 0 | 0.0% | 0 | OK |
| first_third_range | first_third_weekly | 200 | 0 | 0.0% | 0 | OK |
| forming_volume_profile | daily_vp_asof_1h | 200 | 0 | 0.0% | 0 | OK |
| forming_volume_profile | daily_vp_asof_4h | 200 | 0 | 0.0% | 0 | OK |
| fvg_formation | 15m_fvg | 200 | 0 | 0.0% | 0 | OK |
| fvg_formation | 1h_fvg | 200 | 0 | 0.0% | 0 | OK |
| fvg_formation | 4h_fvg | 200 | 0 | 0.0% | 0 | OK |
| fvg_formation | daily_fvg | 200 | 0 | 0.0% | 0 | OK |
| interval_true_range | asia_itr | 200 | 0 | 0.0% | 0 | OK |
| interval_true_range | daily_itr | 200 | 0 | 0.0% | 0 | OK |
| interval_true_range | london_itr | 200 | 0 | 0.0% | 0 | OK |
| interval_true_range | ny_itr | 200 | 0 | 0.0% | 0 | OK |
| interval_true_range | weekly_itr | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | asia_high_1h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | asia_low_1h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | london_high_1h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | london_low_1h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | ny_high_1h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | ny_low_1h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pdh_1h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pdh_4h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pdl_1h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pdl_4h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pwh_4h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pwh_daily | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pwl_4h | 200 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pwl_daily | 200 | 0 | 0.0% | 0 | OK |
| opening_gap_levels | ndog | 200 | 0 | 0.0% | 0 | OK |
| opening_gap_levels | nwog | 200 | 0 | 0.0% | 0 | OK |
| opening_range_breakout | asia_60m | 200 | 0 | 0.0% | 0 | OK |
| opening_range_breakout | ny_15m | 200 | 0 | 0.0% | 0 | OK |
| opening_range_breakout | ny_30m | 200 | 0 | 0.0% | 0 | OK |
| opening_range_breakout | ny_5m | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_asia_high_1h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_asia_low_1h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_london_high_1h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_london_low_1h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_ny_high_1h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_ny_low_1h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_pdh_1h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_pdh_4h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_pdl_1h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_pdl_4h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_pwh_4h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_pwh_daily | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_pwl_4h | 200 | 0 | 0.0% | 0 | OK |
| order_block | swept_pwl_daily | 200 | 0 | 0.0% | 0 | OK |
| psp_candle_divergence | 1h_psp | 200 | 0 | 0.0% | 0 | OK |
| psp_candle_divergence | 4h_psp | 200 | 0 | 0.0% | 0 | OK |
| psp_candle_divergence | daily_psp | 200 | 0 | 0.0% | 0 | OK |
| smt_htf_reference_divergence | previous_day_smt | 200 | 0 | 0.0% | 200 | OK |
| smt_htf_reference_divergence | weekly_smt | 200 | 0 | 0.0% | 200 | OK |
| swing_pivot | pivot_3_1h | 200 | 0 | 0.0% | 0 | OK |
| swing_pivot | pivot_3_4h | 200 | 0 | 0.0% | 0 | OK |
| swing_pivot | pivot_5_1h | 200 | 0 | 0.0% | 0 | OK |
| swing_pivot | pivot_5_4h | 200 | 0 | 0.0% | 0 | OK |
| swing_pivot | pivot_5_daily | 200 | 0 | 0.0% | 0 | OK |
| time_profile | daily_3session | 200 | 0 | 0.0% | 0 | OK |
| time_profile | daily_4session | 200 | 0 | 0.0% | 0 | OK |
| time_profile | monthly | 200 | 0 | 0.0% | 0 | OK |
| time_profile | weekly | 200 | 0 | 0.0% | 0 | OK |
| volume_profile | asia_volume_profile | 200 | 0 | 0.0% | 0 | OK |
| volume_profile | daily_volume_profile | 200 | 0 | 0.0% | 0 | OK |
| volume_profile | london_volume_profile | 200 | 0 | 0.0% | 0 | OK |
| volume_profile | ny_volume_profile | 200 | 0 | 0.0% | 0 | OK |
| volume_profile | weekly_volume_profile | 200 | 0 | 0.0% | 0 | OK |

## Status

CLEAN — no look-ahead violations.

## Event Data Warnings

Soft warnings for event_data fields documented as filled after event fire. These fields can remain in the research event store but should not be used as event-time ML features.

- smt_htf_reference_divergence/previous_day_smt: 200/200 sampled events contain post-fire event_data fields. First: smt_htf_reference_divergence/previous_day_smt: event_data has post-fire field(s), first=did_all_confirm_by_window_end
- smt_htf_reference_divergence/weekly_smt: 200/200 sampled events contain post-fire event_data fields. First: smt_htf_reference_divergence/weekly_smt: event_data has post-fire field(s), first=did_all_confirm_by_window_end
