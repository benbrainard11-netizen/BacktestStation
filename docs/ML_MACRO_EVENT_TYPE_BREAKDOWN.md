# Macro Event-Type Breakdown

_Generated `2026-05-14T02:01:56.365518+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\macro_event_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\macro_event_snapshots_xctx.schema.json`
- Rows: `18414`
- Feature columns: `878`
- Label columns: `372`
- Labels checked: `16`
- Minimum rows per breakdown bucket: `250`

## Output Files

| file | purpose |
| --- | --- |
| C:\Users\benbr\BacktestStation\data\ml\anchors\macro_event_type_breakdown.csv | family/exact event hit-rate CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\macro_event_type_breakdown.parquet | family/exact event hit-rate parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\macro_event_type_model_leaderboard.csv | event-family model leaderboard CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\macro_event_type_model_leaderboard.parquet | event-family model leaderboard parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\macro_event_type_walk_forward_summary.csv | event-family walk-forward summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\macro_event_type_walk_forward_folds.csv | event-family walk-forward folds CSV |

## Family Hit Rates

| family | rows | event_types | main hit rates |
| --- | --- | --- | --- |
| jobs_nfp | 1,461 | 5 | next_5m.range_expanded_2x_pre_15m: 7.9%; next_15m.range_expanded_2x_pre_60m: 4.7%; next_15m.took_pre_60m_high: 34.4%; next_15m.took_pre_60m_low: 27.6%; next_15m.swept_both_pre_60m_sides: 2.7%; next_15m.one_sided_took_pre_60m_high: 31.8% |
| claims | 1,320 | 1 | next_5m.range_expanded_2x_pre_15m: 4.2%; next_15m.range_expanded_2x_pre_60m: 1.3%; next_15m.took_pre_60m_high: 29.9%; next_15m.took_pre_60m_low: 24.4%; next_15m.swept_both_pre_60m_sides: 1.8%; next_15m.one_sided_took_pre_60m_high: 28.1% |
| cpi | 1,110 | 6 | next_5m.range_expanded_2x_pre_15m: 12.2%; next_15m.range_expanded_2x_pre_60m: 8.1%; next_15m.took_pre_60m_high: 34.9%; next_15m.took_pre_60m_low: 30.7%; next_15m.swept_both_pre_60m_sides: 4.6%; next_15m.one_sided_took_pre_60m_high: 30.3% |
| ism | 771 | 3 | next_5m.range_expanded_2x_pre_15m: 2.3%; next_15m.range_expanded_2x_pre_60m: 1.2%; next_15m.took_pre_60m_high: 37.0%; next_15m.took_pre_60m_low: 34.2%; next_15m.swept_both_pre_60m_sides: 3.4%; next_15m.one_sided_took_pre_60m_high: 33.6% |
| retail_sales | 708 | 2 | next_5m.range_expanded_2x_pre_15m: 5.9%; next_15m.range_expanded_2x_pre_60m: 0.8%; next_15m.took_pre_60m_high: 27.4%; next_15m.took_pre_60m_low: 28.8%; next_15m.swept_both_pre_60m_sides: 1.4%; next_15m.one_sided_took_pre_60m_high: 26.0% |
| ppi | 702 | 2 | next_5m.range_expanded_2x_pre_15m: 4.7%; next_15m.range_expanded_2x_pre_60m: 2.6%; next_15m.took_pre_60m_high: 27.5%; next_15m.took_pre_60m_low: 31.1%; next_15m.swept_both_pre_60m_sides: 1.9%; next_15m.one_sided_took_pre_60m_high: 25.6% |
| fomc_rates | 651 | 4 | next_5m.range_expanded_2x_pre_15m: 27.2%; next_15m.range_expanded_2x_pre_60m: 20.7%; next_15m.took_pre_60m_high: 46.8%; next_15m.took_pre_60m_low: 36.7%; next_15m.swept_both_pre_60m_sides: 17.4%; next_15m.one_sided_took_pre_60m_high: 29.3% |
| gdp | 537 | 6 | next_5m.range_expanded_2x_pre_15m: 7.4%; next_15m.range_expanded_2x_pre_60m: 3.0%; next_15m.took_pre_60m_high: 32.8%; next_15m.took_pre_60m_low: 27.7%; next_15m.swept_both_pre_60m_sides: 3.0%; next_15m.one_sided_took_pre_60m_high: 29.8% |
| pce | 463 | 2 | next_5m.range_expanded_2x_pre_15m: 6.1%; next_15m.range_expanded_2x_pre_60m: 2.6%; next_15m.took_pre_60m_high: 31.7%; next_15m.took_pre_60m_low: 24.3%; next_15m.swept_both_pre_60m_sides: 0.9%; next_15m.one_sided_took_pre_60m_high: 30.9% |

