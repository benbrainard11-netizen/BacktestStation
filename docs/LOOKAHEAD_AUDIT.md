# Look-ahead audit

_Generated `2026-05-17T06:29:59.295412+00:00`._

Verifies that outcomes were computed only from bars at or after `event.bar_end_utc + bucket_minutes` (the detector confirmation lag).

Sampled up to 500 events per (feature × event_type) class. 188 classes audited.

## Per-class summary

| feature | event_type | sampled | violations | pct | event_data_flags | status |
|---|---|---|---|---|---|---|
| displacement_candle | 1h_disp | 500 | 0 | 0.0% | 0 | OK |
| displacement_candle | 4h_disp | 500 | 0 | 0.0% | 0 | OK |
| displacement_candle | daily_disp | 500 | 0 | 0.0% | 0 | OK |
| equal_levels | eq_pivot_3_1h_15pts | 500 | 0 | 0.0% | 0 | OK |
| equal_levels | eq_pivot_3_1h_5pts | 500 | 0 | 0.0% | 0 | OK |
| equal_levels | eq_pivot_3_4h_15pts | 500 | 0 | 0.0% | 0 | OK |
| equal_levels | eq_pivot_5_1h_15pts | 500 | 0 | 0.0% | 0 | OK |
| equal_levels | eq_pivot_5_1h_5pts | 500 | 0 | 0.0% | 0 | OK |
| equal_levels | eq_pivot_5_4h_15pts | 500 | 0 | 0.0% | 0 | OK |
| equal_levels | eq_pivot_5_daily_30pts | 375 | 0 | 0.0% | 0 | OK |
| first_third_range | first_third_daily | 500 | 0 | 0.0% | 0 | OK |
| first_third_range | first_third_weekly | 500 | 0 | 0.0% | 0 | OK |
| forming_volume_profile | daily_vp_asof_4h | 500 | 0 | 0.0% | 0 | OK |
| fvg_formation | 15m_fvg | 500 | 0 | 0.0% | 0 | OK |
| fvg_formation | 1h_fvg | 500 | 0 | 0.0% | 0 | OK |
| fvg_formation | 4h_fvg | 500 | 0 | 0.0% | 0 | OK |
| fvg_formation | daily_fvg | 500 | 0 | 0.0% | 0 | OK |
| interval_true_range | asia_itr | 500 | 0 | 0.0% | 0 | OK |
| interval_true_range | daily_itr | 500 | 0 | 0.0% | 0 | OK |
| interval_true_range | london_itr | 500 | 0 | 0.0% | 0 | OK |
| interval_true_range | ny_itr | 500 | 0 | 0.0% | 0 | OK |
| interval_true_range | weekly_itr | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | asia_high_1h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | asia_low_1h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | london_high_1h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | london_low_1h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | ny_high_1h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | ny_low_1h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pdh_1h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pdh_4h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pdl_1h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pdl_4h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pwh_4h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pwh_daily | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pwl_4h | 500 | 0 | 0.0% | 0 | OK |
| liquidity_sweep | pwl_daily | 500 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_10_y_bond_auction | 117 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_30_y_bond_auction | 90 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_adp_non_farm_employment_change | 366 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_advance_gdp_price_index_q_q | 123 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_advance_gdp_q_q | 123 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_average_hourly_earnings_m_m | 363 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_average_hourly_earnings_mom | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_bank_stress_test_results | 15 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_building_permits | 246 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_business_inventories_m_m | 21 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_capacity_utilization_rate | 129 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_cb_consumer_confidence | 366 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_cb_leading_index_m_m | 18 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_chicago_pmi | 311 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_congressional_elections | 12 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_core_cpi_m_m | 363 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_core_cpi_mom | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_core_durable_goods_orders_m_m | 330 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_core_pce_price_index_m_m | 314 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_core_ppi_m_m | 351 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_core_retail_sales_m_m | 360 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_cpi_m_m | 369 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_cpi_mom | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_cpi_y_y | 369 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_cpi_yoy | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_crude_oil_inventories | 500 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_current_account | 42 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_durable_goods_orders_m_m | 297 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_empire_state_manufacturing_index | 189 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_employment_cost_index_q_q | 87 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_existing_home_sales | 237 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_factory_orders_m_m | 102 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fed_announcement | 36 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fed_chair_powell_speaks | 312 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fed_chair_powell_testifies | 141 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fed_chair_yellen_speaks | 102 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fed_chair_yellen_testifies | 51 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fed_monetary_policy_report | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_federal_funds_rate | 246 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_final_gdp_price_index_q_q | 27 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_final_gdp_q_q | 120 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_final_manufacturing_pmi | 33 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_final_services_pmi | 42 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_flash_manufacturing_pmi | 222 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_flash_services_pmi | 117 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_economic_projections | 120 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_meeting_minutes | 246 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_barkin_speaks | 54 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_bostic_speaks | 123 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_bowman_speaks | 39 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_brainard_speaks | 189 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_bullard_speaks | 183 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_clarida_speaks | 87 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_collins_speaks | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_daly_speaks | 12 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_dudley_speaks | 195 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_evans_speaks | 159 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_fischer_speaks | 102 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_george_speaks | 72 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_goolsbee_speaks | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_harker_speaks | 117 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_kaplan_speaks | 87 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_kashkari_speaks | 72 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_kugler_speaks | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_lacker_speaks | 21 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_lockhart_speaks | 63 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_mester_speaks | 144 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_powell_speaks | 81 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_quarles_speaks | 111 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_rosengren_speaks | 42 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_tarullo_speaks | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_waller_speaks | 168 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_member_williams_speaks | 204 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_press_conference | 201 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_fomc_statement | 246 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_goods_trade_balance | 24 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_housing_starts | 144 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_import_prices_m_m | 114 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_industrial_production_m_m | 201 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_ism_manufacturing_pmi | 369 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_ism_manufacturing_prices | 42 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_ism_services_pmi | 360 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_jolts_job_openings | 240 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_mortgage_delinquencies | 42 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_nahb_housing_market_index | 15 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_new_home_sales | 207 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_nfp | 3 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_non_farm_employment_change | 363 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_pending_home_sales_m_m | 273 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_personal_spending_m_m | 146 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_philly_fed_manufacturing_index | 363 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_ppi_m_m | 351 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_prelim_gdp_price_index_q_q | 24 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_prelim_gdp_q_q | 120 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_prelim_nonfarm_productivity_q_q | 42 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_prelim_unit_labor_costs_q_q | 42 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_prelim_uom_consumer_sentiment | 321 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_prelim_uom_inflation_expectations | 90 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_president_biden_speaks | 18 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_president_trump_speaks | 264 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_presidential_election | 9 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_retail_sales_m_m | 348 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_revised_nonfarm_productivity_q_q | 30 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_revised_uom_consumer_sentiment | 315 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_richmond_manufacturing_index | 120 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_s_and_p_cs_composite_20_hpi_y_y | 57 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_trade_balance | 102 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_treasury_currency_report | 48 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_treasury_sec_lew_speaks | 15 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_treasury_sec_mnuchin_speaks | 24 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_treasury_sec_yellen_speaks | 81 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_unemployment_claims | 500 | 0 | 0.0% | 0 | OK |
| macro_event_anchor | pre_unemployment_rate | 366 | 0 | 0.0% | 0 | OK |
| opening_gap_levels | ndog | 500 | 0 | 0.0% | 0 | OK |
| opening_gap_levels | nwog | 500 | 0 | 0.0% | 0 | OK |
| opening_range_breakout | asia_60m | 500 | 0 | 0.0% | 0 | OK |
| opening_range_breakout | ny_15m | 500 | 0 | 0.0% | 0 | OK |
| opening_range_breakout | ny_30m | 500 | 0 | 0.0% | 0 | OK |
| opening_range_breakout | ny_5m | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_asia_high_1h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_asia_low_1h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_london_high_1h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_london_low_1h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_ny_high_1h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_ny_low_1h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_pdh_1h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_pdh_4h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_pdl_1h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_pdl_4h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_pwh_4h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_pwh_daily | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_pwl_4h | 500 | 0 | 0.0% | 0 | OK |
| order_block | swept_pwl_daily | 500 | 0 | 0.0% | 0 | OK |
| psp_candle_divergence | 1h_psp | 500 | 0 | 0.0% | 0 | OK |
| psp_candle_divergence | 4h_psp | 500 | 0 | 0.0% | 0 | OK |
| psp_candle_divergence | daily_psp | 500 | 0 | 0.0% | 0 | OK |
| smt_htf_reference_divergence | previous_day_smt | 500 | 0 | 0.0% | 500 | OK |
| smt_htf_reference_divergence | weekly_smt | 500 | 0 | 0.0% | 500 | OK |
| swing_pivot | pivot_3_1h | 500 | 0 | 0.0% | 0 | OK |
| swing_pivot | pivot_3_4h | 500 | 0 | 0.0% | 0 | OK |
| swing_pivot | pivot_5_1h | 500 | 0 | 0.0% | 0 | OK |
| swing_pivot | pivot_5_4h | 500 | 0 | 0.0% | 0 | OK |
| swing_pivot | pivot_5_daily | 500 | 0 | 0.0% | 0 | OK |
| time_profile | daily_3session | 500 | 0 | 0.0% | 0 | OK |
| time_profile | daily_4session | 500 | 0 | 0.0% | 0 | OK |
| time_profile | monthly | 399 | 0 | 0.0% | 0 | OK |
| time_profile | weekly | 500 | 0 | 0.0% | 0 | OK |
| volume_profile | asia_volume_profile | 500 | 0 | 0.0% | 0 | OK |
| volume_profile | daily_volume_profile | 500 | 0 | 0.0% | 0 | OK |
| volume_profile | london_volume_profile | 500 | 0 | 0.0% | 0 | OK |
| volume_profile | ny_volume_profile | 500 | 0 | 0.0% | 0 | OK |
| volume_profile | weekly_volume_profile | 500 | 0 | 0.0% | 0 | OK |

## Status

CLEAN — no look-ahead violations.

## Event Data Warnings

Soft warnings for event_data fields documented as filled after event fire. These fields can remain in the research event store but should not be used as event-time ML features.

- smt_htf_reference_divergence/previous_day_smt: 500/500 sampled events contain post-fire event_data fields. First: smt_htf_reference_divergence/previous_day_smt: event_data has post-fire field(s), first=did_all_confirm_by_window_end
- smt_htf_reference_divergence/weekly_smt: 500/500 sampled events contain post-fire event_data fields. First: smt_htf_reference_divergence/weekly_smt: event_data has post-fire field(s), first=did_all_confirm_by_window_end
