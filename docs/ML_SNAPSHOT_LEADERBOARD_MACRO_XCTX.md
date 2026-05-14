# ML snapshot leaderboard

_Generated `2026-05-14T01:53:13.851788+00:00`._

## Setup

- Matrix: `data\ml\anchors\macro_event_snapshots_xctx.parquet`
- Schema: `data\ml\anchors\macro_event_snapshots_xctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `high, medium, all`
- Labels searched: `16` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\macro_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| data\ml\anchors\macro_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 18414 |
| schema_feature_columns | 878 |
| schema_label_columns | 372 |
| grid_attempts | 48 |
| trained_ok | 46 |
| skipped | 2 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | 1401 | 5.2% | 0.927 | 0.961 | 0.948 | 141 | 39.0% | 33.8% |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | 2373 | 3.5% | 0.914 | 0.973 | 0.965 | 238 | 27.7% | 24.2% |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | 1400 | 7.5% | 0.872 | 0.944 | 0.925 | 140 | 46.4% | 38.9% |
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | 2371 | 5.4% | 0.849 | 0.961 | 0.946 | 238 | 35.7% | 30.3% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | 972 | 27.9% | 0.832 | 0.790 | 0.721 | 98 | 78.6% | 50.7% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | 972 | 24.8% | 0.824 | 0.811 | 0.752 | 98 | 62.2% | 37.5% |
| at_fire | medium | label.next_15m.took_pre_60m_high | 972 | 29.7% | 0.819 | 0.788 | 0.703 | 98 | 73.5% | 43.7% |
| at_fire | medium | label.next_15m.took_pre_60m_low | 972 | 26.6% | 0.818 | 0.790 | 0.734 | 98 | 65.3% | 38.7% |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | 2373 | 28.4% | 0.814 | 0.790 | 0.716 | 238 | 71.4% | 43.0% |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | 1401 | 4.6% | 0.812 | 0.954 | 0.954 | 141 | 13.5% | 8.8% |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_low | 2373 | 24.0% | 0.805 | 0.810 | 0.760 | 238 | 72.3% | 48.2% |
| at_fire | medium | label.next_60m.range_expanded_1x_pre_60m | 978 | 57.5% | 0.805 | 0.751 | 0.425 | 98 | 93.9% | 36.4% |
| at_fire | all | label.next_60m.range_expanded_1x_pre_60m | 2382 | 60.0% | 0.805 | 0.737 | 0.600 | 239 | 95.4% | 35.4% |
| at_fire | all | label.next_15m.took_pre_60m_high | 2373 | 31.9% | 0.804 | 0.764 | 0.681 | 238 | 73.9% | 42.0% |
| at_fire | all | label.next_15m.took_pre_60m_low | 2373 | 27.5% | 0.804 | 0.788 | 0.725 | 238 | 75.6% | 48.1% |
| at_fire | high | label.next_15m.one_sided_took_pre_60m_high | 1401 | 28.8% | 0.789 | 0.771 | 0.712 | 141 | 67.4% | 38.6% |
| at_fire | high | label.next_15m.took_pre_60m_high | 1401 | 33.4% | 0.786 | 0.756 | 0.666 | 141 | 81.6% | 48.2% |
| at_fire | medium | label.next_15m.took_pre_60m_high_held_above | 972 | 16.9% | 0.784 | 0.829 | 0.831 | 98 | 38.8% | 21.9% |
| at_fire | medium | label.next_15m.took_pre_60m_low_held_below | 972 | 11.3% | 0.778 | 0.876 | 0.887 | 98 | 32.7% | 21.3% |
| at_fire | high | label.next_15m.one_sided_took_pre_60m_low | 1401 | 23.5% | 0.777 | 0.813 | 0.765 | 141 | 69.5% | 46.0% |
| at_fire | all | label.next_15m.swept_both_pre_60m_sides | 2373 | 3.5% | 0.772 | 0.961 | 0.965 | 238 | 12.6% | 9.1% |
| at_fire | high | label.next_60m.range_expanded_1x_pre_60m | 1404 | 61.8% | 0.772 | 0.704 | 0.618 | 141 | 91.5% | 29.7% |
| at_fire | all | label.next_15m.took_pre_60m_low_rejected_inside | 2373 | 14.0% | 0.766 | 0.858 | 0.860 | 238 | 37.8% | 23.8% |
| at_fire | high | label.next_15m.took_pre_60m_low | 1401 | 28.1% | 0.765 | 0.764 | 0.719 | 141 | 67.4% | 39.3% |
| at_fire | medium | label.next_15m.took_pre_60m_low_rejected_inside | 972 | 14.7% | 0.761 | 0.854 | 0.853 | 98 | 41.8% | 27.1% |
| at_fire | all | label.next_15m.took_pre_60m_high_held_above | 2373 | 16.3% | 0.738 | 0.829 | 0.837 | 238 | 31.5% | 15.2% |
| at_fire | all | label.next_15m.took_pre_60m_low_held_below | 2373 | 12.4% | 0.719 | 0.876 | 0.876 | 238 | 31.9% | 19.5% |
| at_fire | high | label.next_15m.took_pre_60m_low_rejected_inside | 1401 | 13.6% | 0.712 | 0.864 | 0.864 | 141 | 28.4% | 14.8% |
| at_fire | all | label.next_15m.took_pre_60m_high_rejected_inside | 2373 | 14.4% | 0.712 | 0.858 | 0.856 | 238 | 32.4% | 18.0% |
| at_fire | high | label.next_15m.took_pre_60m_high_held_above | 1401 | 15.9% | 0.707 | 0.838 | 0.841 | 141 | 37.6% | 21.7% |
| at_fire | high | label.next_15m.took_pre_60m_high_rejected_inside | 1401 | 15.8% | 0.706 | 0.842 | 0.842 | 141 | 36.2% | 20.3% |
| at_fire | high | label.next_15m.took_pre_60m_low_held_below | 1401 | 13.1% | 0.693 | 0.867 | 0.869 | 141 | 36.9% | 23.7% |
| at_fire | medium | label.next_15m.took_pre_60m_high_rejected_inside | 972 | 12.2% | 0.690 | 0.872 | 0.878 | 98 | 23.5% | 11.2% |
| at_fire | medium | label.next_60m.swept_both_pre_60m_sides | 978 | 17.4% | 0.684 | 0.828 | 0.826 | 98 | 38.8% | 21.4% |
| at_fire | all | label.next_60m.swept_both_pre_60m_sides | 2382 | 18.5% | 0.680 | 0.814 | 0.815 | 239 | 38.1% | 19.6% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | xctx.minutes_since_last_orb_4h=6119; xctx.minutes_since_last_orb_24h=2165; xctx.minutes_since_last_fvp_4h=1829; xctx.minutes_since_last_orb_same_primary_4h=1107; ts.year=1006; macro.event_type_pre_core_cpi_m_m=747; macro.ed.forecast_value=732; macro.ed.previous_value=717; macro.event_type_pre_average_hourly_earnings_m_m=560; xctx.minutes_since_last_orb_same_primary_24h=537 |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | xctx.minutes_since_last_orb_4h=7571; xctx.minutes_since_last_orb_24h=2806; xctx.minutes_since_last_fvp_4h=1708; xctx.minutes_since_last_orb_same_primary_4h=1408; macro.event_type_pre_core_cpi_m_m=1027; macro.side_high=771; ts.year=764; macro.ed.previous_value=689; macro.event_type_pre_average_hourly_earnings_m_m=679; xctx.minutes_since_last_tp_24h=513 |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | xctx.minutes_since_last_orb_4h=6391; xctx.minutes_since_last_orb_24h=3814; macro.ed.scheduled_hour_et=1847; xctx.minutes_since_last_itr_24h=1391; xctx.minutes_since_last_orb_same_primary_4h=944; macro.event_type_pre_core_cpi_m_m=726; xctx.minutes_since_last_orb_same_primary_24h=678; macro.event_type_pre_average_hourly_earnings_m_m=572; xctx.total_events_1h=504; ts.year=491 |
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | xctx.minutes_since_last_orb_4h=9984; xctx.minutes_since_last_orb_24h=4569; macro.ed.scheduled_hour_et=3169; macro.side_high=1494; xctx.minutes_since_last_orb_same_primary_4h=1437; macro.event_type_pre_core_cpi_m_m=1250; xctx.minutes_since_last_itr_24h=1163; macro.event_type_pre_average_hourly_earnings_m_m=900; ts.year=708; xctx.minutes_since_last_orb_same_primary_24h=660 |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | macro.ed.pre_60m_close_location=31548; macro.ed.pre_60m_return_pts=2973; macro.ed.pre_15m_close_location=2261; xctx.minutes_since_last_smt_side_low_7d=922; xctx.minutes_since_last_ogap_side_gap_down_24h=755; xctx.minutes_since_last_fvg_1h=563; macro.ed.pre_5m_close_location=517; xctx.minutes_since_last_fvp_side_selling_24h=501; xctx.minutes_since_last_ft_side_bearish_7d=499; xctx.minutes_since_last_vp_side_selling_24h=491 |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | macro.ed.pre_60m_close_location=29067; macro.ed.pre_15m_return_pts=2084; macro.ed.pre_15m_close_location=1619; macro.ed.pre_60m_return_pts=1565; macro.ed.pre_5m_close_location=1326; macro.ed.scheduled_hour_et=832; xctx.minutes_since_last_ogap_24h=791; xctx.minutes_since_last_fvg_side_bullish_4h=694; xctx.minutes_since_last_smt_side_low_7d=611; xctx.minutes_since_last_psp_side_bearish_24h=455 |
| at_fire | medium | label.next_15m.took_pre_60m_high | macro.ed.pre_60m_close_location=31843; macro.ed.pre_60m_return_pts=3488; macro.ed.pre_15m_close_location=3202; xctx.minutes_since_last_smt_side_low_7d=1104; xctx.minutes_since_last_ogap_side_gap_down_24h=975; xctx.minutes_since_last_fvg_1h=903; xctx.minutes_since_last_itr_side_bullish_24h=769; xctx.minutes_since_last_orb_side_doji_7d=743; xctx.minutes_since_last_psp_side_bearish_24h=735; xctx.minutes_since_last_smt_24h=718 |
| at_fire | medium | label.next_15m.took_pre_60m_low | macro.ed.pre_60m_close_location=27767; macro.ed.pre_15m_return_pts=1918; macro.ed.pre_15m_close_location=1768; macro.ed.pre_60m_return_pts=1480; macro.ed.pre_5m_close_location=1256; xctx.minutes_since_last_ogap_24h=964; macro.ed.scheduled_hour_et=820; xctx.minutes_since_last_fvg_side_bullish_4h=708; xctx.minutes_since_last_smt_side_low_7d=591; xctx.minutes_since_last_psp_side_bearish_24h=493 |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | macro.ed.pre_60m_close_location=56176; macro.ed.pre_15m_close_location=2615; macro.ed.pre_60m_return_pts=2557; macro.ed.pre_15m_return_pts=2156; xctx.minutes_since_last_ogap_24h=1164; xctx.minutes_since_last_psp_side_bullish_24h=942; xctx.minutes_since_last_ft_side_bearish_7d=927; xctx.minutes_since_last_ogap_same_primary_24h=923; xctx.minutes_since_last_smt_24h=900; xctx.minutes_since_last_smt_side_low_7d=827 |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | xctx.minutes_since_last_orb_4h=5630; xctx.minutes_since_last_orb_same_primary_4h=1058; xctx.minutes_since_last_orb_24h=674; macro.event_type_pre_average_hourly_earnings_m_m=412; xctx.n_fvg_side_bearish_7d=324; xctx.minutes_since_last_psp_side_bullish_4h=305; xctx.n_fvg_side_bullish_7d=283; xctx.minutes_since_last_orb_side_bearish_24h=269; xctx.minutes_since_last_psp_side_bearish_24h=268; xctx.n_sweep_side_high_24h=236 |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_low | macro.ed.pre_60m_close_location=50877; macro.ed.scheduled_hour_et=3017; macro.ed.pre_60m_return_pts=2436; macro.ed.pre_15m_close_location=2222; macro.ed.pre_15m_return_pts=2051; xctx.minutes_since_last_ogap_24h=1679; macro.ed.pre_5m_close_location=1027; xctx.minutes_since_last_psp_side_bearish_24h=890; xctx.minutes_since_last_disp_side_bearish_24h=764; xctx.n_psp_7d=730 |
| at_fire | medium | label.next_60m.range_expanded_1x_pre_60m | xctx.minutes_since_last_ogap_24h=10364; macro.ed.pre_60m_range_pts=7674; macro.ed.pre_60m_return_pts=2645; macro.ed.pre_60m_close_location=2632; macro.ed.scheduled_hour_et=2569; xctx.minutes_since_last_fvg_same_primary_1h=1910; xctx.minutes_since_last_orb_24h=1669; macro.ed.pre_5m_range_pts=1309; xctx.minutes_since_last_disp_same_primary_24h=986; xctx.n_eql_side_high_7d=959 |
| at_fire | all | label.next_60m.range_expanded_1x_pre_60m | macro.ed.pre_60m_range_pts=15206; xctx.minutes_since_last_ogap_24h=14327; macro.ed.pre_60m_return_pts=5298; macro.ed.pre_60m_close_location=5123; macro.ed.scheduled_hour_et=4007; xctx.minutes_since_last_disp_same_primary_1h=3419; macro.ed.pre_5m_range_pts=2912; xctx.minutes_since_last_orb_4h=2840; xctx.minutes_since_last_ogap_7d=2122; xctx.n_eql_7d=2086 |
| at_fire | all | label.next_15m.took_pre_60m_high | macro.ed.pre_60m_close_location=53456; xctx.minutes_since_last_orb_4h=3212; macro.ed.pre_15m_close_location=3211; macro.ed.pre_60m_return_pts=3163; macro.ed.pre_15m_return_pts=1633; xctx.minutes_since_last_ogap_side_gap_down_24h=1561; xctx.minutes_since_last_ogap_same_primary_24h=1205; xctx.minutes_since_last_ogap_24h=1093; xctx.minutes_since_last_smt_24h=946; xctx.total_events_4h=934 |
| at_fire | all | label.next_15m.took_pre_60m_low | macro.ed.pre_60m_close_location=46108; macro.ed.scheduled_hour_et=3534; macro.ed.pre_15m_close_location=3038; macro.ed.pre_60m_return_pts=2179; xctx.minutes_since_last_orb_4h=1619; macro.ed.pre_15m_return_pts=1586; xctx.minutes_since_last_ogap_24h=1499; macro.ed.pre_5m_close_location=963; xctx.n_ob_side_bearish_7d=913; xctx.minutes_since_last_smt_side_low_7d=860 |

## Skipped Summary

| status | count |
|---|---|
| skip_test_imbalance | 2 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
