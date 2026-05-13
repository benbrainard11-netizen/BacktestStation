# ML snapshot leaderboard

_Generated `2026-05-12T14:47:18.773464+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshots_xctx.schema.json`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 36095 |
| schema_feature_columns | 645 |
| schema_label_columns | 51 |
| grid_attempts | 180 |
| trained_ok | 166 |
| skipped | 14 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | buying | label.vwap_1sd_low_touch.wicked_above | 1803 | 98.2% | 0.954 | 0.981 | 0.982 | 181 | 100.0% | 1.8% |
| at_fire | buying | label.vwap_1sd_low_touch.closed_above | 1803 | 97.9% | 0.943 | 0.979 | 0.979 | 181 | 100.0% | 2.1% |
| at_fire | buying | label.vah_touch.wicked_above | 1803 | 97.2% | 0.943 | 0.961 | 0.972 | 181 | 100.0% | 2.8% |
| at_fire | buying | label.vwap_touch.wicked_above | 1803 | 94.8% | 0.941 | 0.938 | 0.948 | 181 | 100.0% | 5.2% |
| at_fire | all | label.vah_touch.wicked_above | 6546 | 97.6% | 0.936 | 0.975 | 0.976 | 655 | 100.0% | 2.4% |
| at_fire | selling | label.val_touch.wicked_below | 1133 | 92.7% | 0.933 | 0.927 | 0.927 | 114 | 100.0% | 7.3% |
| at_fire | buying | label.vah_touch.closed_above | 1803 | 96.7% | 0.931 | 0.957 | 0.967 | 181 | 100.0% | 3.3% |
| at_fire | all | label.vwap_1sd_low_touch.wicked_above | 6546 | 97.8% | 0.930 | 0.978 | 0.978 | 655 | 100.0% | 2.2% |
| at_fire | selling | label.vwap_1sd_low_touch.wicked_above | 1133 | 98.1% | 0.924 | 0.981 | 0.981 | 114 | 100.0% | 1.9% |
| at_fire | balanced | label.vah_touch.wicked_above | 3610 | 97.3% | 0.923 | 0.972 | 0.973 | 361 | 100.0% | 2.7% |
| at_fire | selling | label.vwap_touch.wicked_below | 1133 | 89.1% | 0.923 | 0.901 | 0.891 | 114 | 100.0% | 10.9% |
| at_fire | balanced | label.vwap_1sd_low_touch.wicked_above | 3610 | 97.6% | 0.921 | 0.975 | 0.976 | 361 | 99.7% | 2.2% |
| at_fire | balanced | label.vwap_2sd_low_touch.wicked_above | 3610 | 99.4% | 0.912 | 0.994 | 0.994 | 361 | 100.0% | 0.6% |
| at_fire | buying | label.vwap_touch.closed_above | 1803 | 94.2% | 0.910 | 0.929 | 0.942 | 181 | 99.4% | 5.2% |
| at_fire | all | label.val_touch.wicked_below | 6546 | 95.7% | 0.908 | 0.959 | 0.957 | 655 | 100.0% | 4.3% |
| at_fire | all | label.poc_touch.wicked_above | 6546 | 92.5% | 0.907 | 0.932 | 0.925 | 655 | 100.0% | 7.5% |
| at_fire | balanced | label.val_touch.wicked_below | 3610 | 95.4% | 0.902 | 0.955 | 0.954 | 361 | 100.0% | 4.6% |
| at_fire | buying | label.vwap_1sd_high_touch.wicked_above | 1803 | 85.9% | 0.901 | 0.890 | 0.859 | 181 | 100.0% | 14.1% |
| at_fire | selling | label.val_touch.closed_below | 1133 | 91.9% | 0.901 | 0.921 | 0.919 | 114 | 100.0% | 8.1% |
| at_fire | all | label.vwap_2sd_low_touch.wicked_above | 6546 | 99.6% | 0.900 | 0.996 | 0.996 | 655 | 100.0% | 0.4% |
| at_fire | balanced | label.poc_touch.wicked_above | 3610 | 93.6% | 0.900 | 0.936 | 0.936 | 361 | 100.0% | 6.4% |
| at_fire | selling | label.vwap_1sd_high_touch.wicked_below | 1133 | 94.4% | 0.899 | 0.946 | 0.944 | 114 | 98.2% | 3.8% |
| at_fire | buying | label.poc_touch.wicked_above | 1803 | 87.5% | 0.899 | 0.890 | 0.875 | 181 | 100.0% | 12.5% |
| at_fire | all | label.vah_touch.closed_above | 6546 | 97.0% | 0.898 | 0.969 | 0.970 | 655 | 100.0% | 3.0% |
| at_fire | selling | label.vwap_1sd_high_touch.closed_below | 1133 | 93.9% | 0.895 | 0.939 | 0.939 | 114 | 99.1% | 5.2% |
| at_fire | all | label.vwap_touch.wicked_above | 6546 | 92.2% | 0.895 | 0.920 | 0.922 | 655 | 100.0% | 7.8% |
| at_fire | all | label.vwap_1sd_high_touch.wicked_below | 6546 | 95.3% | 0.894 | 0.954 | 0.953 | 655 | 100.0% | 4.7% |
| at_fire | selling | label.vwap_touch.closed_below | 1133 | 87.8% | 0.894 | 0.898 | 0.878 | 114 | 99.1% | 11.3% |
| at_fire | balanced | label.vwap_1sd_high_touch.wicked_below | 3610 | 95.7% | 0.893 | 0.957 | 0.957 | 361 | 100.0% | 4.3% |
| at_fire | balanced | label.vwap_touch.wicked_above | 3610 | 92.7% | 0.893 | 0.927 | 0.927 | 361 | 100.0% | 7.3% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | buying | label.vwap_1sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=8083; vp.ed.close_vs_vwap_pts=688; xctx.minutes_since_last_tp_24h=440; vp.ed.close_vs_poc_pts=433; xctx.minutes_since_last_disp_side_bullish_24h=361; xctx.minutes_since_last_smt_side_high_7d=287; xctx.n_swing_7d=231; xctx.n_ft_side_bullish_24h=228; xctx.n_psp_7d=177; xctx.minutes_since_last_fvg_side_bullish_24h=175 |
| at_fire | buying | label.vwap_1sd_low_touch.closed_above | vp.ed.close_vs_vwap_sd=9036; vp.ed.close_vs_vwap_pts=956; xctx.minutes_since_last_tp_24h=449; xctx.active_concepts_4h=378; xctx.minutes_since_last_smt_side_high_7d=335; xctx.minutes_since_last_disp_side_bullish_24h=315; xctx.n_fvg_4h=257; xctx.n_swing_side_high_7d=255; xctx.minutes_since_last_psp_side_bearish_24h=193; xctx.minutes_since_last_fvg_side_bullish_24h=164 |
| at_fire | buying | label.vah_touch.wicked_above | vp.ed.close_vs_vwap_sd=12919; vp.ed.close_vs_vwap_pts=1888; ts.hour_of_day_utc=436; xctx.minutes_since_last_tp_24h=321; xctx.n_fvg_side_bearish_24h=289; vp.ed.close_band_1sd_2sd_below=286; xctx.minutes_since_last_ob_side_bullish_24h=281; xctx.minutes_since_last_smt_side_high_7d=253; vp.ed.poc_pct_in_range=244; xctx.minutes_since_last_eql_same_primary_7d=241 |
| at_fire | buying | label.vwap_touch.wicked_above | vp.ed.close_vs_vwap_sd=14725; vp.ed.close_vs_vwap_pts=6249; ts.hour_of_day_utc=559; xctx.minutes_since_last_tp_24h=513; xctx.n_fvg_side_bullish_24h=423; xctx.minutes_since_last_psp_side_bearish_24h=383; vp.ed.poc_pct_in_range=367; vp.ed.close_vs_poc_pts=342; xctx.minutes_since_last_smt_side_high_7d=298; xctx.n_ob_side_bullish_7d=297 |
| at_fire | all | label.vah_touch.wicked_above | vp.ed.close_vs_vwap_sd=24372; vp.ed.close_vs_poc_pts=2959; vp.ed.poc_pct_in_range=2490; vp.ed.poc_bin_idx=997; xctx.n_disp_4h=820; xctx.minutes_since_last_smt_side_low_7d=746; xctx.minutes_since_last_orb_24h=742; xctx.n_ob_side_bullish_7d=738; vp.ed.close_vs_vwap_pts=725; xctx.minutes_since_last_fvg_24h=696 |
| at_fire | selling | label.val_touch.wicked_below | vp.ed.close_vs_vwap_sd=12660; vp.ed.close_vs_vwap_pts=1428; ts.hour_of_day_utc=888; vp.ed.close_above_vwap=435; vp.ed.close_band_vwap_to_1sd_above=385; xctx.n_fvg_7d=376; vp.ed.total_volume=357; xctx.total_events_7d=323; xctx.minutes_since_last_disp_side_bullish_24h=304; xctx.minutes_since_last_smt_24h=250 |
| at_fire | buying | label.vah_touch.closed_above | vp.ed.close_vs_vwap_sd=12986; vp.ed.close_vs_vwap_pts=2076; xctx.minutes_since_last_tp_24h=409; vp.ed.poc_pct_in_range=327; xctx.minutes_since_last_ft_side_bearish_7d=295; xctx.n_fvg_side_bearish_24h=276; xctx.n_swing_side_high_7d=273; xctx.minutes_since_last_smt_side_high_7d=270; xctx.minutes_since_last_fvg_side_bullish_24h=261; ts.hour_of_day_utc=257 |
| at_fire | all | label.vwap_1sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=21789; vp.ed.close_vs_vwap_pts=1950; xctx.minutes_since_last_fvg_24h=799; xctx.minutes_since_last_smt_side_low_7d=706; xctx.minutes_since_last_orb_24h=696; xctx.minutes_since_last_tp_24h=691; xctx.n_disp_same_primary_4h=665; xctx.n_disp_side_bullish_7d=617; xctx.n_swing_7d=600; xctx.n_ob_side_bullish_7d=557 |
| at_fire | selling | label.vwap_1sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=2512; vp.event_type_daily_volume_profile=430; vp.ed.close_vs_poc_pts=409; xctx.minutes_since_last_psp_side_bullish_24h=407; ts.day_of_week=227; xctx.minutes_since_last_fvg_side_bullish_4h=222; xctx.n_fvg_same_primary_7d=208; xctx.minutes_since_last_ob_same_primary_24h=186; xctx.minutes_since_last_ft_side_bearish_7d=164; xctx.minutes_since_last_smt_7d=164 |
| at_fire | balanced | label.vah_touch.wicked_above | vp.ed.close_vs_vwap_sd=11100; vp.ed.close_vs_poc_pts=1554; vp.ed.poc_pct_in_range=531; xctx.minutes_since_last_eql_side_low_24h=500; xctx.minutes_since_last_fvg_24h=487; xctx.minutes_since_last_orb_24h=484; xctx.n_fvg_side_bullish_7d=426; xctx.minutes_since_last_smt_side_low_7d=407; xctx.n_swing_7d=407; vp.ed.total_volume=401 |
| at_fire | selling | label.vwap_touch.wicked_below | vp.ed.close_vs_vwap_sd=16061; vp.ed.close_vs_vwap_pts=3500; ts.hour_of_day_utc=862; vp.ed.close_above_vwap=763; vp.ed.poc_volume=501; xctx.minutes_since_last_psp_side_bearish_24h=463; vp.ed.total_volume=419; xctx.minutes_since_last_smt_side_low_7d=417; xctx.minutes_since_last_smt_same_primary_7d=384; xctx.n_eql_side_low_7d=329 |
| at_fire | balanced | label.vwap_1sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=9789; vp.ed.close_vs_poc_pts=1177; xctx.minutes_since_last_orb_24h=609; xctx.n_fvg_4h=565; xctx.minutes_since_last_eql_side_low_24h=559; xctx.n_disp_side_bearish_4h=489; xctx.minutes_since_last_fvg_24h=445; xctx.n_ob_side_bearish_7d=350; vp.ed.total_volume=346; xctx.n_swing_7d=344 |
| at_fire | balanced | label.vwap_2sd_low_touch.wicked_above | vp.ed.close_vs_vwap_sd=1205; vp.ed.close_band_below_3sd=720; vp.ed.close_vs_vwap_pts=635; vp.ed.total_volume=596; xctx.minutes_since_last_fvg_24h=549; vp.ed.close_vs_poc_pts=539; xctx.minutes_since_last_orb_24h=371; xctx.n_fvg_4h=354; xctx.minutes_since_last_eql_side_low_24h=313; xctx.minutes_since_last_eql_same_primary_24h=238 |
| at_fire | buying | label.vwap_touch.closed_above | vp.ed.close_vs_vwap_pts=11383; vp.ed.close_vs_vwap_sd=9183; xctx.minutes_since_last_tp_24h=518; xctx.minutes_since_last_ob_side_bullish_24h=377; xctx.minutes_since_last_smt_side_low_7d=365; ts.hour_of_day_utc=365; xctx.minutes_since_last_smt_24h=336; xctx.minutes_since_last_psp_same_primary_24h=332; xctx.n_fvg_side_bullish_24h=282; xctx.minutes_since_last_psp_side_bearish_24h=276 |
| at_fire | all | label.val_touch.wicked_below | vp.ed.close_vs_vwap_sd=37799; vp.ed.close_vs_poc_pts=6312; vp.ed.poc_pct_in_range=3327; vp.ed.poc_bin_idx=1334; xctx.minutes_since_last_smt_side_low_7d=1248; xctx.minutes_since_last_smt_side_high_7d=991; xctx.n_disp_side_bullish_7d=944; xctx.n_fvg_7d=941; vp.ed.close_vs_vwap_pts=899; xctx.n_fvg_side_bearish_4h=863 |

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
