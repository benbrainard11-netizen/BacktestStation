# ML snapshot leaderboard

_Generated `2026-05-11T23:32:52.090135+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshots.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `balanced, buying, selling, all`
- Labels searched: `45` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 36095 |
| schema_feature_columns | 65 |
| schema_label_columns | 51 |
| grid_attempts | 180 |
| trained_ok | 166 |
| skipped | 14 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | buying | label.vwap_1sd_low_touch.wicked_above | 1803 | 98.2% | 0.961 | 0.972 | 0.982 | 181 | 100.0% | 1.8% |
| at_fire | buying | label.vah_touch.wicked_above | 1803 | 97.2% | 0.946 | 0.957 | 0.972 | 181 | 100.0% | 2.8% |
| at_fire | buying | label.vwap_1sd_low_touch.closed_above | 1803 | 97.9% | 0.945 | 0.966 | 0.979 | 181 | 100.0% | 2.1% |
| at_fire | buying | label.vwap_touch.wicked_above | 1803 | 94.8% | 0.940 | 0.932 | 0.948 | 181 | 100.0% | 5.2% |
| at_fire | selling | label.val_touch.wicked_below | 1133 | 92.7% | 0.937 | 0.938 | 0.927 | 114 | 100.0% | 7.3% |
| at_fire | all | label.vah_touch.wicked_above | 6546 | 97.6% | 0.937 | 0.972 | 0.976 | 655 | 100.0% | 2.4% |
| at_fire | all | label.vwap_1sd_low_touch.wicked_above | 6546 | 97.8% | 0.935 | 0.977 | 0.978 | 655 | 100.0% | 2.2% |
| at_fire | balanced | label.vwap_1sd_low_touch.wicked_above | 3610 | 97.6% | 0.932 | 0.976 | 0.976 | 361 | 100.0% | 2.4% |
| at_fire | buying | label.vah_touch.closed_above | 1803 | 96.7% | 0.930 | 0.949 | 0.967 | 181 | 100.0% | 3.3% |
| at_fire | selling | label.vwap_1sd_high_touch.wicked_below | 1133 | 94.4% | 0.928 | 0.949 | 0.944 | 114 | 100.0% | 5.6% |
| at_fire | selling | label.vwap_touch.wicked_below | 1133 | 89.1% | 0.925 | 0.906 | 0.891 | 114 | 100.0% | 10.9% |
| at_fire | balanced | label.vah_touch.wicked_above | 3610 | 97.3% | 0.922 | 0.971 | 0.973 | 361 | 100.0% | 2.7% |
| at_fire | all | label.val_touch.wicked_below | 6546 | 95.7% | 0.912 | 0.959 | 0.957 | 655 | 100.0% | 4.3% |
| at_fire | buying | label.vwap_touch.closed_above | 1803 | 94.2% | 0.910 | 0.926 | 0.942 | 181 | 100.0% | 5.8% |
| at_fire | all | label.vwap_2sd_low_touch.wicked_above | 6546 | 99.6% | 0.909 | 0.995 | 0.996 | 655 | 100.0% | 0.4% |
| at_fire | selling | label.val_touch.closed_below | 1133 | 91.9% | 0.909 | 0.927 | 0.919 | 114 | 99.1% | 7.2% |
| at_fire | all | label.vwap_2sd_high_touch.wicked_below | 6546 | 98.9% | 0.909 | 0.989 | 0.989 | 655 | 100.0% | 1.1% |
| at_fire | all | label.poc_touch.wicked_above | 6546 | 92.5% | 0.904 | 0.930 | 0.925 | 655 | 100.0% | 7.5% |
| at_fire | all | label.vwap_1sd_high_touch.wicked_below | 6546 | 95.3% | 0.900 | 0.953 | 0.953 | 655 | 99.7% | 4.4% |
| at_fire | balanced | label.poc_touch.wicked_above | 3610 | 93.6% | 0.900 | 0.933 | 0.936 | 361 | 100.0% | 6.4% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | buying | label.vwap_1sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=8623; vp.ed.close_vs_vwap_pts=1019; vp.ed.poc_pct_in_range=973; vp.ed.total_volume=724; ts.hour_of_day_utc=680; vp.ed.close_vs_poc_pts=634; vp.ed.poc_volume=588; vp.ed.value_area_range_pts=582; ts.year=518; vp.ed.n_bars=504 |
| at_fire | buying | label.vah_touch.wicked_above | vp.ed.close_vs_vwap_sd=13465; vp.ed.close_vs_vwap_pts=2073; vp.ed.poc_pct_in_range=1320; vp.ed.poc_volume=1033; ts.hour_of_day_utc=961; vp.ed.n_bars=782; vp.ed.total_volume=689; vp.ed.value_area_range_pts=674; ts.month=611; vp.ed.period_range_pts=596 |
| at_fire | buying | label.vwap_1sd_low_touch.closed_above | vp.ed.close_vs_vwap_sd=9776; vp.ed.close_vs_vwap_pts=1233; vp.ed.poc_pct_in_range=1137; vp.ed.total_volume=845; ts.hour_of_day_utc=776; vp.ed.poc_volume=719; vp.ed.close_vs_poc_pts=661; vp.ed.n_bars=561; vp.ed.value_area_range_pts=551; vp.ed.period_range_pts=524 |
| at_fire | buying | label.vwap_touch.wicked_above | vp.ed.close_vs_vwap_sd=15302; vp.ed.close_vs_vwap_pts=6816; vp.ed.poc_pct_in_range=1822; ts.hour_of_day_utc=1340; vp.ed.poc_volume=1071; vp.ed.close_vs_poc_pts=987; vp.ed.period_range_pts=974; ts.month=929; ts.year=867; vp.ed.total_volume=847 |
| at_fire | selling | label.val_touch.wicked_below | vp.ed.close_vs_vwap_sd=14200; vp.ed.close_vs_vwap_pts=1264; ts.hour_of_day_utc=1233; vp.ed.poc_pct_in_range=1218; vp.ed.total_volume=1096; vp.ed.poc_volume=860; vp.ed.value_area_range_pts=806; vp.ed.vwap_sd=686; vp.ed.period_range_pts=657; vp.ed.n_bars=619 |
| at_fire | all | label.vah_touch.wicked_above | vp.ed.close_vs_vwap_sd=23171; vp.ed.poc_pct_in_range=4876; vp.ed.close_vs_poc_pts=4360; vp.ed.close_vs_vwap_pts=2497; ts.day_of_week=1793; vp.ed.poc_volume=1737; vp.ed.n_bars=1720; vp.ed.total_volume=1614; ts.hour_of_day_utc=1483; vp.ed.value_area_range_pts=1259 |
| at_fire | all | label.vwap_1sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=21091; vp.ed.close_vs_vwap_pts=4098; ts.day_of_week=2234; vp.ed.poc_volume=1809; vp.ed.close_vs_poc_pts=1687; vp.ed.poc_pct_in_range=1651; vp.ed.n_bars=1519; ts.year=1218; vp.ed.total_volume=1203; ts.month=1171 |
| at_fire | balanced | label.vwap_1sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=9962; vp.ed.close_vs_vwap_pts=1998; vp.ed.poc_volume=1690; vp.ed.close_vs_poc_pts=1467; vp.ed.n_bars=1420; ts.day_of_week=1086; vp.ed.poc_pct_in_range=865; vp.ed.total_volume=839; vp.ed.value_area_range_pts=740; ts.month=715 |
| at_fire | buying | label.vah_touch.closed_above | vp.ed.close_vs_vwap_sd=13975; vp.ed.close_vs_vwap_pts=2008; vp.ed.poc_pct_in_range=1380; vp.ed.poc_volume=1058; ts.hour_of_day_utc=966; vp.ed.total_volume=955; vp.ed.close_vs_poc_pts=825; vp.ed.n_bars=817; vp.ed.period_range_pts=612; vp.ed.vwap_sd=584 |
| at_fire | selling | label.vwap_1sd_high_touch.wicked_below | vp.ed.close_vs_vwap_sd=11172; vp.ed.poc_volume=804; vp.ed.close_vs_vwap_pts=764; ts.hour_of_day_utc=730; vp.ed.poc_pct_in_range=699; vp.ed.total_volume=678; vp.ed.value_area_range_pts=553; ts.day_of_week=478; vp.ed.period_range_pts=434; vp.ed.close_vs_poc_pts=429 |
| at_fire | selling | label.vwap_touch.wicked_below | vp.ed.close_vs_vwap_sd=18273; vp.ed.close_vs_vwap_pts=3614; ts.hour_of_day_utc=1664; vp.ed.total_volume=1591; vp.ed.value_area_range_pts=1302; vp.ed.poc_pct_in_range=1286; vp.ed.period_range_pts=1028; vp.ed.poc_volume=1027; vp.ed.vwap_sd=948; vp.ed.close_vs_poc_pts=806 |
| at_fire | balanced | label.vah_touch.wicked_above | vp.ed.close_vs_vwap_sd=10976; vp.ed.close_vs_poc_pts=2758; vp.ed.poc_volume=1506; vp.ed.n_bars=1378; vp.ed.poc_pct_in_range=1309; vp.ed.close_vs_vwap_pts=1069; vp.ed.total_volume=961; vp.ed.period_range_pts=879; ts.day_of_week=709; vp.ed.value_area_range_pts=666 |
| at_fire | all | label.val_touch.wicked_below | vp.ed.close_vs_vwap_sd=36709; vp.ed.close_vs_poc_pts=9080; vp.ed.poc_pct_in_range=5178; vp.ed.poc_volume=2457; vp.ed.close_vs_vwap_pts=2351; vp.ed.n_bars=2273; vp.ed.total_volume=1924; ts.day_of_week=1914; vp.ed.value_area_range_pts=1856; vp.ed.poc_bin_idx=1699 |
| at_fire | buying | label.vwap_touch.closed_above | vp.ed.close_vs_vwap_pts=11811; vp.ed.close_vs_vwap_sd=9478; vp.ed.poc_pct_in_range=1492; ts.hour_of_day_utc=1077; vp.ed.poc_volume=1002; vp.ed.total_volume=936; ts.year=836; ts.month=818; vp.ed.period_range_pts=802; vp.ed.value_area_range_pts=745 |
| at_fire | all | label.vwap_2sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=4730; vp.ed.n_bars=2038; ts.day_of_week=1342; vp.ed.poc_volume=1183; ts.month=1030; vp.ed.poc_pct_in_range=1011; vp.ed.value_area_range_pts=978; vp.ed.close_vs_poc_pts=841; vp.ed.close_vs_vwap_pts=827; vp.event_type_daily_volume_profile=729 |

## Skipped Summary

| status | count |
|---|---|
| skip_train_imbalance | 12 |
| skip_test_imbalance | 2 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
