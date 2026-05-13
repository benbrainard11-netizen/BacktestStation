# ML snapshot leaderboard

_Generated `2026-05-12T14:35:32.103149+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshots_xctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `13` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 46331 |
| schema_feature_columns | 650 |
| schema_label_columns | 226 |
| grid_attempts | 39 |
| trained_ok | 39 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.level_tags.open.wick_tapped | 8764 | 95.3% | 0.876 | 0.952 | 0.953 | 877 | 100.0% | 4.7% |
| at_fire | bearish | label.level_tags.open.wick_tapped | 4679 | 96.2% | 0.866 | 0.962 | 0.962 | 468 | 100.0% | 3.8% |
| at_fire | bullish | label.level_tags.open.wick_tapped | 4085 | 94.2% | 0.863 | 0.942 | 0.942 | 409 | 99.5% | 5.3% |
| at_fire | all | label.level_tags.q25.wick_tapped | 8764 | 94.5% | 0.862 | 0.945 | 0.945 | 877 | 99.9% | 5.4% |
| at_fire | bearish | label.level_tags.q25.wick_tapped | 4679 | 95.6% | 0.855 | 0.957 | 0.956 | 468 | 100.0% | 4.4% |
| at_fire | bullish | label.level_tags.q25.wick_tapped | 4085 | 93.2% | 0.841 | 0.932 | 0.932 | 409 | 100.0% | 6.8% |
| at_fire | bearish | label.level_tags.q50.wick_tapped | 4679 | 94.9% | 0.835 | 0.949 | 0.949 | 468 | 99.8% | 4.9% |
| at_fire | all | label.level_tags.q50.wick_tapped | 8764 | 93.3% | 0.825 | 0.934 | 0.933 | 877 | 99.8% | 6.4% |
| at_fire | bearish | label.level_tags.q75.wick_tapped | 4679 | 94.0% | 0.796 | 0.941 | 0.940 | 468 | 99.1% | 5.2% |
| at_fire | bullish | label.level_tags.q50.wick_tapped | 4085 | 91.6% | 0.796 | 0.917 | 0.916 | 409 | 99.3% | 7.7% |
| at_fire | all | label.level_tags.q75.wick_tapped | 8764 | 91.9% | 0.781 | 0.919 | 0.919 | 877 | 99.5% | 7.7% |
| at_fire | bearish | label.level_tags.open.close_past | 4679 | 91.9% | 0.762 | 0.920 | 0.919 | 468 | 97.6% | 5.7% |
| at_fire | all | label.level_tags.open.close_past | 8764 | 89.6% | 0.759 | 0.896 | 0.896 | 877 | 98.4% | 8.8% |
| at_fire | bearish | label.level_tags.q25.close_past | 4679 | 91.0% | 0.752 | 0.911 | 0.910 | 468 | 98.3% | 7.3% |
| at_fire | bearish | label.level_tags.close.wick_tapped | 4679 | 92.0% | 0.749 | 0.923 | 0.920 | 468 | 98.7% | 6.7% |
| at_fire | bullish | label.level_tags.q75.wick_tapped | 4085 | 89.4% | 0.740 | 0.893 | 0.894 | 409 | 97.8% | 8.4% |
| at_fire | all | label.level_tags.q25.close_past | 8764 | 88.2% | 0.739 | 0.884 | 0.882 | 877 | 96.8% | 8.6% |
| at_fire | all | label.level_tags.close.wick_tapped | 8764 | 89.2% | 0.737 | 0.894 | 0.892 | 877 | 98.1% | 8.9% |
| at_fire | bullish | label.level_tags.open.close_past | 4085 | 86.9% | 0.730 | 0.869 | 0.869 | 409 | 95.6% | 8.7% |
| at_fire | bearish | label.level_tags.q50.close_past | 4679 | 89.8% | 0.724 | 0.899 | 0.898 | 468 | 97.9% | 8.0% |
| at_fire | all | label.level_tags.q50.close_past | 8764 | 86.4% | 0.701 | 0.866 | 0.864 | 877 | 94.8% | 8.3% |
| at_fire | bearish | label.level_tags.range_far.wick_tapped | 4679 | 88.1% | 0.697 | 0.884 | 0.881 | 468 | 97.0% | 8.9% |
| at_fire | all | label.level_tags.range_far.wick_tapped | 8764 | 84.0% | 0.695 | 0.843 | 0.840 | 877 | 94.8% | 10.7% |
| at_fire | bullish | label.level_tags.close.wick_tapped | 4085 | 86.0% | 0.693 | 0.861 | 0.860 | 409 | 94.9% | 8.9% |
| at_fire | bullish | label.level_tags.q25.close_past | 4085 | 85.0% | 0.689 | 0.851 | 0.850 | 409 | 96.1% | 11.0% |
| at_fire | bearish | label.level_tags.range_far.close_past | 4679 | 82.2% | 0.678 | 0.827 | 0.822 | 468 | 92.9% | 10.8% |
| at_fire | bearish | label.level_tags.q75.close_past | 4679 | 87.7% | 0.676 | 0.879 | 0.877 | 468 | 95.9% | 8.2% |
| at_fire | all | label.level_tags.q75.close_past | 8764 | 83.8% | 0.676 | 0.839 | 0.838 | 877 | 94.4% | 10.6% |
| at_fire | bearish | label.invalidation.invalidated | 4679 | 85.6% | 0.672 | 0.860 | 0.856 | 468 | 94.4% | 8.8% |
| at_fire | all | label.level_tags.close.close_past | 8764 | 80.9% | 0.669 | 0.813 | 0.809 | 877 | 93.2% | 12.3% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.level_tags.open.wick_tapped | ob.ed.confirms_close_gt_ob_high=26749; ob.ed.confirms_close_gt_ob_open=16625; xctx.minutes_since_last_tp_24h=1535; ob.ed.bars_back_to_ob=1342; xctx.n_fvg_7d=1202; xctx.minutes_since_last_orb_side_doji_7d=1173; xctx.minutes_since_last_psp_side_bearish_24h=1166; xctx.n_eql_side_high_7d=1133; xctx.minutes_since_last_smt_side_low_7d=1115; xctx.n_fvg_side_bullish_7d=1055 |
| at_fire | bearish | label.level_tags.open.wick_tapped | ob.ed.confirms_close_gt_ob_high=11708; ob.ed.confirms_close_gt_ob_open=8257; xctx.minutes_since_last_orb_side_doji_7d=900; xctx.n_fvg_7d=800; xctx.n_swing_side_high_7d=762; xctx.n_fvg_side_bullish_7d=761; ob.hour_of_day_utc=746; xctx.minutes_since_last_sweep_side_low_24h=717; xctx.n_sweep_7d=694; xctx.minutes_since_last_fvg_side_bullish_24h=681 |
| at_fire | bullish | label.level_tags.open.wick_tapped | ob.ed.confirms_close_gt_ob_open=12633; ob.ed.confirms_close_gt_ob_high=10810; xctx.minutes_since_last_orb_side_doji_7d=1400; xctx.minutes_since_last_smt_side_high_7d=946; xctx.n_fvg_side_bullish_7d=899; xctx.n_eql_side_high_7d=877; ob.ed.bars_back_to_ob=857; xctx.n_disp_side_bearish_7d=819; xctx.n_fvg_side_bearish_24h=819; xctx.minutes_since_last_smt_side_low_7d=806 |
| at_fire | all | label.level_tags.q25.wick_tapped | ob.ed.confirms_close_gt_ob_high=23122; ob.ed.confirms_close_gt_ob_open=20378; ob.ed.bars_back_to_ob=1899; xctx.minutes_since_last_tp_24h=1639; xctx.minutes_since_last_orb_side_doji_7d=1611; xctx.n_fvg_side_bearish_24h=1576; xctx.n_eql_side_high_7d=1413; xctx.minutes_since_last_smt_side_low_7d=1360; xctx.n_sweep_side_low_7d=1260; xctx.n_fvg_7d=1241 |
| at_fire | bearish | label.level_tags.q25.wick_tapped | ob.ed.confirms_close_gt_ob_high=11056; ob.ed.confirms_close_gt_ob_open=8389; xctx.minutes_since_last_orb_side_doji_7d=1057; xctx.minutes_since_last_disp_side_bearish_24h=803; xctx.n_fvg_side_bullish_7d=778; xctx.n_fvg_side_bullish_24h=740; xctx.n_fvg_7d=739; ob.event_type_swept_ny_high_1h=642; xctx.n_vp_side_balanced_7d=637; xctx.minutes_since_last_tp_24h=631 |
| at_fire | bullish | label.level_tags.q25.wick_tapped | ob.ed.confirms_close_gt_ob_open=16829; ob.ed.confirms_close_gt_ob_high=7129; xctx.minutes_since_last_smt_side_high_7d=1316; xctx.minutes_since_last_psp_side_bearish_24h=1101; xctx.n_eql_side_low_7d=989; ob.ed.bars_back_to_ob=965; xctx.minutes_since_last_orb_side_doji_7d=950; xctx.n_disp_side_bearish_7d=916; xctx.n_eql_side_high_7d=830; xctx.n_fvg_side_bearish_24h=817 |
| at_fire | bearish | label.level_tags.q50.wick_tapped | ob.ed.confirms_close_gt_ob_high=11046; ob.ed.confirms_close_gt_ob_open=5253; xctx.minutes_since_last_tp_24h=1165; xctx.minutes_since_last_orb_side_doji_7d=960; xctx.n_disp_side_bullish_7d=843; xctx.n_eql_7d=829; xctx.n_eql_side_high_7d=751; xctx.n_fvg_side_bullish_7d=690; xctx.n_fvg_side_bullish_24h=621; xctx.minutes_since_last_disp_side_bearish_24h=568 |
| at_fire | all | label.level_tags.q50.wick_tapped | ob.ed.confirms_close_gt_ob_high=21518; ob.ed.confirms_close_gt_ob_open=15050; xctx.minutes_since_last_tp_24h=1995; ob.ed.bars_back_to_ob=1929; xctx.minutes_since_last_psp_side_bearish_24h=1438; xctx.n_fvg_side_bullish_7d=1378; xctx.minutes_since_last_orb_side_doji_7d=1281; xctx.n_orb_side_bullish_7d=1276; xctx.minutes_since_last_smt_side_high_7d=1262; xctx.minutes_since_last_vp_side_buying_24h=1219 |
| at_fire | bearish | label.level_tags.q75.wick_tapped | ob.ed.confirms_close_gt_ob_high=8750; ob.ed.confirms_close_gt_ob_open=4171; xctx.n_fvg_side_bullish_7d=1217; xctx.n_eql_7d=1062; xctx.minutes_since_last_tp_24h=1024; xctx.minutes_since_last_sweep_side_low_24h=923; xctx.minutes_since_last_smt_side_high_7d=906; xctx.n_vp_side_balanced_7d=905; ob.event_type_swept_ny_high_1h=900; xctx.n_sweep_7d=853 |
| at_fire | bullish | label.level_tags.q50.wick_tapped | ob.ed.confirms_close_gt_ob_open=13192; ob.ed.confirms_close_gt_ob_high=6924; xctx.minutes_since_last_smt_side_high_7d=1439; xctx.minutes_since_last_psp_side_bearish_24h=1210; ob.ed.bars_back_to_ob=1150; xctx.n_eql_side_high_7d=1080; xctx.n_fvg_side_bearish_24h=863; xctx.n_fvg_side_bearish_7d=837; xctx.minutes_since_last_tp_24h=780; xctx.n_vp_side_buying_7d=757 |
| at_fire | all | label.level_tags.q75.wick_tapped | ob.ed.confirms_close_gt_ob_high=19340; ob.ed.confirms_close_gt_ob_open=8248; xctx.minutes_since_last_tp_24h=2331; ob.ed.bars_back_to_ob=1898; xctx.n_disp_side_bearish_7d=1726; xctx.minutes_since_last_orb_side_doji_7d=1618; xctx.n_fvg_side_bullish_7d=1432; xctx.n_eql_side_high_7d=1345; xctx.minutes_since_last_psp_side_bearish_24h=1312; xctx.minutes_since_last_smt_side_high_7d=1301 |
| at_fire | bearish | label.level_tags.open.close_past | ob.ed.confirms_close_gt_ob_high=9280; ob.ed.confirms_close_gt_ob_open=4849; xctx.n_fvg_side_bullish_24h=1085; xctx.n_fvg_side_bullish_7d=1061; xctx.n_sweep_7d=1006; xctx.minutes_since_last_smt_side_low_7d=991; xctx.minutes_since_last_tp_24h=961; xctx.n_disp_side_bullish_7d=937; xctx.n_eql_side_high_7d=905; xctx.minutes_since_last_smt_side_high_7d=895 |
| at_fire | all | label.level_tags.open.close_past | ob.ed.confirms_close_gt_ob_high=17049; ob.ed.confirms_close_gt_ob_open=14599; xctx.n_fvg_side_bullish_7d=1679; xctx.minutes_since_last_orb_side_doji_7d=1402; xctx.minutes_since_last_tp_24h=1366; ob.side_bearish=1363; xctx.n_fvg_side_bearish_24h=1303; xctx.total_events_7d=1257; ob.ctx.day_of_week_et=1254; xctx.n_disp_side_bullish_7d=1252 |
| at_fire | bearish | label.level_tags.q25.close_past | ob.ed.confirms_close_gt_ob_high=8715; ob.ed.confirms_close_gt_ob_open=3690; xctx.n_fvg_side_bullish_7d=1144; xctx.n_sweep_7d=1119; xctx.minutes_since_last_tp_24h=1075; xctx.n_eql_side_low_7d=949; xctx.minutes_since_last_smt_side_high_7d=887; xctx.n_eql_side_high_7d=835; xctx.n_eql_7d=811; xctx.total_events_7d=806 |
| at_fire | bearish | label.level_tags.close.wick_tapped | ob.ed.confirms_close_gt_ob_high=6807; xctx.n_fvg_side_bullish_7d=1660; ob.ed.confirms_close_gt_ob_open=1659; xctx.n_eql_side_low_7d=1468; xctx.n_vp_side_balanced_7d=1235; xctx.minutes_since_last_tp_24h=1159; xctx.n_sweep_7d=1092; ob.ed.ob_body_width_pts=1087; xctx.minutes_since_last_orb_side_doji_7d=1054; xctx.n_disp_7d=1025 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
