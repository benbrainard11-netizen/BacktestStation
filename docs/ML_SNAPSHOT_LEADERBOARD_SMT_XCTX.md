# ML snapshot leaderboard

_Generated `2026-05-12T04:25:07.503991+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots_xctx.schema.json`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 873 |
| schema_label_columns | 18 |
| grid_attempts | 60 |
| trained_ok | 60 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | low | label.n1_primary_took_period_n_low | 251 | 48.2% | 0.941 | 0.869 | 0.518 | 26 | 100.0% | 51.8% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 277 | 43.3% | 0.936 | 0.852 | 0.567 | 28 | 100.0% | 56.7% |
| at_period_close | high | label.n1_primary_took_period_n_low | 277 | 43.3% | 0.936 | 0.852 | 0.567 | 28 | 100.0% | 56.7% |
| at_period_close | all | label.n1_close_moved_with_thesis | 528 | 46.8% | 0.935 | 0.845 | 0.532 | 53 | 100.0% | 53.2% |
| at_period_close | all | label.n1_primary_took_period_n_low | 528 | 45.6% | 0.930 | 0.841 | 0.544 | 53 | 100.0% | 54.4% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 528 | 46.2% | 0.929 | 0.852 | 0.538 | 53 | 100.0% | 53.8% |
| at_period_close | high | label.n1_close_moved_with_thesis | 277 | 43.7% | 0.926 | 0.841 | 0.563 | 28 | 100.0% | 56.3% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 251 | 49.4% | 0.926 | 0.837 | 0.506 | 26 | 100.0% | 50.6% |
| at_period_close | low | label.n1_primary_took_period_n_high | 251 | 49.4% | 0.926 | 0.837 | 0.506 | 26 | 100.0% | 50.6% |
| at_period_close | high | label.n1_primary_took_period_n_high | 277 | 56.3% | 0.924 | 0.834 | 0.563 | 28 | 100.0% | 43.7% |
| at_period_close | low | label.n1_close_moved_with_thesis | 251 | 50.2% | 0.923 | 0.833 | 0.498 | 26 | 100.0% | 49.8% |
| at_period_close | all | label.n1_primary_took_period_n_high | 528 | 53.0% | 0.918 | 0.826 | 0.530 | 53 | 100.0% | 47.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 528 | 59.3% | 0.882 | 0.799 | 0.593 | 53 | 98.1% | 38.8% |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | 528 | 60.0% | 0.881 | 0.794 | 0.600 | 53 | 100.0% | 40.0% |
| at_period_close | low | label.n1_or_n2_close_moved_with_thesis | 251 | 64.9% | 0.880 | 0.817 | 0.649 | 26 | 100.0% | 35.1% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 277 | 55.6% | 0.880 | 0.780 | 0.556 | 28 | 100.0% | 44.4% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 277 | 54.2% | 0.870 | 0.791 | 0.542 | 28 | 100.0% | 45.8% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 251 | 64.9% | 0.862 | 0.813 | 0.649 | 26 | 100.0% | 35.1% |
| at_period_close | all | label.n2_close_moved_with_thesis | 518 | 45.9% | 0.749 | 0.685 | 0.541 | 52 | 84.6% | 38.7% |
| at_period_close | low | label.n2_primary_took_period_n_low | 244 | 46.7% | 0.746 | 0.693 | 0.533 | 25 | 92.0% | 45.3% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 518 | 46.1% | 0.737 | 0.670 | 0.539 | 52 | 80.8% | 34.6% |
| at_period_close | low | label.n2_close_moved_with_thesis | 244 | 53.7% | 0.737 | 0.643 | 0.537 | 25 | 92.0% | 38.3% |
| at_period_close | high | label.n2_close_moved_with_thesis | 274 | 39.1% | 0.731 | 0.682 | 0.609 | 28 | 85.7% | 46.7% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 274 | 40.5% | 0.729 | 0.697 | 0.595 | 28 | 78.6% | 38.1% |
| at_period_close | high | label.n2_primary_took_period_n_low | 274 | 40.5% | 0.729 | 0.697 | 0.595 | 28 | 78.6% | 38.1% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 244 | 52.5% | 0.729 | 0.639 | 0.525 | 25 | 88.0% | 35.5% |
| at_period_close | low | label.n2_primary_took_period_n_high | 244 | 52.5% | 0.729 | 0.639 | 0.525 | 25 | 88.0% | 35.5% |
| at_period_close | all | label.n2_primary_took_period_n_low | 518 | 43.4% | 0.725 | 0.683 | 0.566 | 52 | 73.1% | 29.6% |
| at_period_close | high | label.n2_primary_took_period_n_high | 274 | 59.9% | 0.722 | 0.661 | 0.599 | 28 | 92.9% | 33.0% |
| at_period_close | all | label.n2_primary_took_period_n_high | 518 | 56.4% | 0.720 | 0.656 | 0.564 | 52 | 90.4% | 34.0% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_period_close | low | label.n1_primary_took_period_n_low | xctx.n_disp_side_bearish_24h=2556; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1237; xctx.n_fvg_side_bearish_24h=915; pc.minutes_since_last_sweep_low_same_primary_in_window=647; pc.n_1h_fvg_bullish_same_primary_in_window=615; xctx.n_fvg_side_bullish_4h=499; xctx.minutes_since_last_sweep_side_high_24h=498; pc.n_sweep_ny_low_1h_low_same_primary_in_window=497; xctx.n_fvg_side_bearish_4h=322; xctx.minutes_since_last_sweep_side_low_24h=288 |
| at_period_close | high | label.n1_thesis_confirmed_strict | pc.n_1h_disp_bearish_same_primary_in_window=2030; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1495; pc.n_1h_fvg_bearish_same_primary_in_window=916; xctx.n_fvg_side_bullish_24h=851; pc.minutes_since_last_sweep_high_same_primary_in_window=752; xctx.n_fvg_side_bearish_4h=714; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=518; xctx.minutes_since_last_sweep_side_low_24h=401; xctx.minutes_since_last_sweep_side_high_24h=365; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=333 |
| at_period_close | high | label.n1_primary_took_period_n_low | pc.n_1h_disp_bearish_same_primary_in_window=2030; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1495; pc.n_1h_fvg_bearish_same_primary_in_window=916; xctx.n_fvg_side_bullish_24h=851; pc.minutes_since_last_sweep_high_same_primary_in_window=752; xctx.n_fvg_side_bearish_4h=714; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=518; xctx.minutes_since_last_sweep_side_low_24h=401; xctx.minutes_since_last_sweep_side_high_24h=365; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=333 |
| at_period_close | all | label.n1_close_moved_with_thesis | pc.n_1h_disp_bearish_same_primary_in_window=1839; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1562; pc.n_1h_fvg_bullish_same_primary_in_window=1561; xctx.n_disp_side_bearish_24h=1292; pc.minutes_since_last_sweep_high_same_primary_in_window=1218; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1190; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=1038; pc.minutes_since_last_sweep_low_same_primary_in_window=828; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=780; xctx.minutes_since_last_sweep_side_low_24h=760 |
| at_period_close | all | label.n1_primary_took_period_n_low | xctx.n_disp_side_bearish_24h=5514; xctx.n_fvg_side_bearish_4h=1539; xctx.minutes_since_last_sweep_side_low_24h=1352; xctx.minutes_since_last_sweep_side_high_24h=1265; xctx.n_fvg_side_bullish_24h=1105; xctx.n_fvg_side_bullish_4h=1099; xctx.minutes_since_last_fvg_side_bearish_24h=1098; xctx.n_fvg_side_bearish_24h=863; pc.minutes_since_last_sweep_high_same_primary_in_window=524; xctx.n_disp_side_bullish_24h=513 |
| at_period_close | all | label.n1_thesis_confirmed_strict | pc.n_1h_disp_bearish_same_primary_in_window=2262; xctx.n_disp_side_bearish_24h=1456; pc.n_1h_fvg_bullish_same_primary_in_window=1432; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1393; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1334; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=1093; pc.minutes_since_last_sweep_high_same_primary_in_window=918; pc.minutes_since_last_sweep_low_same_primary_in_window=917; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=741; xctx.n_fvg_side_bearish_4h=732 |
| at_period_close | high | label.n1_close_moved_with_thesis | pc.n_1h_disp_bearish_same_primary_in_window=2404; pc.minutes_since_last_sweep_high_same_primary_in_window=1043; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1034; xctx.n_fvg_side_bullish_24h=893; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=699; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=635; xctx.minutes_since_last_sweep_side_low_24h=543; xctx.n_fvg_side_bullish_4h=501; pc.n_15m_fvg_bearish_same_primary_in_window=411; xctx.n_fvg_side_bearish_4h=366 |
| at_period_close | low | label.n1_thesis_confirmed_strict | xctx.n_disp_side_bearish_24h=2266; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1123; xctx.n_fvg_side_bearish_24h=1092; pc.minutes_since_last_sweep_low_same_primary_in_window=999; pc.n_1h_fvg_bullish_same_primary_in_window=790; xctx.minutes_since_last_sweep_side_high_24h=443; xctx.n_fvg_side_bearish_4h=418; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=360; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=314; xctx.n_fvg_side_bullish_24h=295 |
| at_period_close | low | label.n1_primary_took_period_n_high | xctx.n_disp_side_bearish_24h=2266; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1123; xctx.n_fvg_side_bearish_24h=1092; pc.minutes_since_last_sweep_low_same_primary_in_window=999; pc.n_1h_fvg_bullish_same_primary_in_window=790; xctx.minutes_since_last_sweep_side_high_24h=443; xctx.n_fvg_side_bearish_4h=418; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=360; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=314; xctx.n_fvg_side_bullish_24h=295 |
| at_period_close | high | label.n1_primary_took_period_n_high | pc.n_1h_disp_bearish_same_primary_in_window=1889; xctx.n_fvg_side_bullish_24h=1533; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=1143; pc.minutes_since_last_sweep_high_same_primary_in_window=1096; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=762; xctx.minutes_since_last_sweep_side_low_24h=641; xctx.n_fvg_side_bullish_4h=462; pc.n_1h_fvg_bearish_same_primary_in_window=418; xctx.n_disp_side_bullish_24h=396; xctx.n_fvg_side_bearish_4h=385 |
| at_period_close | low | label.n1_close_moved_with_thesis | xctx.n_disp_side_bearish_24h=1871; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1650; xctx.n_fvg_side_bearish_24h=869; pc.n_1h_fvg_bullish_same_primary_in_window=773; pc.minutes_since_last_sweep_low_same_primary_in_window=611; xctx.minutes_since_last_sweep_side_low_24h=498; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=408; xctx.n_fvg_side_bullish_4h=369; xctx.minutes_since_last_sweep_side_high_24h=254; xctx.n_fvg_side_bullish_24h=247 |
| at_period_close | all | label.n1_primary_took_period_n_high | xctx.n_disp_side_bearish_24h=5624; xctx.n_fvg_side_bullish_24h=1652; xctx.minutes_since_last_sweep_side_low_24h=1553; xctx.n_fvg_side_bullish_4h=1322; xctx.n_fvg_side_bearish_4h=1229; xctx.n_fvg_side_bearish_24h=1075; xctx.n_disp_side_bullish_24h=1043; xctx.minutes_since_last_sweep_side_high_24h=702; pc.minutes_since_last_sweep_high_same_primary_in_window=507; pc.minutes_since_last_sweep_low_same_primary_in_window=439 |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | xctx.n_disp_side_bearish_24h=1462; pc.minutes_since_last_sweep_high_same_primary_in_window=1331; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=1140; pc.n_1h_disp_bearish_same_primary_in_window=986; pc.minutes_since_last_sweep_low_same_primary_in_window=958; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=592; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=583; xctx.n_fvg_side_bearish_24h=539; pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window=470; xctx.minutes_since_last_eql_same_primary_24h=425 |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | pc.minutes_since_last_sweep_high_same_primary_in_window=1310; xctx.n_disp_side_bearish_24h=1120; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=1111; pc.n_1h_disp_bearish_same_primary_in_window=1022; pc.minutes_since_last_sweep_low_same_primary_in_window=836; xctx.n_fvg_side_bullish_4h=572; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=555; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=515; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=465; xctx.n_fvg_side_bullish_24h=445 |
| at_period_close | low | label.n1_or_n2_close_moved_with_thesis | xctx.n_disp_side_bearish_24h=1585; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=828; pc.minutes_since_last_sweep_low_same_primary_in_window=518; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=430; xctx.n_fvg_same_primary_24h=263; pc.n_1h_fvg_bullish_same_primary_in_window=236; xctx.minutes_since_last_sweep_side_high_24h=208; xctx.n_fvg_side_bearish_24h=207; xctx.n_swing_side_low_24h=194; xctx.n_fvg_side_bullish_4h=176 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
