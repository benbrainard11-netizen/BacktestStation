# ML snapshot leaderboard

_Generated `2026-05-12T14:36:53.283702+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots_xctx.schema.json`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 19414 |
| schema_feature_columns | 626 |
| schema_label_columns | 24 |
| grid_attempts | 18 |
| trained_ok | 18 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | 3672 | 56.2% | 0.782 | 0.717 | 0.562 | 368 | 89.9% | 33.7% |
| at_fire | all | label.next_period.took_parent_low | 3672 | 43.4% | 0.750 | 0.684 | 0.566 | 368 | 78.5% | 35.1% |
| at_fire | bullish | label.next_period.took_parent_low | 2000 | 29.9% | 0.728 | 0.728 | 0.701 | 200 | 62.5% | 32.6% |
| at_fire | bearish | label.next_period.took_parent_high | 1662 | 35.6% | 0.714 | 0.676 | 0.644 | 167 | 61.1% | 25.5% |
| at_fire | bullish | label.next_period.took_parent_high | 2000 | 73.6% | 0.700 | 0.750 | 0.736 | 200 | 93.5% | 19.9% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2000 | 73.6% | 0.700 | 0.750 | 0.736 | 200 | 93.5% | 19.9% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 165 | 61.2% | 0.674 | 0.612 | 0.612 | 17 | 58.8% | -2.4% |
| at_fire | all | label.next_period.thesis_confirmed | 3672 | 67.2% | 0.668 | 0.685 | 0.672 | 368 | 91.6% | 24.4% |
| at_fire | bearish | label.next_period.took_parent_low | 1662 | 59.6% | 0.642 | 0.632 | 0.596 | 167 | 81.4% | 21.9% |
| at_fire | bearish | label.next_period.thesis_confirmed | 1662 | 59.6% | 0.642 | 0.632 | 0.596 | 167 | 81.4% | 21.9% |
| at_fire | all | label.n_plus_2.thesis_confirmed | 390 | 62.3% | 0.637 | 0.626 | 0.623 | 39 | 76.9% | 14.6% |
| at_fire | all | label.n_plus_2.took_parent_high | 390 | 70.8% | 0.620 | 0.744 | 0.708 | 39 | 87.2% | 16.4% |
| at_fire | bullish | label.n_plus_2.took_parent_high | 225 | 77.8% | 0.619 | 0.778 | 0.778 | 23 | 95.7% | 17.9% |
| at_fire | bullish | label.n_plus_2.thesis_confirmed | 225 | 77.8% | 0.619 | 0.778 | 0.778 | 23 | 95.7% | 17.9% |
| at_fire | all | label.n_plus_2.took_parent_low | 390 | 33.6% | 0.560 | 0.613 | 0.664 | 39 | 48.7% | 15.1% |
| at_fire | bullish | label.n_plus_2.took_parent_low | 225 | 28.0% | 0.458 | 0.720 | 0.720 | 23 | 43.5% | 15.5% |
| at_fire | bearish | label.n_plus_2.took_parent_low | 165 | 41.2% | 0.430 | 0.473 | 0.588 | 17 | 23.5% | -17.7% |
| at_fire | bearish | label.n_plus_2.thesis_confirmed | 165 | 41.2% | 0.430 | 0.473 | 0.588 | 17 | 23.5% | -17.7% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | tp.ed.is_bearish_classic_po3=23597; tp.side_bearish=6723; tp.ed.parent_body_pts=4665; xctx.n_disp_side_bearish_24h=2679; xctx.n_fvg_side_bullish_4h=2447; xctx.minutes_since_last_fvg_side_bearish_24h=2413; xctx.minutes_since_last_fvg_side_bullish_24h=2189; xctx.minutes_since_last_smt_side_low_7d=1918; xctx.n_fvg_side_bearish_24h=1859; tp.ed.is_bullish_classic_po3=1751 |
| at_fire | all | label.next_period.took_parent_low | tp.ed.is_bullish_classic_po3=12030; xctx.n_fvg_side_bullish_4h=5696; tp.side_bearish=5691; tp.side_bullish=4667; xctx.n_disp_side_bullish_24h=3435; tp.ed.parent_body_pts=3090; xctx.n_fvg_side_bullish_1h=2982; xctx.n_disp_side_bullish_1h=2837; xctx.minutes_since_last_fvg_side_bullish_24h=2296; xctx.n_disp_side_bearish_4h=2087 |
| at_fire | bullish | label.next_period.took_parent_low | tp.ed.parent_body_pts=3936; xctx.n_fvg_side_bullish_4h=3665; xctx.n_disp_side_bullish_24h=1863; xctx.n_fvg_side_bullish_1h=1502; xctx.minutes_since_last_disp_side_bearish_24h=1396; xctx.minutes_since_last_swing_side_high_24h=836; xctx.minutes_since_last_smt_side_high_7d=792; xctx.minutes_since_last_fvg_side_bullish_24h=748; xctx.n_eql_side_low_7d=743; xctx.minutes_since_last_smt_side_low_7d=710 |
| at_fire | bearish | label.next_period.took_parent_high | tp.ed.parent_body_pts=6170; xctx.n_disp_side_bearish_24h=3270; xctx.minutes_since_last_swing_side_low_24h=1555; xctx.minutes_since_last_smt_side_low_7d=1528; xctx.n_fvg_side_bearish_24h=1228; xctx.minutes_since_last_fvg_side_bearish_24h=1140; xctx.minutes_since_last_fvg_side_bearish_4h=1124; xctx.minutes_since_last_smt_side_high_7d=933; xctx.n_fvg_side_bullish_7d=833; xctx.minutes_since_last_orb_side_doji_7d=818 |
| at_fire | bullish | label.next_period.took_parent_high | xctx.n_fvg_side_bullish_4h=2855; xctx.minutes_since_last_fvg_side_bullish_24h=1590; xctx.n_fvg_24h=1285; xctx.minutes_since_last_disp_side_bearish_24h=1253; tp.ed.high_sub_period_london=1231; xctx.has_disp_side_bearish_1h=1192; xctx.n_eql_side_low_7d=1072; xctx.n_vp_side_balanced_7d=1025; xctx.n_ob_side_bearish_7d=960; tp.ed.parent_body_pts=814 |
| at_fire | bullish | label.next_period.thesis_confirmed | xctx.n_fvg_side_bullish_4h=2855; xctx.minutes_since_last_fvg_side_bullish_24h=1590; xctx.n_fvg_24h=1285; xctx.minutes_since_last_disp_side_bearish_24h=1253; tp.ed.high_sub_period_london=1231; xctx.has_disp_side_bearish_1h=1192; xctx.n_eql_side_low_7d=1072; xctx.n_vp_side_balanced_7d=1025; xctx.n_ob_side_bearish_7d=960; tp.ed.parent_body_pts=814 |
| at_fire | bearish | label.n_plus_2.took_parent_high | xctx.n_fvg_7d=34; xctx.n_disp_7d=28; xctx.minutes_since_last_ob_side_bearish_24h=27; xctx.n_disp_24h=19; xctx.n_psp_side_bearish_7d=17; xctx.n_fvg_side_bullish_7d=15; xctx.minutes_since_last_smt_side_high_7d=13; xctx.total_events_24h=11; xctx.minutes_since_last_eql_24h=11; xctx.minutes_since_last_ob_same_primary_24h=6 |
| at_fire | all | label.next_period.thesis_confirmed | tp.ed.parent_body_pts=3414; xctx.minutes_since_last_fvg_side_bullish_24h=2595; tp.ed.is_bullish_classic_po3=2405; xctx.n_fvg_side_bullish_24h=1839; xctx.minutes_since_last_disp_side_bearish_24h=1823; xctx.has_disp_side_bearish_1h=1721; xctx.n_fvg_side_bullish_4h=1637; xctx.n_fvg_side_bearish_4h=1506; xctx.minutes_since_last_fvg_side_bearish_24h=1489; xctx.n_fvg_side_bearish_7d=1489 |
| at_fire | bearish | label.next_period.took_parent_low | xctx.n_fvg_side_bullish_4h=2352; xctx.n_disp_side_bullish_1h=1899; xctx.n_fvg_side_bearish_4h=1606; xctx.minutes_since_last_disp_side_bearish_7d=1310; xctx.minutes_since_last_fvg_side_bearish_4h=1268; xctx.n_fvg_side_bullish_1h=1197; xctx.n_fvg_24h=1159; xctx.n_disp_side_bearish_4h=1125; xctx.n_disp_side_bullish_24h=1010; xctx.minutes_since_last_orb_side_doji_7d=1001 |
| at_fire | bearish | label.next_period.thesis_confirmed | xctx.n_fvg_side_bullish_4h=2352; xctx.n_disp_side_bullish_1h=1899; xctx.n_fvg_side_bearish_4h=1606; xctx.minutes_since_last_disp_side_bearish_7d=1310; xctx.minutes_since_last_fvg_side_bearish_4h=1268; xctx.n_fvg_side_bullish_1h=1197; xctx.n_fvg_24h=1159; xctx.n_disp_side_bearish_4h=1125; xctx.n_disp_side_bullish_24h=1010; xctx.minutes_since_last_orb_side_doji_7d=1001 |
| at_fire | all | label.n_plus_2.thesis_confirmed | tp.side_bearish=987; ts.year=318; xctx.n_sweep_side_high_24h=308; xctx.n_disp_7d=217; xctx.minutes_since_last_smt_side_high_7d=200; tp.ed.parent_direction_bearish=200; xctx.minutes_since_last_ob_side_bullish_7d=199; xctx.n_fvg_side_bullish_7d=196; xctx.n_ft_side_bearish_7d=168; xctx.n_fvg_7d=167 |
| at_fire | all | label.n_plus_2.took_parent_high | xctx.n_fvg_side_bearish_7d=1057; xctx.n_sweep_side_low_24h=328; xctx.minutes_since_last_ob_side_bearish_4h=283; ts.year=248; xctx.n_fvg_7d=233; xctx.minutes_since_last_eql_side_low_24h=223; xctx.minutes_since_last_ob_side_bearish_24h=202; xctx.n_sweep_side_high_24h=184; xctx.n_ob_side_bearish_24h=179; xctx.n_eql_side_high_24h=178 |
| at_fire | bullish | label.n_plus_2.took_parent_high | xctx.n_sweep_side_high_24h=458; ts.year=296; xctx.minutes_since_last_psp_side_bullish_24h=164; xctx.minutes_since_last_smt_7d=160; xctx.total_events_7d=147; xctx.n_eql_side_high_24h=120; xctx.n_fvg_side_bearish_7d=113; xctx.n_ob_side_bearish_24h=113; xctx.minutes_since_last_eql_side_low_24h=109; xctx.n_fvg_7d=100 |
| at_fire | bullish | label.n_plus_2.thesis_confirmed | xctx.n_sweep_side_high_24h=458; ts.year=296; xctx.minutes_since_last_psp_side_bullish_24h=164; xctx.minutes_since_last_smt_7d=160; xctx.total_events_7d=147; xctx.n_eql_side_high_24h=120; xctx.n_fvg_side_bearish_7d=113; xctx.n_ob_side_bearish_24h=113; xctx.minutes_since_last_eql_side_low_24h=109; xctx.n_fvg_7d=100 |
| at_fire | all | label.n_plus_2.took_parent_low | xctx.n_sweep_side_low_24h=991; xctx.minutes_since_last_smt_7d=322; xctx.minutes_since_last_smt_side_high_7d=291; xctx.minutes_since_last_smt_side_low_7d=270; xctx.minutes_since_last_psp_side_bullish_24h=256; xctx.n_sweep_side_low_7d=241; tp.year=240; xctx.n_fvg_side_bearish_24h=237; ts.year=215; xctx.n_sweep_side_high_24h=209 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
