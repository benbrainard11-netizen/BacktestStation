# Scheduled Macro Events - Current Stats

_Generated `2026-05-17T19:32:55+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Scheduled economic-calendar release anchors and post-release reaction labels.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `macro` / `macro_event_anchor` |
| Total feature rows | 18,414 |
| Date range | 2015-01-02 -> 2026-05-12 |
| Outcomes coverage | 18,414 / 18,414 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `pre_unemployment_claims` | 1,320 | 7.2% |
| `pre_crude_oil_inventories` | 993 | 5.4% |
| `pre_ism_manufacturing_pmi` | 369 | 2.0% |
| `pre_cpi_y_y` | 369 | 2.0% |
| `pre_cpi_m_m` | 369 | 2.0% |
| `pre_unemployment_rate` | 366 | 2.0% |
| `pre_cb_consumer_confidence` | 366 | 2.0% |
| `pre_adp_non_farm_employment_change` | 366 | 2.0% |
| `pre_philly_fed_manufacturing_index` | 363 | 2.0% |
| `pre_non_farm_employment_change` | 363 | 2.0% |
| `pre_core_cpi_m_m` | 363 | 2.0% |
| `pre_average_hourly_earnings_m_m` | 363 | 2.0% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v2` | 18,330 | 99.5% |
| `(missing)` | 84 | 0.5% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 6,139 | 33.3% |
| `ES.c.0` | 6,139 | 33.3% |
| `YM.c.0` | 6,136 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `high` | 9,303 | 50.5% |
| `medium` | 9,111 | 49.5% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 18,414 |
| Columns | 468 |
| ed.* event_data | 50 |
| oc.* outcome labels | 389 |
| ctx.* context | 5 |
| xd.* cross-detector | 15 |
| numeric | 420 |
| object/category | 47 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_5m.range_expanded_2x_pre_15m` | 998 / 18,160 | 5.5% |
| `oc.next_15m.range_expanded_2x_pre_60m` | 541 / 18,180 | 3.0% |
| `oc.next_15m.one_sided_took_pre_60m_high` | 5,225 / 18,180 | 28.7% |
| `oc.next_15m.one_sided_took_pre_60m_low` | 4,652 / 18,180 | 25.6% |
| `oc.next_15m.took_pre_60m_high_rejected_inside` | 2,734 / 18,180 | 15.0% |
| `oc.next_15m.took_pre_60m_low_rejected_inside` | 2,389 / 18,180 | 13.1% |
| `oc.next_60m.closed_inside_pre_60m_range` | 9,477 / 18,264 | 51.9% |

### Breakdown - `oc.next_5m.range_expanded_2x_pre_15m` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `pre_10_y_bond_auction` | 12 / 117 | 10.3% |
| `pre_30_y_bond_auction` | 3 / 90 | 3.3% |
| `pre_adp_non_farm_employment_change` | 30 / 366 | 8.2% |
| `pre_advance_gdp_price_index_q_q` | 3 / 123 | 2.4% |
| `pre_advance_gdp_q_q` | 28 / 123 | 22.8% |
| `pre_average_hourly_earnings_m_m` | 56 / 363 | 15.4% |
| `pre_average_hourly_earnings_mom` | 1 / 3 | 33.3% |
| `pre_bank_stress_test_results` | 0 / 15 | 0.0% |
| `pre_building_permits` | 9 / 246 | 3.7% |
| `pre_business_inventories_m_m` | 0 / 21 | 0.0% |
| `pre_capacity_utilization_rate` | 2 / 129 | 1.6% |
| `pre_cb_consumer_confidence` | 4 / 366 | 1.1% |
| `pre_cb_leading_index_m_m` | 0 / 18 | 0.0% |
| `pre_chicago_pmi` | 2 / 311 | 0.6% |
| `pre_congressional_elections` | 0 / 12 | 0.0% |
| `pre_core_cpi_m_m` | 116 / 363 | 32.0% |
| `pre_core_cpi_mom` | 2 / 3 | 66.7% |
| `pre_core_durable_goods_orders_m_m` | 11 / 330 | 3.3% |
| `pre_core_pce_price_index_m_m` | 27 / 314 | 8.6% |
| `pre_core_ppi_m_m` | 18 / 351 | 5.1% |
| `pre_core_retail_sales_m_m` | 39 / 360 | 10.8% |
| `pre_cpi_m_m` | 8 / 369 | 2.2% |
| `pre_cpi_mom` | 2 / 3 | 66.7% |
| `pre_cpi_y_y` | 5 / 369 | 1.4% |
| `pre_cpi_yoy` | 2 / 3 | 66.7% |
| `pre_crude_oil_inventories` | 21 / 993 | 2.1% |
| `pre_current_account` | 0 / 42 | 0.0% |
| `pre_durable_goods_orders_m_m` | 3 / 297 | 1.0% |
| `pre_empire_state_manufacturing_index` | 3 / 187 | 1.6% |
| `pre_employment_cost_index_q_q` | 0 / 87 | 0.0% |
| `pre_existing_home_sales` | 0 / 237 | 0.0% |
| `pre_factory_orders_m_m` | 0 / 102 | 0.0% |
| `pre_fed_announcement` | 8 / 36 | 22.2% |
| `pre_fed_chair_powell_speaks` | 37 / 312 | 11.9% |
| `pre_fed_chair_powell_testifies` | 5 / 141 | 3.5% |
| `pre_fed_chair_yellen_speaks` | 19 / 96 | 19.8% |
| `pre_fed_chair_yellen_testifies` | 6 / 51 | 11.8% |
| `pre_fed_monetary_policy_report` | 0 / 3 | 0.0% |
| `pre_federal_funds_rate` | 143 / 246 | 58.1% |
| `pre_final_gdp_price_index_q_q` | 0 / 27 | 0.0% |
| `pre_final_gdp_q_q` | 6 / 120 | 5.0% |
| `pre_final_manufacturing_pmi` | 0 / 33 | 0.0% |
| `pre_final_services_pmi` | 0 / 42 | 0.0% |
| `pre_flash_manufacturing_pmi` | 0 / 222 | 0.0% |
| `pre_flash_services_pmi` | 1 / 117 | 0.9% |
| `pre_fomc_economic_projections` | 13 / 120 | 10.8% |
| `pre_fomc_meeting_minutes` | 94 / 246 | 38.2% |
| `pre_fomc_member_barkin_speaks` | 3 / 54 | 5.6% |
| `pre_fomc_member_bostic_speaks` | 0 / 120 | 0.0% |
| `pre_fomc_member_bowman_speaks` | 2 / 39 | 5.1% |
| `pre_fomc_member_brainard_speaks` | 5 / 183 | 2.7% |
| `pre_fomc_member_bullard_speaks` | 8 / 180 | 4.4% |
| `pre_fomc_member_clarida_speaks` | 4 / 87 | 4.6% |
| `pre_fomc_member_collins_speaks` | 0 / 3 | 0.0% |
| `pre_fomc_member_daly_speaks` | 0 / 6 | 0.0% |
| `pre_fomc_member_dudley_speaks` | 4 / 189 | 2.1% |
| `pre_fomc_member_evans_speaks` | 2 / 156 | 1.3% |
| `pre_fomc_member_fischer_speaks` | 1 / 102 | 1.0% |
| `pre_fomc_member_george_speaks` | 0 / 69 | 0.0% |
| `pre_fomc_member_goolsbee_speaks` | 0 / 3 | 0.0% |
| `pre_fomc_member_harker_speaks` | 6 / 105 | 5.7% |
| `pre_fomc_member_kaplan_speaks` | 3 / 84 | 3.6% |
| `pre_fomc_member_kashkari_speaks` | 2 / 69 | 2.9% |
| `pre_fomc_member_kugler_speaks` | 0 / 3 | 0.0% |
| `pre_fomc_member_lacker_speaks` | 0 / 21 | 0.0% |
| `pre_fomc_member_lockhart_speaks` | 0 / 63 | 0.0% |
| `pre_fomc_member_mester_speaks` | 0 / 132 | 0.0% |
| `pre_fomc_member_powell_speaks` | 0 / 81 | 0.0% |
| `pre_fomc_member_quarles_speaks` | 2 / 106 | 1.9% |
| `pre_fomc_member_rosengren_speaks` | 1 / 39 | 2.6% |
| `pre_fomc_member_tarullo_speaks` | 0 / 3 | 0.0% |
| `pre_fomc_member_waller_speaks` | 13 / 156 | 8.3% |
| `pre_fomc_member_williams_speaks` | 6 / 192 | 3.1% |
| `pre_fomc_press_conference` | 10 / 201 | 5.0% |
| `pre_fomc_statement` | 12 / 246 | 4.9% |
| `pre_goods_trade_balance` | 3 / 24 | 12.5% |
| `pre_housing_starts` | 3 / 144 | 2.1% |
| `pre_import_prices_m_m` | 3 / 114 | 2.6% |
| `pre_industrial_production_m_m` | 3 / 201 | 1.5% |
| `pre_ism_manufacturing_pmi` | 15 / 369 | 4.1% |
| `pre_ism_manufacturing_prices` | 0 / 42 | 0.0% |
| `pre_ism_services_pmi` | 3 / 360 | 0.8% |
| `pre_jolts_job_openings` | 2 / 240 | 0.8% |
| `pre_mortgage_delinquencies` | 0 / 42 | 0.0% |
| `pre_nahb_housing_market_index` | 0 / 15 | 0.0% |
| `pre_new_home_sales` | 0 / 207 | 0.0% |
| `pre_nfp` | 1 / 3 | 33.3% |
| `pre_non_farm_employment_change` | 17 / 363 | 4.7% |
| `pre_pending_home_sales_m_m` | 1 / 273 | 0.4% |
| `pre_personal_spending_m_m` | 1 / 146 | 0.7% |
| `pre_philly_fed_manufacturing_index` | 6 / 363 | 1.7% |
| `pre_ppi_m_m` | 15 / 351 | 4.3% |
| `pre_prelim_gdp_price_index_q_q` | 0 / 24 | 0.0% |
| `pre_prelim_gdp_q_q` | 3 / 120 | 2.5% |
| `pre_prelim_nonfarm_productivity_q_q` | 0 / 42 | 0.0% |
| `pre_prelim_unit_labor_costs_q_q` | 0 / 42 | 0.0% |
| `pre_prelim_uom_consumer_sentiment` | 7 / 321 | 2.2% |
| `pre_prelim_uom_inflation_expectations` | 2 / 89 | 2.2% |
| `pre_president_biden_speaks` | 0 / 15 | 0.0% |
| `pre_president_trump_speaks` | 7 / 207 | 3.4% |
| `pre_presidential_election` | 0 / 9 | 0.0% |
| `pre_retail_sales_m_m` | 3 / 348 | 0.9% |
| `pre_revised_nonfarm_productivity_q_q` | 0 / 30 | 0.0% |
| `pre_revised_uom_consumer_sentiment` | 6 / 315 | 1.9% |
| `pre_richmond_manufacturing_index` | 2 / 120 | 1.7% |
| `pre_s_and_p_cs_composite_20_hpi_y_y` | 0 / 57 | 0.0% |
| `pre_trade_balance` | 0 / 102 | 0.0% |
| `pre_treasury_currency_report` | 2 / 39 | 5.1% |
| `pre_treasury_sec_lew_speaks` | 0 / 15 | 0.0% |
| `pre_treasury_sec_mnuchin_speaks` | 2 / 24 | 8.3% |
| `pre_treasury_sec_yellen_speaks` | 1 / 81 | 1.2% |
| `pre_unemployment_claims` | 55 / 1,320 | 4.2% |
| `pre_unemployment_rate` | 12 / 366 | 3.3% |

### Breakdown - `oc.next_5m.range_expanded_2x_pre_15m` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 815 / 9,206 | 8.9% |
| `medium` | 183 / 8,954 | 2.0% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_240m.first_bar_up_then_final_down` | 3,479 / 18,330 | 19.0% |
| `oc.next_240m.first_bar_down_then_final_up` | 4,060 / 18,330 | 22.1% |
| `oc.next_240m.direction_reversed_from_first_bar` | 7,539 / 18,330 | 41.1% |
| `oc.next_240m.close_above_release_ref` | 9,786 / 18,330 | 53.4% |
| `oc.next_240m.close_below_release_ref` | 8,368 / 18,330 | 45.7% |
| `oc.next_240m.wicked_above_ref_closed_below_ref` | 7,770 / 18,330 | 42.4% |
| `oc.next_240m.wicked_below_ref_closed_above_ref` | 9,209 / 18,330 | 50.2% |
| `oc.next_240m.range_expanded_1x_pre_15m` | 17,039 / 18,330 | 93.0% |
| `oc.next_240m.range_expanded_2x_pre_15m` | 13,657 / 18,330 | 74.5% |
| `oc.next_240m.took_pre_15m_high` | 13,968 / 18,330 | 76.2% |
| `oc.next_240m.took_pre_15m_low` | 13,429 / 18,330 | 73.3% |
| `oc.next_240m.swept_both_pre_15m_sides` | 10,093 / 18,330 | 55.1% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

