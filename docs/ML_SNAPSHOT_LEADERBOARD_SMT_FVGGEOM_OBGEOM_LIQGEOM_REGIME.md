# ML snapshot leaderboard

_Generated `2026-05-15T01:40:47.944497+00:00`._

## Setup

- Matrix: `data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- Schema: `data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- Event type: `previous_day_smt`
- Snapshots: `at_fire, at_period_close`
- Sides: `low, high, all`
- Labels searched: `10` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.csv | CSV leaderboard |
| data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 3150 |
| schema_label_columns | 18 |
| grid_attempts | 60 |
| trained_ok | 60 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | high | label.n1_primary_took_period_n_high | 277 | 56.3% | 0.970 | 0.892 | 0.563 | 28 | 100.0% | 43.7% |
| at_period_close | all | label.n1_primary_took_period_n_high | 528 | 53.0% | 0.964 | 0.883 | 0.530 | 53 | 100.0% | 47.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 251 | 48.2% | 0.963 | 0.896 | 0.518 | 26 | 100.0% | 51.8% |
| at_period_close | all | label.n1_primary_took_period_n_low | 528 | 45.6% | 0.960 | 0.884 | 0.544 | 53 | 100.0% | 54.4% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 277 | 43.3% | 0.959 | 0.863 | 0.567 | 28 | 100.0% | 56.7% |
| at_period_close | high | label.n1_primary_took_period_n_low | 277 | 43.3% | 0.959 | 0.863 | 0.567 | 28 | 100.0% | 56.7% |
| at_period_close | high | label.n1_close_moved_with_thesis | 277 | 43.7% | 0.958 | 0.877 | 0.563 | 28 | 96.4% | 52.7% |
| at_period_close | all | label.n1_close_moved_with_thesis | 528 | 46.8% | 0.953 | 0.873 | 0.532 | 53 | 100.0% | 53.2% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 528 | 46.2% | 0.951 | 0.875 | 0.538 | 53 | 100.0% | 53.8% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 251 | 49.4% | 0.951 | 0.876 | 0.506 | 26 | 100.0% | 50.6% |
| at_period_close | low | label.n1_primary_took_period_n_high | 251 | 49.4% | 0.951 | 0.876 | 0.506 | 26 | 100.0% | 50.6% |
| at_period_close | low | label.n1_close_moved_with_thesis | 251 | 50.2% | 0.949 | 0.869 | 0.498 | 26 | 100.0% | 49.8% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 277 | 55.6% | 0.929 | 0.870 | 0.556 | 28 | 100.0% | 44.4% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 277 | 54.2% | 0.928 | 0.859 | 0.542 | 28 | 100.0% | 45.8% |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | 528 | 60.0% | 0.893 | 0.811 | 0.600 | 53 | 100.0% | 40.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 528 | 59.3% | 0.887 | 0.786 | 0.593 | 53 | 100.0% | 40.7% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 251 | 64.9% | 0.863 | 0.797 | 0.649 | 26 | 100.0% | 35.1% |
| at_period_close | low | label.n1_or_n2_close_moved_with_thesis | 251 | 64.9% | 0.861 | 0.805 | 0.649 | 26 | 100.0% | 35.1% |
| at_period_close | high | label.n2_primary_took_period_n_high | 274 | 59.9% | 0.790 | 0.719 | 0.599 | 28 | 96.4% | 36.6% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 274 | 40.5% | 0.785 | 0.704 | 0.595 | 28 | 89.3% | 48.8% |
| at_period_close | high | label.n2_primary_took_period_n_low | 274 | 40.5% | 0.785 | 0.704 | 0.595 | 28 | 89.3% | 48.8% |
| at_period_close | high | label.n2_close_moved_with_thesis | 274 | 39.1% | 0.782 | 0.712 | 0.609 | 28 | 92.9% | 53.8% |
| at_period_close | all | label.n2_primary_took_period_n_low | 518 | 43.4% | 0.774 | 0.681 | 0.566 | 52 | 86.5% | 43.1% |
| at_period_close | all | label.n2_primary_took_period_n_high | 518 | 56.4% | 0.773 | 0.703 | 0.564 | 52 | 92.3% | 35.9% |
| at_period_close | all | label.n2_close_moved_with_thesis | 518 | 45.9% | 0.760 | 0.695 | 0.541 | 52 | 84.6% | 38.7% |
| at_period_close | low | label.n2_primary_took_period_n_low | 244 | 46.7% | 0.759 | 0.713 | 0.533 | 25 | 92.0% | 45.3% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 518 | 46.1% | 0.750 | 0.685 | 0.539 | 52 | 78.8% | 32.7% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 244 | 52.5% | 0.739 | 0.672 | 0.525 | 25 | 92.0% | 39.5% |
| at_period_close | low | label.n2_primary_took_period_n_high | 244 | 52.5% | 0.739 | 0.672 | 0.525 | 25 | 92.0% | 39.5% |
| at_period_close | low | label.n2_close_moved_with_thesis | 244 | 53.7% | 0.719 | 0.648 | 0.537 | 25 | 80.0% | 26.3% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_period_close | high | label.n1_primary_took_period_n_high | fvggeom.distance_pts_same_primary_bearish_untouched_below=3046; fvggeom.distance_pts_any_symbol_bearish_untouched_below=2936; liqgeom.distance_pts_eql_same_primary_high_fresh_above=1126; fvggeom.distance_pts_any_symbol_bullish_untouched_above=494; fvggeom.has_same_primary_bullish_untouched_above=412; fvggeom.distance_pts_any_symbol_bearish_tapped_below=266; pc.n_1h_disp_bearish_same_primary_in_window=231; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=222; fvggeom.width_pts_same_primary_bullish_untouched_above=220; fvggeom.has_same_primary_bearish_untouched_below=219 |
| at_period_close | all | label.n1_primary_took_period_n_high | fvggeom.age_min_same_primary_bullish_untouched_above=7172; fvggeom.distance_pts_same_primary_bearish_untouched_below=2497; fvggeom.distance_pts_same_primary_bullish_untouched_above=1142; fvggeom.distance_pts_any_symbol_bearish_untouched_below=1010; fvggeom.has_same_primary_bullish_untouched_above=948; fvggeom.age_min_same_primary_bearish_untouched_below=832; fvggeom.distance_pts_any_symbol_bullish_untouched_above=728; pc.minutes_since_last_sweep_high_same_primary_in_window=550; fvggeom.n_same_primary_bearish_untouched_within_25pts=487; liqgeom.distance_pts_eql_same_primary_high_fresh_above=479 |
| at_period_close | low | label.n1_primary_took_period_n_low | fvggeom.distance_pts_same_primary_bullish_untouched_above=2415; fvggeom.age_min_same_primary_bullish_untouched_above=1881; fvggeom.n_same_primary_bearish_untouched_within_25pts=1014; fvggeom.has_same_primary_bullish_untouched_above=724; fvggeom.distance_pts_any_symbol_bullish_untouched_above=510; fvggeom.n_same_primary_bearish_untouched_within_10pts=346; xctx.n_disp_side_bearish_24h=317; fvggeom.age_min_same_primary_bearish_untouched_below=291; fvggeom.age_min_same_primary_bullish_fully_filled_above=215; pc.n_1h_fvg_bullish_same_primary_in_window=203 |
| at_period_close | all | label.n1_primary_took_period_n_low | fvggeom.distance_pts_any_symbol_bearish_untouched_below=5646; fvggeom.age_min_same_primary_bullish_untouched_above=1746; fvggeom.age_min_any_symbol_bullish_untouched_above=1641; fvggeom.has_same_primary_bearish_untouched_below=1148; fvggeom.distance_pts_same_primary_bullish_untouched_above=1068; fvggeom.age_min_same_primary_bearish_untouched_below=1041; fvggeom.distance_pts_same_primary_bearish_untouched_below=800; fvggeom.n_same_primary_bearish_untouched_within_25pts=698; xctx.n_disp_side_bearish_24h=579; fvggeom.n_same_primary_bearish_untouched_within_50pts=515 |
| at_period_close | high | label.n1_thesis_confirmed_strict | fvggeom.distance_pts_any_symbol_bearish_untouched_below=4586; fvggeom.has_same_primary_bearish_untouched_below=747; fvggeom.width_pts_same_primary_bearish_untouched_below=596; liqgeom.distance_pts_eql_same_primary_high_fresh_above=520; fvggeom.distance_pts_same_primary_bearish_untouched_below=494; pc.n_1h_disp_bearish_same_primary_in_window=490; fvggeom.distance_pts_any_symbol_bullish_untouched_above=333; pc.n_1h_fvg_bearish_same_primary_in_window=224; fvggeom.distance_pts_any_symbol_bearish_tapped_below=191; fvggeom.width_pts_same_primary_bullish_untouched_above=161 |
| at_period_close | high | label.n1_primary_took_period_n_low | fvggeom.distance_pts_any_symbol_bearish_untouched_below=4586; fvggeom.has_same_primary_bearish_untouched_below=747; fvggeom.width_pts_same_primary_bearish_untouched_below=596; liqgeom.distance_pts_eql_same_primary_high_fresh_above=520; fvggeom.distance_pts_same_primary_bearish_untouched_below=494; pc.n_1h_disp_bearish_same_primary_in_window=490; fvggeom.distance_pts_any_symbol_bullish_untouched_above=333; pc.n_1h_fvg_bearish_same_primary_in_window=224; fvggeom.distance_pts_any_symbol_bearish_tapped_below=191; fvggeom.width_pts_same_primary_bullish_untouched_above=161 |
| at_period_close | high | label.n1_close_moved_with_thesis | fvggeom.distance_pts_any_symbol_bearish_untouched_below=4898; fvggeom.has_same_primary_bearish_untouched_below=819; liqgeom.distance_pts_eql_same_primary_high_fresh_above=788; fvggeom.distance_pts_any_symbol_bullish_untouched_above=536; fvggeom.distance_pts_same_primary_bearish_untouched_below=504; pc.n_1h_disp_bearish_same_primary_in_window=453; fvggeom.width_pts_same_primary_bearish_untouched_below=335; xctx.minutes_since_last_sweep_side_low_24h=230; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=183; fvggeom.distance_pts_any_symbol_bearish_tapped_below=168 |
| at_period_close | all | label.n1_close_moved_with_thesis | pc.n_1h_disp_bearish_same_primary_in_window=2269; pc.n_1h_fvg_bullish_same_primary_in_window=1563; fvggeom.distance_pts_any_symbol_bullish_untouched_above=1466; fvggeom.distance_pts_any_symbol_bearish_untouched_below=1451; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1392; pc.minutes_since_last_sweep_high_same_primary_in_window=1068; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=898; pc.minutes_since_last_sweep_low_same_primary_in_window=742; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=493; fvggeom.distance_pts_same_primary_bullish_untouched_above=455 |
| at_period_close | all | label.n1_thesis_confirmed_strict | pc.n_1h_disp_bearish_same_primary_in_window=2119; pc.n_1h_fvg_bullish_same_primary_in_window=1714; fvggeom.distance_pts_any_symbol_bearish_untouched_below=1239; fvggeom.distance_pts_any_symbol_bullish_untouched_above=1195; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1147; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1071; pc.minutes_since_last_sweep_high_same_primary_in_window=938; pc.minutes_since_last_sweep_low_same_primary_in_window=929; fvggeom.width_pts_same_primary_bearish_untouched_below=884; fvggeom.distance_pts_same_primary_bullish_untouched_above=618 |
| at_period_close | low | label.n1_thesis_confirmed_strict | fvggeom.age_min_same_primary_bullish_untouched_above=2898; fvggeom.has_same_primary_bullish_untouched_above=1435; fvggeom.distance_pts_same_primary_bullish_untouched_above=1215; fvggeom.n_same_primary_bearish_untouched_within_25pts=775; fvggeom.distance_pts_any_symbol_bullish_untouched_above=476; xctx.n_disp_side_bearish_24h=356; xctx.n_fvg_side_bearish_24h=295; fvggeom.n_same_primary_bearish_untouched_within_10pts=244; pc.n_1h_fvg_bullish_same_primary_in_window=215; fvggeom.n_any_symbol_bearish_untouched_within_25pts=212 |
| at_period_close | low | label.n1_primary_took_period_n_high | fvggeom.age_min_same_primary_bullish_untouched_above=2898; fvggeom.has_same_primary_bullish_untouched_above=1435; fvggeom.distance_pts_same_primary_bullish_untouched_above=1215; fvggeom.n_same_primary_bearish_untouched_within_25pts=775; fvggeom.distance_pts_any_symbol_bullish_untouched_above=476; xctx.n_disp_side_bearish_24h=356; xctx.n_fvg_side_bearish_24h=295; fvggeom.n_same_primary_bearish_untouched_within_10pts=244; pc.n_1h_fvg_bullish_same_primary_in_window=215; fvggeom.n_any_symbol_bearish_untouched_within_25pts=212 |
| at_period_close | low | label.n1_close_moved_with_thesis | fvggeom.distance_pts_same_primary_bullish_untouched_above=2579; fvggeom.age_min_same_primary_bullish_untouched_above=2055; fvggeom.has_same_primary_bullish_untouched_above=720; fvggeom.n_same_primary_bearish_untouched_within_25pts=556; fvggeom.age_min_same_primary_bearish_untouched_below=359; fvggeom.age_min_same_primary_bullish_fully_filled_above=350; fvggeom.n_same_primary_bearish_untouched_within_50pts=274; fvggeom.n_any_symbol_bearish_untouched_within_25pts=269; fvggeom.age_min_any_symbol_bullish_tapped_above=220; fvggeom.age_min_same_primary_bullish_tapped_above=206 |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | fvggeom.distance_pts_any_symbol_bearish_untouched_below=2572; fvggeom.age_min_same_primary_bearish_untouched_below=759; fvggeom.distance_pts_same_primary_bearish_untouched_below=708; fvggeom.width_pts_same_primary_bullish_untouched_above=458; fvggeom.age_min_same_primary_bullish_untouched_above=370; liqgeom.distance_pts_eql_any_symbol_high_fresh_above=261; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=256; xctx.n_fvg_side_bullish_24h=243; pc.n_1h_disp_bearish_same_primary_in_window=224; fvggeom.age_min_same_primary_bearish_mid_filled_below=142 |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | fvggeom.distance_pts_any_symbol_bearish_untouched_below=2880; fvggeom.age_min_same_primary_bearish_untouched_below=642; fvggeom.has_same_primary_bearish_untouched_below=345; fvggeom.age_min_same_primary_bullish_untouched_above=342; fvggeom.distance_pts_same_primary_bearish_untouched_below=335; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=222; fvggeom.n_same_primary_bearish_untouched_within_25pts=214; fvggeom.age_min_any_symbol_bullish_untouched_above=209; liqgeom.distance_pts_eql_any_symbol_high_fresh_above=197; fvggeom.width_pts_same_primary_bullish_untouched_above=180 |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | pc.minutes_since_last_sweep_high_same_primary_in_window=1341; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=1131; pc.minutes_since_last_sweep_low_same_primary_in_window=962; fvggeom.distance_pts_any_symbol_bearish_untouched_below=926; pc.n_1h_disp_bearish_same_primary_in_window=904; fvggeom.age_min_same_primary_bearish_untouched_below=851; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=511; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=394; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=366; liqgeom.distance_pts_eql_same_primary_high_fresh_above=320 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