## Top Exact Event Types

| event_type | rows | next_5m.range_expanded_2x_pre_15m | next_15m.range_expanded_2x_pre_60m |
| --- | --- | --- | --- |
| pre_unemployment_claims | 1,320 | 4.2% | 1.3% |
| pre_crude_oil_inventories | 993 | 2.1% | 0.6% |
| pre_cpi_m_m | 369 | 2.2% | 1.1% |
| pre_cpi_y_y | 369 | 1.4% | 0.3% |
| pre_ism_manufacturing_pmi | 369 | 4.1% | 2.4% |
| pre_adp_non_farm_employment_change | 366 | 8.2% | 1.6% |
| pre_cb_consumer_confidence | 366 | 1.1% | 0.3% |
| pre_unemployment_rate | 366 | 3.3% | 2.5% |
| pre_average_hourly_earnings_m_m | 363 | 15.4% | 10.5% |
| pre_core_cpi_m_m | 363 | 32.0% | 23.4% |
| pre_non_farm_employment_change | 363 | 4.7% | 3.3% |
| pre_philly_fed_manufacturing_index | 363 | 1.7% | 0.0% |
| pre_core_retail_sales_m_m | 360 | 10.8% | 1.7% |
| pre_ism_services_pmi | 360 | 0.8% | 0.0% |
| pre_prelim_uom_consumer_sentiment | 357 | 2.2% | 0.6% |
| pre_core_ppi_m_m | 351 | 5.1% | 3.4% |
| pre_ppi_m_m | 351 | 4.3% | 1.7% |
| pre_retail_sales_m_m | 348 | 0.9% | 0.0% |
| pre_core_durable_goods_orders_m_m | 330 | 3.3% | 2.1% |
| pre_core_pce_price_index_m_m | 317 | 8.6% | 3.5% |

## Event-Family Model Leaderboard