_No baseline rows found in `docs/ML_BASELINE.md`._

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| macro | high | `label.next_15m.range_expanded_2x_pre_60m` | 1,401 | 5.2% | 0.927 | 39.0% | imbalanced base rate |
| macro | all | `label.next_15m.range_expanded_2x_pre_60m` | 2,373 | 3.5% | 0.914 | 27.7% | imbalanced base rate |
| macro | high | `label.next_5m.range_expanded_2x_pre_15m` | 1,400 | 7.5% | 0.872 | 46.4% | imbalanced base rate |
| macro | all | `label.next_5m.range_expanded_2x_pre_15m` | 2,371 | 5.4% | 0.849 | 35.7% | imbalanced base rate |
| macro | medium | `label.next_15m.one_sided_took_pre_60m_high` | 972 | 27.9% | 0.832 | 78.6% |  |
| macro | medium | `label.next_15m.one_sided_took_pre_60m_low` | 972 | 24.8% | 0.824 | 62.2% |  |
| macro | medium | `label.next_15m.took_pre_60m_high` | 972 | 29.7% | 0.819 | 73.5% |  |
| macro | medium | `label.next_15m.took_pre_60m_low` | 972 | 26.6% | 0.818 | 65.3% |  |
| macro | all | `label.next_15m.one_sided_took_pre_60m_high` | 2,373 | 28.4% | 0.814 | 71.4% |  |
| macro | high | `label.next_15m.swept_both_pre_60m_sides` | 1,401 | 4.6% | 0.812 | 13.5% | imbalanced base rate |

## Reading

Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/macro.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_MACRO_XCTX.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
