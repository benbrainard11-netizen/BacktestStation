# ML snapshot leaderboard

_Generated `2026-05-12T19:48:06.014002+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots_xctx_fvggeom.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `6` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard_xctx_fvggeom.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard_xctx_fvggeom.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 19414 |
| schema_feature_columns | 1077 |
| schema_label_columns | 24 |
| grid_attempts | 18 |
| trained_ok | 18 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | 3672 | 56.2% | 0.794 | 0.718 | 0.562 | 368 | 89.7% | 33.4% |
| at_fire | all | label.next_period.took_parent_low | 3672 | 43.4% | 0.757 | 0.685 | 0.566 | 368 | 80.4% | 37.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2000 | 29.9% | 0.746 | 0.736 | 0.701 | 200 | 68.5% | 38.6% |
| at_fire | bullish | label.next_period.took_parent_high | 2000 | 73.6% | 0.733 | 0.753 | 0.736 | 200 | 94.0% | 20.4% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2000 | 73.6% | 0.733 | 0.753 | 0.736 | 200 | 94.0% | 20.4% |
| at_fire | bearish | label.next_period.took_parent_high | 1662 | 35.6% | 0.724 | 0.697 | 0.644 | 167 | 67.1% | 31.5% |
| at_fire | all | label.next_period.thesis_confirmed | 3672 | 67.2% | 0.700 | 0.692 | 0.672 | 368 | 92.4% | 25.2% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 165 | 61.2% | 0.668 | 0.564 | 0.612 | 17 | 88.2% | 27.0% |
| at_fire | bearish | label.next_period.took_parent_low | 1662 | 59.6% | 0.664 | 0.633 | 0.596 | 167 | 86.2% | 26.7% |
| at_fire | bearish | label.next_period.thesis_confirmed | 1662 | 59.6% | 0.664 | 0.633 | 0.596 | 167 | 86.2% | 26.7% |
| at_fire | all | label.n_plus_2.took_parent_high | 390 | 70.8% | 0.663 | 0.731 | 0.708 | 39 | 79.5% | 8.7% |
| at_fire | all | label.n_plus_2.took_parent_low | 390 | 33.6% | 0.598 | 0.664 | 0.664 | 39 | 41.0% | 7.4% |
| at_fire | all | label.n_plus_2.thesis_confirmed | 390 | 62.3% | 0.593 | 0.633 | 0.623 | 39 | 74.4% | 12.1% |
| at_fire | bullish | label.n_plus_2.took_parent_high | 225 | 77.8% | 0.568 | 0.778 | 0.778 | 23 | 82.6% | 4.8% |
| at_fire | bullish | label.n_plus_2.thesis_confirmed | 225 | 77.8% | 0.568 | 0.778 | 0.778 | 23 | 82.6% | 4.8% |
| at_fire | bullish | label.n_plus_2.took_parent_low | 225 | 28.0% | 0.516 | 0.720 | 0.720 | 23 | 30.4% | 2.4% |
| at_fire | bearish | label.n_plus_2.took_parent_low | 165 | 41.2% | 0.394 | 0.448 | 0.588 | 17 | 35.3% | -5.9% |
| at_fire | bearish | label.n_plus_2.thesis_confirmed | 165 | 41.2% | 0.394 | 0.448 | 0.588 | 17 | 35.3% | -5.9% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | tp.ed.is_bearish_classic_po3=20083; fvggeom.age_min_same_primary_bearish_untouched_above=15829; fvggeom.age_min_same_primary_any_side_untouched_above=2636; xctx.n_fvg_side_bearish_24h=2566; tp.ed.parent_body_pts=2251; fvggeom.age_min_same_primary_bullish_untouched_below=2214; xctx.n_disp_side_bearish_24h=1823; xctx.minutes_since_last_smt_side_low_7d=1676; fvggeom.age_min_same_primary_any_side_tapped_above=1459; xctx.n_disp_side_bearish_4h=1336 |
| at_fire | all | label.next_period.took_parent_low | fvggeom.age_min_same_primary_bullish_untouched_below=26545; tp.ed.is_bullish_classic_po3=3544; tp.ed.is_bearish_classic_po3=2997; xctx.n_fvg_side_bullish_4h=2743; xctx.n_disp_side_bullish_24h=2393; fvggeom.age_min_same_primary_any_side_untouched_below=2302; tp.ed.parent_body_pts=1848; tp.side_bearish=1609; xctx.n_sweep_24h=1576; xctx.minutes_since_last_fvg_side_bearish_4h=1474 |
| at_fire | bullish | label.next_period.took_parent_low | fvggeom.age_min_same_primary_bullish_untouched_below=4952; tp.ed.parent_body_pts=3209; xctx.n_disp_side_bullish_24h=1685; xctx.n_fvg_side_bullish_4h=1601; fvggeom.age_min_any_symbol_bullish_untouched_below=1542; xctx.minutes_since_last_disp_side_bearish_24h=1186; xctx.minutes_since_last_swing_side_high_24h=1087; xctx.n_ob_side_bearish_7d=1036; xctx.n_vp_side_balanced_7d=1010; xctx.minutes_since_last_smt_side_high_7d=949 |
| at_fire | bullish | label.next_period.took_parent_high | fvggeom.age_min_any_symbol_bearish_untouched_above=3231; fvggeom.age_min_same_primary_bullish_untouched_below=1892; fvggeom.age_min_same_primary_bearish_untouched_above=1678; xctx.minutes_since_last_disp_side_bearish_24h=1059; xctx.n_fvg_side_bullish_4h=1027; xctx.n_swing_side_high_4h=1010; xctx.n_ob_side_bearish_7d=938; xctx.n_eql_side_low_7d=932; fvggeom.age_min_same_primary_any_side_untouched_below=791; xctx.n_fvg_side_bearish_7d=763 |
| at_fire | bullish | label.next_period.thesis_confirmed | fvggeom.age_min_any_symbol_bearish_untouched_above=3231; fvggeom.age_min_same_primary_bullish_untouched_below=1892; fvggeom.age_min_same_primary_bearish_untouched_above=1678; xctx.minutes_since_last_disp_side_bearish_24h=1059; xctx.n_fvg_side_bullish_4h=1027; xctx.n_swing_side_high_4h=1010; xctx.n_ob_side_bearish_7d=938; xctx.n_eql_side_low_7d=932; fvggeom.age_min_same_primary_any_side_untouched_below=791; xctx.n_fvg_side_bearish_7d=763 |
| at_fire | bearish | label.next_period.took_parent_high | fvggeom.age_min_same_primary_bearish_untouched_above=4222; tp.ed.parent_body_pts=3551; xctx.n_disp_side_bearish_24h=1923; xctx.n_fvg_side_bearish_24h=1632; xctx.minutes_since_last_swing_side_low_24h=1293; xctx.minutes_since_last_smt_side_low_7d=1036; fvggeom.age_min_same_primary_any_side_untouched_above=819; xctx.minutes_since_last_fvg_side_bearish_4h=725; xctx.n_eql_24h=584; xctx.n_fvg_side_bullish_7d=568 |
| at_fire | all | label.next_period.thesis_confirmed | fvggeom.age_min_same_primary_bullish_untouched_below=2800; fvggeom.age_min_any_symbol_bearish_untouched_above=2724; tp.ed.is_bullish_classic_po3=2157; tp.ed.parent_body_pts=1925; fvggeom.age_min_same_primary_bullish_closed_through_above=1376; xctx.minutes_since_last_fvg_side_bullish_24h=1330; fvggeom.age_min_same_primary_bearish_untouched_above=1198; xctx.minutes_since_last_disp_side_bearish_24h=1152; fvggeom.age_min_same_primary_any_side_closed_through_above=1117; xctx.n_fvg_24h=1076 |
| at_fire | bearish | label.n_plus_2.took_parent_high | xctx.minutes_since_last_psp_side_bearish_4h=211; fvggeom.age_min_same_primary_any_side_untouched_above=184; xctx.minutes_since_last_smt_side_high_7d=175; xctx.n_fvg_7d=174; fvggeom.age_min_same_primary_bearish_untouched_above=166; xctx.n_vp_side_buying_24h=158; xctx.n_disp_7d=156; xctx.n_swing_24h=151; xctx.n_ob_side_bearish_24h=144; xctx.n_disp_24h=132 |
| at_fire | bearish | label.next_period.took_parent_low | fvggeom.age_min_same_primary_bullish_untouched_below=6092; xctx.minutes_since_last_fvg_side_bearish_4h=1300; xctx.n_disp_side_bearish_4h=1153; xctx.n_disp_side_bullish_24h=992; xctx.n_fvg_24h=939; xctx.n_disp_side_bullish_1h=857; xctx.n_fvg_side_bearish_4h=856; xctx.n_disp_side_bearish_7d=809; xctx.minutes_since_last_swing_side_low_24h=788; xctx.n_psp_side_bullish_7d=783 |
| at_fire | bearish | label.next_period.thesis_confirmed | fvggeom.age_min_same_primary_bullish_untouched_below=6092; xctx.minutes_since_last_fvg_side_bearish_4h=1300; xctx.n_disp_side_bearish_4h=1153; xctx.n_disp_side_bullish_24h=992; xctx.n_fvg_24h=939; xctx.n_disp_side_bullish_1h=857; xctx.n_fvg_side_bearish_4h=856; xctx.n_disp_side_bearish_7d=809; xctx.minutes_since_last_swing_side_low_24h=788; xctx.n_psp_side_bullish_7d=783 |
| at_fire | all | label.n_plus_2.took_parent_high | xctx.n_fvg_side_bearish_7d=943; xctx.n_sweep_side_low_24h=441; xctx.minutes_since_last_ob_side_bearish_4h=289; xctx.minutes_since_last_smt_7d=256; xctx.n_fvg_7d=238; fvggeom.distance_pts_same_primary_bullish_fully_filled_above=203; xctx.minutes_since_last_eql_side_low_24h=197; xctx.n_sweep_side_high_24h=187; xctx.n_ob_side_bearish_24h=175; xctx.minutes_since_last_psp_side_bullish_24h=166 |
| at_fire | all | label.n_plus_2.took_parent_low | xctx.n_sweep_side_low_24h=896; xctx.minutes_since_last_smt_side_high_7d=430; xctx.n_sweep_side_low_7d=310; fvggeom.age_min_same_primary_bearish_fully_filled_below=252; ts.year=218; xctx.minutes_since_last_smt_side_low_7d=196; xctx.n_vp_side_balanced_7d=194; tp.year=180; xctx.minutes_since_last_smt_7d=175; xctx.minutes_since_last_psp_side_bullish_24h=163 |
| at_fire | all | label.n_plus_2.thesis_confirmed | tp.side_bearish=1086; ts.year=455; fvggeom.distance_pts_same_primary_bullish_fully_filled_above=369; xctx.n_sweep_side_high_24h=367; xctx.minutes_since_last_smt_side_high_7d=303; xctx.n_disp_7d=274; xctx.n_fvg_side_bullish_7d=233; xctx.n_swing_24h=231; xctx.n_vp_side_balanced_7d=229; xctx.minutes_since_last_ob_side_bullish_7d=200 |
| at_fire | bullish | label.n_plus_2.took_parent_high | xctx.n_sweep_side_high_24h=404; ts.year=202; xctx.n_ft_side_bullish_24h=144; fvggeom.distance_pts_same_primary_bullish_fully_filled_above=107; xctx.minutes_since_last_smt_7d=94; xctx.minutes_since_last_psp_side_bullish_24h=90; xctx.minutes_since_last_smt_side_low_7d=60; xctx.n_eql_side_high_7d=58; xctx.n_disp_24h=56; fvggeom.width_pts_any_symbol_bearish_fully_filled_above=54 |
| at_fire | bullish | label.n_plus_2.thesis_confirmed | xctx.n_sweep_side_high_24h=404; ts.year=202; xctx.n_ft_side_bullish_24h=144; fvggeom.distance_pts_same_primary_bullish_fully_filled_above=107; xctx.minutes_since_last_smt_7d=94; xctx.minutes_since_last_psp_side_bullish_24h=90; xctx.minutes_since_last_smt_side_low_7d=60; xctx.n_eql_side_high_7d=58; xctx.n_disp_24h=56; fvggeom.width_pts_any_symbol_bearish_fully_filled_above=54 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