| family | side | label | test_n | base | AUC | top_10_rate | top_lift |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cpi | all | `label.next_15m.range_expanded_2x_pre_60m` | 144 | 16.7% | 1.000 | 100.0% | 83.3% |
| cpi | high | `label.next_15m.range_expanded_2x_pre_60m` | 144 | 16.7% | 1.000 | 100.0% | 83.3% |
| jobs_nfp | all | `label.next_15m.range_expanded_2x_pre_60m` | 180 | 7.2% | 0.993 | 72.2% | 65.0% |
| jobs_nfp | high | `label.next_15m.range_expanded_2x_pre_60m` | 180 | 7.2% | 0.991 | 72.2% | 65.0% |
| fomc_rates | all | `label.next_5m.range_expanded_2x_pre_15m` | 75 | 18.7% | 0.966 | 87.5% | 68.8% |
| jobs_nfp | all | `label.next_5m.range_expanded_2x_pre_15m` | 180 | 7.2% | 0.963 | 61.1% | 53.9% |
| cpi | high | `label.next_5m.range_expanded_2x_pre_15m` | 144 | 21.5% | 0.961 | 93.3% | 71.8% |
| fomc_rates | high | `label.next_15m.range_expanded_2x_pre_60m` | 75 | 12.0% | 0.951 | 75.0% | 63.0% |
| cpi | all | `label.next_5m.range_expanded_2x_pre_15m` | 144 | 21.5% | 0.950 | 93.3% | 71.8% |
| jobs_nfp | high | `label.next_5m.range_expanded_2x_pre_15m` | 180 | 7.2% | 0.946 | 61.1% | 53.9% |
| fomc_rates | high | `label.next_5m.range_expanded_2x_pre_15m` | 75 | 18.7% | 0.945 | 100.0% | 81.3% |
| fomc_rates | all | `label.next_15m.range_expanded_2x_pre_60m` | 75 | 12.0% | 0.914 | 50.0% | 38.0% |
| cpi | high | `label.next_15m.took_pre_60m_high_rejected_inside` | 144 | 16.0% | 0.886 | 93.3% | 77.4% |
| ism | high | `label.next_15m.took_pre_60m_high_held_above` | 99 | 13.1% | 0.875 | 50.0% | 36.9% |
| ism | all | `label.next_15m.took_pre_60m_high_held_above` | 126 | 14.3% | 0.866 | 53.8% | 39.6% |
| cpi | all | `label.next_15m.took_pre_60m_high` | 144 | 41.7% | 0.860 | 93.3% | 51.7% |
| cpi | all | `label.next_15m.one_sided_took_pre_60m_high` | 144 | 25.0% | 0.852 | 53.3% | 28.3% |
| cpi | high | `label.next_60m.swept_both_pre_60m_sides` | 144 | 25.0% | 0.849 | 86.7% | 61.7% |
| retail_sales | high | `label.next_60m.range_expanded_1x_pre_60m` | 78 | 44.9% | 0.843 | 100.0% | 55.1% |
| claims | all | `label.next_15m.one_sided_took_pre_60m_low` | 195 | 20.5% | 0.841 | 65.0% | 44.5% |
| gdp | all | `label.next_15m.took_pre_60m_low_rejected_inside` | 90 | 10.0% | 0.839 | 33.3% | 23.3% |
| jobs_nfp | high | `label.next_15m.took_pre_60m_high_rejected_inside` | 180 | 13.9% | 0.835 | 50.0% | 36.1% |
| jobs_nfp | all | `label.next_15m.took_pre_60m_high` | 180 | 29.4% | 0.833 | 77.8% | 48.3% |
| cpi | high | `label.next_15m.one_sided_took_pre_60m_high` | 144 | 25.0% | 0.832 | 73.3% | 48.3% |
| ism | all | `label.next_15m.one_sided_took_pre_60m_high` | 126 | 31.0% | 0.825 | 100.0% | 69.0% |

## Event-Family Walk-Forward

| family | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | mean_top_10_rate | mean_top_lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jobs_nfp | all | `label.next_5m.range_expanded_2x_pre_15m` | 5 | 705 | 0.777 | 0.769 | 0.541 | 38.6% | 29.7% |
| cpi | high | `label.next_5m.range_expanded_2x_pre_15m` | 4 | 423 | 0.966 | 0.961 | 0.953 | 85.9% | 67.4% |
| cpi | all | `label.next_5m.range_expanded_2x_pre_15m` | 4 | 432 | 0.966 | 0.963 | 0.946 | 84.1% | 66.0% |
| jobs_nfp | high | `label.next_5m.range_expanded_2x_pre_15m` | 4 | 549 | 0.841 | 0.845 | 0.722 | 43.6% | 33.7% |
| cpi | high | `label.next_15m.range_expanded_2x_pre_60m` | 2 | 216 | 0.925 | 0.925 | 0.850 | 77.3% | 63.4% |
| cpi | all | `label.next_15m.range_expanded_2x_pre_60m` | 2 | 216 | 0.903 | 0.903 | 0.806 | 77.3% | 63.4% |
| fomc_rates | all | `label.next_5m.range_expanded_2x_pre_15m` | 1 | 87 | 0.874 | 0.874 | 0.874 | 88.9% | 59.0% |
| fomc_rates | all | `label.next_15m.range_expanded_2x_pre_60m` | 1 | 87 | 0.604 | 0.604 | 0.604 | 33.3% | 18.4% |

## Reading

- Use this as macro research triage, not strategy logic.
- The one-split event-family leaderboard is for finding candidates; the walk-forward table is the stricter trust filter.
- Broad families with strong walk-forward AUC and acceptable minimum-year AUC are better future ML features than tiny exact event groups.
- Imbalanced labels can still be useful for ranking rare reactions, but they need event-specific validation before being trusted.
- Exact event-type hit rates are descriptive only; they are not proof of predictive edge.
