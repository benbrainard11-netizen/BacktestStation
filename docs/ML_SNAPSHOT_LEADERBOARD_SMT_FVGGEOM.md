# ML snapshot leaderboard

_Generated `2026-05-12T19:35:13.470439+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom.schema.json`
- Event type: `all`
- Snapshots: `at_fire, at_period_close`
- Sides: `high, low, all`
- Labels searched: `10` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx_fvggeom.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx_fvggeom.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 1324 |
| schema_label_columns | 18 |
| grid_attempts | 60 |
| trained_ok | 60 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | high | label.n1_primary_took_period_n_high | 277 | 56.3% | 0.970 | 0.903 | 0.563 | 28 | 100.0% | 43.7% |
| at_period_close | low | label.n1_primary_took_period_n_low | 251 | 48.2% | 0.967 | 0.912 | 0.518 | 26 | 100.0% | 51.8% |
| at_period_close | all | label.n1_primary_took_period_n_low | 528 | 45.6% | 0.964 | 0.883 | 0.544 | 53 | 100.0% | 54.4% |
| at_period_close | all | label.n1_primary_took_period_n_high | 528 | 53.0% | 0.962 | 0.884 | 0.530 | 53 | 100.0% | 47.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 277 | 43.3% | 0.961 | 0.870 | 0.567 | 28 | 100.0% | 56.7% |
| at_period_close | high | label.n1_primary_took_period_n_low | 277 | 43.3% | 0.961 | 0.870 | 0.567 | 28 | 100.0% | 56.7% |
| at_period_close | high | label.n1_close_moved_with_thesis | 277 | 43.7% | 0.958 | 0.884 | 0.563 | 28 | 96.4% | 52.7% |
| at_period_close | low | label.n1_close_moved_with_thesis | 251 | 50.2% | 0.955 | 0.869 | 0.498 | 26 | 100.0% | 49.8% |
| at_period_close | all | label.n1_close_moved_with_thesis | 528 | 46.8% | 0.953 | 0.862 | 0.532 | 53 | 100.0% | 53.2% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 251 | 49.4% | 0.950 | 0.865 | 0.506 | 26 | 100.0% | 50.6% |
| at_period_close | low | label.n1_primary_took_period_n_high | 251 | 49.4% | 0.950 | 0.865 | 0.506 | 26 | 100.0% | 50.6% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 528 | 46.2% | 0.950 | 0.864 | 0.538 | 53 | 98.1% | 51.9% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 277 | 55.6% | 0.916 | 0.845 | 0.556 | 28 | 100.0% | 44.4% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 277 | 54.2% | 0.913 | 0.841 | 0.542 | 28 | 100.0% | 45.8% |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | 528 | 60.0% | 0.897 | 0.811 | 0.600 | 53 | 100.0% | 40.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 528 | 59.3% | 0.895 | 0.826 | 0.593 | 53 | 100.0% | 40.7% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 251 | 64.9% | 0.892 | 0.825 | 0.649 | 26 | 100.0% | 35.1% |
| at_period_close | low | label.n1_or_n2_close_moved_with_thesis | 251 | 64.9% | 0.882 | 0.821 | 0.649 | 26 | 100.0% | 35.1% |
| at_period_close | low | label.n2_primary_took_period_n_low | 244 | 46.7% | 0.781 | 0.701 | 0.533 | 25 | 96.0% | 49.3% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 274 | 40.5% | 0.780 | 0.712 | 0.595 | 28 | 89.3% | 48.8% |
| at_period_close | high | label.n2_primary_took_period_n_low | 274 | 40.5% | 0.780 | 0.712 | 0.595 | 28 | 89.3% | 48.8% |
| at_period_close | high | label.n2_primary_took_period_n_high | 274 | 59.9% | 0.779 | 0.726 | 0.599 | 28 | 96.4% | 36.6% |
| at_period_close | all | label.n2_primary_took_period_n_high | 518 | 56.4% | 0.776 | 0.708 | 0.564 | 52 | 92.3% | 35.9% |
| at_period_close | all | label.n2_primary_took_period_n_low | 518 | 43.4% | 0.775 | 0.710 | 0.566 | 52 | 88.5% | 45.0% |
| at_period_close | all | label.n2_close_moved_with_thesis | 518 | 45.9% | 0.766 | 0.681 | 0.541 | 52 | 88.5% | 42.5% |
| at_period_close | high | label.n2_close_moved_with_thesis | 274 | 39.1% | 0.764 | 0.726 | 0.609 | 28 | 96.4% | 57.4% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 518 | 46.1% | 0.760 | 0.695 | 0.539 | 52 | 82.7% | 36.6% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 244 | 52.5% | 0.758 | 0.684 | 0.525 | 25 | 84.0% | 31.5% |
| at_period_close | low | label.n2_primary_took_period_n_high | 244 | 52.5% | 0.758 | 0.684 | 0.525 | 25 | 84.0% | 31.5% |
| at_period_close | low | label.n2_close_moved_with_thesis | 244 | 53.7% | 0.747 | 0.676 | 0.537 | 25 | 80.0% | 26.3% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_period_close | high | label.n1_primary_took_period_n_high | fvggeom.distance_pts_any_symbol_bearish_untouched_below=3240; fvggeom.distance_pts_same_primary_bearish_untouched_below=3087; fvggeom.has_same_primary_bullish_untouched_above=689; fvggeom.distance_pts_any_symbol_bullish_untouched_above=547; fvggeom.width_pts_same_primary_bullish_untouched_above=443; fvggeom.age_min_same_primary_bearish_fully_filled_below=417; xctx.n_fvg_side_bullish_24h=272; fvggeom.age_min_same_primary_bullish_fully_filled_below=271; fvggeom.distance_pts_any_symbol_bearish_tapped_below=250; fvggeom.distance_pts_any_symbol_bearish_mid_filled_below=243 |
| at_period_close | low | label.n1_primary_took_period_n_low | fvggeom.distance_pts_same_primary_bullish_untouched_above=2466; fvggeom.age_min_same_primary_bullish_untouched_above=2242; fvggeom.distance_pts_any_symbol_bullish_untouched_above=911; fvggeom.n_same_primary_bearish_untouched_within_25pts=829; xctx.n_disp_side_bearish_24h=400; fvggeom.n_same_primary_bearish_untouched_within_10pts=352; fvggeom.age_min_same_primary_bearish_untouched_below=300; fvggeom.age_min_any_symbol_bullish_untouched_above=279; fvggeom.age_min_same_primary_bullish_fully_filled_above=271; fvggeom.n_any_symbol_bearish_untouched_within_25pts=232 |
| at_period_close | all | label.n1_primary_took_period_n_low | fvggeom.distance_pts_any_symbol_bearish_untouched_below=5650; fvggeom.age_min_same_primary_bullish_untouched_above=2076; fvggeom.age_min_any_symbol_bullish_untouched_above=1784; fvggeom.has_same_primary_bearish_untouched_below=1359; fvggeom.age_min_same_primary_bearish_untouched_below=975; fvggeom.distance_pts_same_primary_bullish_untouched_above=746; fvggeom.n_same_primary_bearish_untouched_within_50pts=595; fvggeom.distance_pts_same_primary_bearish_untouched_below=539; xctx.n_disp_side_bearish_24h=539; fvggeom.width_pts_same_primary_bearish_untouched_below=495 |
| at_period_close | all | label.n1_primary_took_period_n_high | fvggeom.age_min_same_primary_bullish_untouched_above=7066; fvggeom.distance_pts_same_primary_bearish_untouched_below=2349; fvggeom.has_same_primary_bullish_untouched_above=1211; fvggeom.distance_pts_any_symbol_bearish_untouched_below=1122; fvggeom.age_min_same_primary_bearish_untouched_below=1028; fvggeom.distance_pts_same_primary_bullish_untouched_above=986; fvggeom.distance_pts_any_symbol_bullish_untouched_above=928; pc.minutes_since_last_sweep_high_same_primary_in_window=578; xctx.n_disp_side_bearish_24h=469; xctx.minutes_since_last_sweep_side_low_24h=431 |
| at_period_close | high | label.n1_thesis_confirmed_strict | fvggeom.distance_pts_any_symbol_bearish_untouched_below=4147; fvggeom.has_same_primary_bearish_untouched_below=1496; fvggeom.width_pts_same_primary_bearish_untouched_below=855; pc.n_1h_disp_bearish_same_primary_in_window=475; fvggeom.distance_pts_any_symbol_bullish_untouched_above=421; pc.n_1h_fvg_bearish_same_primary_in_window=241; fvggeom.distance_pts_any_symbol_bearish_mid_filled_below=239; fvggeom.width_pts_same_primary_bullish_untouched_above=236; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=223; fvggeom.has_same_primary_bullish_untouched_above=212 |
| at_period_close | high | label.n1_primary_took_period_n_low | fvggeom.distance_pts_any_symbol_bearish_untouched_below=4147; fvggeom.has_same_primary_bearish_untouched_below=1496; fvggeom.width_pts_same_primary_bearish_untouched_below=855; pc.n_1h_disp_bearish_same_primary_in_window=475; fvggeom.distance_pts_any_symbol_bullish_untouched_above=421; pc.n_1h_fvg_bearish_same_primary_in_window=241; fvggeom.distance_pts_any_symbol_bearish_mid_filled_below=239; fvggeom.width_pts_same_primary_bullish_untouched_above=236; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=223; fvggeom.has_same_primary_bullish_untouched_above=212 |
| at_period_close | high | label.n1_close_moved_with_thesis | fvggeom.distance_pts_any_symbol_bearish_untouched_below=4575; fvggeom.has_same_primary_bearish_untouched_below=1551; fvggeom.distance_pts_any_symbol_bullish_untouched_above=509; xctx.minutes_since_last_sweep_side_low_24h=419; fvggeom.has_same_primary_bullish_untouched_above=398; pc.n_1h_disp_bearish_same_primary_in_window=387; fvggeom.width_pts_same_primary_bullish_untouched_above=369; fvggeom.width_pts_same_primary_bearish_untouched_below=362; pc.minutes_since_last_sweep_high_same_primary_in_window=283; fvggeom.distance_pts_same_primary_bearish_untouched_below=236 |
| at_period_close | low | label.n1_close_moved_with_thesis | fvggeom.age_min_same_primary_bullish_untouched_above=2779; fvggeom.distance_pts_same_primary_bullish_untouched_above=2701; fvggeom.n_same_primary_bearish_untouched_within_25pts=637; fvggeom.age_min_same_primary_bullish_fully_filled_above=373; fvggeom.age_min_same_primary_bearish_untouched_below=369; fvggeom.n_same_primary_bearish_untouched_within_50pts=347; pc.n_15m_fvg_bullish_same_primary_in_window=262; fvggeom.age_min_same_primary_bullish_tapped_above=244; fvggeom.distance_pts_any_symbol_bullish_mid_filled_above=233; fvggeom.age_min_any_symbol_bullish_tapped_above=204 |
| at_period_close | all | label.n1_close_moved_with_thesis | pc.n_1h_disp_bearish_same_primary_in_window=1985; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1671; pc.n_1h_fvg_bullish_same_primary_in_window=1576; fvggeom.distance_pts_any_symbol_bullish_untouched_above=1496; fvggeom.distance_pts_any_symbol_bearish_untouched_below=1422; pc.minutes_since_last_sweep_high_same_primary_in_window=1258; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1007; pc.minutes_since_last_sweep_low_same_primary_in_window=803; fvggeom.distance_pts_same_primary_bullish_untouched_above=639; fvggeom.width_pts_same_primary_bearish_untouched_below=467 |
| at_period_close | low | label.n1_thesis_confirmed_strict | fvggeom.age_min_same_primary_bullish_untouched_above=3545; fvggeom.distance_pts_same_primary_bullish_untouched_above=1250; fvggeom.has_same_primary_bullish_untouched_above=1066; fvggeom.n_same_primary_bearish_untouched_within_25pts=825; xctx.n_fvg_side_bearish_24h=313; fvggeom.distance_pts_any_symbol_bullish_untouched_above=308; xctx.n_disp_side_bearish_24h=304; fvggeom.age_min_same_primary_any_side_untouched_below=239; pc.n_1h_fvg_bullish_same_primary_in_window=235; fvggeom.age_min_any_symbol_bullish_mid_filled_above=215 |
| at_period_close | low | label.n1_primary_took_period_n_high | fvggeom.age_min_same_primary_bullish_untouched_above=3545; fvggeom.distance_pts_same_primary_bullish_untouched_above=1250; fvggeom.has_same_primary_bullish_untouched_above=1066; fvggeom.n_same_primary_bearish_untouched_within_25pts=825; xctx.n_fvg_side_bearish_24h=313; fvggeom.distance_pts_any_symbol_bullish_untouched_above=308; xctx.n_disp_side_bearish_24h=304; fvggeom.age_min_same_primary_any_side_untouched_below=239; pc.n_1h_fvg_bullish_same_primary_in_window=235; fvggeom.age_min_any_symbol_bullish_mid_filled_above=215 |
| at_period_close | all | label.n1_thesis_confirmed_strict | pc.n_1h_disp_bearish_same_primary_in_window=2167; pc.n_1h_fvg_bullish_same_primary_in_window=1533; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1308; fvggeom.distance_pts_any_symbol_bearish_untouched_below=1308; fvggeom.distance_pts_any_symbol_bullish_untouched_above=1264; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1118; pc.minutes_since_last_sweep_high_same_primary_in_window=999; fvggeom.width_pts_same_primary_bearish_untouched_below=999; pc.minutes_since_last_sweep_low_same_primary_in_window=882; fvggeom.age_min_same_primary_bullish_untouched_above=729 |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | fvggeom.distance_pts_any_symbol_bearish_untouched_below=2381; fvggeom.distance_pts_same_primary_bearish_untouched_below=981; fvggeom.age_min_same_primary_bearish_untouched_below=668; fvggeom.width_pts_same_primary_bullish_untouched_above=443; fvggeom.age_min_same_primary_bullish_untouched_above=416; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=338; xctx.n_fvg_side_bullish_24h=318; pc.n_1h_disp_bearish_same_primary_in_window=224; fvggeom.age_min_same_primary_bearish_mid_filled_below=169; pc.minutes_since_last_1h_psp_bearish_in_window=157 |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | fvggeom.distance_pts_any_symbol_bearish_untouched_below=2627; fvggeom.distance_pts_same_primary_bearish_untouched_below=731; fvggeom.age_min_same_primary_bearish_untouched_below=550; fvggeom.age_min_any_symbol_bullish_untouched_above=328; fvggeom.has_same_primary_bearish_untouched_below=327; fvggeom.age_min_same_primary_bullish_untouched_above=287; fvggeom.width_pts_same_primary_bullish_untouched_above=232; pc.n_1h_disp_bearish_same_primary_in_window=215; fvggeom.age_min_any_symbol_bullish_fully_filled_above=196; fvggeom.n_same_primary_bearish_untouched_within_25pts=189 |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | pc.minutes_since_last_sweep_high_same_primary_in_window=1292; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=1084; pc.n_1h_disp_bearish_same_primary_in_window=963; fvggeom.distance_pts_any_symbol_bearish_untouched_below=958; pc.minutes_since_last_sweep_low_same_primary_in_window=900; fvggeom.age_min_same_primary_bearish_untouched_below=772; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=506; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=460; xctx.n_disp_side_bearish_24h=393; fvggeom.width_pts_same_primary_bearish_untouched_below=343 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
