# ML snapshot leaderboard

_Generated `2026-05-13T04:26:41.686845+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_snapshots_xctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `buying, selling, balanced, all`
- Labels searched: `18` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 43150 |
| schema_feature_columns | 710 |
| schema_label_columns | 411 |
| grid_attempts | 72 |
| trained_ok | 72 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | 1418 | 2.5% | 0.934 | 0.975 | 0.975 | 142 | 18.3% | 15.8% |
| at_fire | selling | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 1418 | 1.8% | 0.933 | 0.981 | 0.982 | 142 | 13.4% | 11.5% |
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 1418 | 2.3% | 0.933 | 0.977 | 0.977 | 142 | 16.2% | 13.9% |
| at_fire | selling | label.next_60m.vah_touch.resistance_rejection_3bar | 1418 | 2.3% | 0.931 | 0.977 | 0.977 | 142 | 14.1% | 11.8% |
| at_fire | selling | label.next_60m.took_profile_high_so_far | 1418 | 15.7% | 0.910 | 0.889 | 0.843 | 142 | 69.0% | 53.4% |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | 2032 | 4.8% | 0.905 | 0.952 | 0.952 | 204 | 23.0% | 18.3% |
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | 8124 | 4.6% | 0.903 | 0.954 | 0.954 | 813 | 21.5% | 16.9% |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 2031 | 4.1% | 0.903 | 0.958 | 0.959 | 204 | 18.6% | 14.5% |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | 2031 | 3.2% | 0.902 | 0.968 | 0.968 | 204 | 16.2% | 13.0% |
| at_fire | buying | label.next_60m.took_profile_low_so_far | 2031 | 14.1% | 0.900 | 0.898 | 0.859 | 204 | 68.6% | 54.5% |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | 8121 | 3.2% | 0.899 | 0.968 | 0.968 | 813 | 15.7% | 12.5% |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 8121 | 3.0% | 0.894 | 0.970 | 0.970 | 813 | 13.5% | 10.6% |
| at_fire | all | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 8124 | 4.2% | 0.893 | 0.958 | 0.958 | 813 | 18.0% | 13.7% |
| at_fire | balanced | label.next_240m.vah_touch.resistance_rejection_3bar | 4674 | 5.1% | 0.892 | 0.949 | 0.949 | 468 | 21.6% | 16.5% |
| at_fire | all | label.next_60m.took_profile_high_so_far | 8121 | 24.9% | 0.889 | 0.834 | 0.751 | 813 | 80.9% | 56.0% |
| at_fire | all | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 8121 | 5.4% | 0.886 | 0.946 | 0.946 | 813 | 25.7% | 20.3% |
| at_fire | balanced | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 4672 | 3.2% | 0.886 | 0.968 | 0.968 | 468 | 13.5% | 10.3% |
| at_fire | balanced | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 4674 | 4.5% | 0.883 | 0.955 | 0.955 | 468 | 18.8% | 14.3% |
| at_fire | buying | label.next_240m.vwap_touch.resistance_break_acceptance_3bar | 2032 | 6.3% | 0.883 | 0.937 | 0.937 | 204 | 23.5% | 17.2% |
| at_fire | balanced | label.next_60m.took_profile_high_so_far | 4672 | 24.3% | 0.882 | 0.836 | 0.757 | 468 | 82.5% | 58.2% |
| at_fire | balanced | label.next_60m.vah_touch.resistance_rejection_3bar | 4672 | 3.5% | 0.882 | 0.965 | 0.965 | 468 | 14.7% | 11.3% |
| at_fire | balanced | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 4672 | 5.8% | 0.878 | 0.940 | 0.942 | 468 | 23.9% | 18.1% |
| at_fire | buying | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 2032 | 4.9% | 0.876 | 0.951 | 0.951 | 204 | 20.6% | 15.7% |
| at_fire | all | label.next_60m.took_profile_low_so_far | 8121 | 19.5% | 0.875 | 0.852 | 0.805 | 813 | 71.0% | 51.5% |
| at_fire | buying | label.next_240m.val_touch.support_rejection_3bar | 2032 | 4.3% | 0.875 | 0.957 | 0.957 | 204 | 19.6% | 15.3% |
| at_fire | selling | label.next_60m.val_touch.support_rejection_3bar | 1418 | 3.2% | 0.872 | 0.968 | 0.968 | 142 | 12.7% | 9.5% |
| at_fire | buying | label.next_60m.took_profile_high_so_far | 2031 | 32.9% | 0.868 | 0.786 | 0.671 | 204 | 84.8% | 51.9% |
| at_fire | buying | label.next_240m.val_touch.support_break_acceptance_3bar | 2032 | 3.3% | 0.868 | 0.967 | 0.967 | 204 | 13.7% | 10.4% |
| at_fire | selling | label.next_60m.vwap_touch.support_break_acceptance_3bar | 1418 | 4.2% | 0.866 | 0.959 | 0.958 | 142 | 21.1% | 17.0% |
| at_fire | all | label.next_240m.val_touch.support_break_acceptance_3bar | 8124 | 5.1% | 0.865 | 0.949 | 0.949 | 813 | 19.2% | 14.0% |
| at_fire | balanced | label.next_60m.took_profile_low_so_far | 4672 | 20.2% | 0.864 | 0.856 | 0.798 | 468 | 75.0% | 54.8% |
| at_fire | selling | label.next_240m.took_profile_high_so_far | 1418 | 32.7% | 0.862 | 0.800 | 0.673 | 142 | 90.1% | 57.4% |
| at_fire | selling | label.rest_of_day.took_profile_high_so_far | 1418 | 56.9% | 0.861 | 0.800 | 0.569 | 142 | 93.0% | 36.0% |
| at_fire | balanced | label.next_60m.val_touch.support_break_acceptance_3bar | 4672 | 4.1% | 0.861 | 0.959 | 0.959 | 468 | 15.6% | 11.5% |
| at_fire | all | label.next_60m.val_touch.support_break_acceptance_3bar | 8121 | 3.6% | 0.860 | 0.964 | 0.964 | 813 | 13.8% | 10.1% |
| at_fire | balanced | label.next_240m.val_touch.support_break_acceptance_3bar | 4674 | 6.0% | 0.857 | 0.940 | 0.940 | 468 | 18.2% | 12.2% |
| at_fire | buying | label.next_60m.val_touch.support_break_acceptance_3bar | 2031 | 2.7% | 0.857 | 0.973 | 0.973 | 204 | 10.8% | 8.1% |
| at_fire | selling | label.next_240m.val_touch.support_rejection_3bar | 1418 | 5.6% | 0.857 | 0.944 | 0.944 | 142 | 15.5% | 9.9% |
| at_fire | buying | label.next_60m.val_touch.support_rejection_3bar | 2031 | 3.8% | 0.854 | 0.962 | 0.962 | 204 | 13.7% | 9.9% |
| at_fire | all | label.next_240m.val_touch.support_rejection_3bar | 8124 | 5.4% | 0.854 | 0.946 | 0.946 | 813 | 17.5% | 12.1% |
| at_fire | balanced | label.next_240m.val_touch.support_rejection_3bar | 4674 | 5.8% | 0.853 | 0.942 | 0.942 | 468 | 20.5% | 14.8% |
| at_fire | all | label.next_60m.val_touch.support_rejection_3bar | 8121 | 4.0% | 0.852 | 0.960 | 0.960 | 813 | 14.5% | 10.5% |
| at_fire | selling | label.next_60m.took_profile_low_so_far | 1418 | 24.9% | 0.851 | 0.799 | 0.751 | 142 | 69.7% | 44.8% |
| at_fire | balanced | label.next_60m.vwap_touch.support_break_acceptance_3bar | 4672 | 6.6% | 0.850 | 0.934 | 0.934 | 468 | 25.0% | 18.4% |
| at_fire | all | label.next_60m.vwap_touch.support_break_acceptance_3bar | 8121 | 6.0% | 0.847 | 0.939 | 0.940 | 813 | 23.1% | 17.1% |
| at_fire | buying | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2031 | 3.3% | 0.847 | 0.967 | 0.967 | 204 | 13.7% | 10.4% |
| at_fire | balanced | label.next_60m.val_touch.support_rejection_3bar | 4672 | 4.3% | 0.847 | 0.957 | 0.957 | 468 | 15.4% | 11.0% |
| at_fire | selling | label.next_240m.vwap_touch.support_break_acceptance_3bar | 1418 | 6.6% | 0.846 | 0.935 | 0.934 | 142 | 23.2% | 16.7% |
| at_fire | all | label.next_240m.vwap_touch.resistance_break_acceptance_3bar | 8124 | 8.1% | 0.842 | 0.919 | 0.919 | 813 | 25.5% | 17.4% |
| at_fire | balanced | label.next_240m.vwap_touch.resistance_break_acceptance_3bar | 4674 | 8.4% | 0.841 | 0.914 | 0.916 | 468 | 25.9% | 17.4% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | fvp.ed.close_vs_vwap_sd=3368; fvp.ed.close_vs_poc_pts=2444; xctx.minutes_since_last_smt_same_primary_7d=348; fvp.ed.vwap_sd=265; fvp.ed.value_area_range_pts=261; xctx.minutes_since_last_psp_same_primary_7d=252; xctx.n_eql_side_high_24h=238; xctx.n_ob_7d=203; xctx.n_ob_side_bearish_7d=200; xctx.minutes_since_last_disp_side_bearish_24h=190 |
| at_fire | selling | label.next_60m.vah_touch.resistance_break_acceptance_3bar | fvp.ed.close_vs_vwap_sd=3891; fvp.ed.close_vs_poc_pts=1508; xctx.minutes_since_last_eql_same_primary_7d=300; xctx.n_eql_side_high_4h=272; fvp.ed.close_above_poc=271; xctx.minutes_since_last_disp_side_bullish_24h=265; fvp.ed.poc_pct_in_range=251; xctx.minutes_since_last_psp_same_primary_7d=197; xctx.n_disp_7d=174; xctx.minutes_since_last_eql_side_high_24h=160 |
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | fvp.ed.close_vs_vwap_sd=4508; fvp.ed.close_vs_poc_pts=1871; fvp.ed.close_above_poc=318; xctx.n_fvg_4h=234; xctx.n_fvg_same_primary_7d=233; xctx.minutes_since_last_eql_same_primary_7d=224; xctx.minutes_since_last_vp_side_buying_7d=201; xctx.n_eql_side_high_4h=175; xctx.n_fvg_24h=169; xctx.minutes_since_last_orb_side_doji_7d=160 |
| at_fire | selling | label.next_60m.vah_touch.resistance_rejection_3bar | fvp.ed.close_vs_vwap_sd=2864; fvp.ed.close_vs_poc_pts=1856; fvp.ed.value_area_range_pts=336; xctx.minutes_since_last_smt_same_primary_7d=306; xctx.n_ob_side_bearish_7d=246; xctx.minutes_since_last_orb_side_bearish_24h=176; xctx.n_vp_side_buying_24h=176; xctx.minutes_since_last_smt_7d=161; xctx.minutes_since_last_psp_side_bearish_24h=151; xctx.n_fvg_side_bearish_7d=138 |
| at_fire | selling | label.next_60m.took_profile_high_so_far | fvp.ed.close_vs_vwap_sd=23523; fvp.ed.close_vs_vwap_pts=1850; fvp.ed.close_above_vwap=1455; fvp.ed.close_band_vwap_to_1sd_above=1002; xctx.minutes_since_last_orb_side_bullish_24h=389; xctx.minutes_since_last_disp_side_bearish_24h=366; xctx.minutes_since_last_orb_side_doji_7d=355; xctx.n_disp_side_bullish_7d=341; fvp.ed.poc_pct_in_range=304; xctx.minutes_since_last_disp_same_primary_24h=304 |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | fvp.ed.close_vs_vwap_sd=11576; fvp.ed.close_vs_vwap_pts=3352; xctx.minutes_since_last_smt_same_primary_7d=399; fvp.ed.total_volume_so_far=317; xctx.minutes_since_last_psp_same_primary_24h=311; xctx.n_disp_side_bullish_7d=288; xctx.minutes_since_last_disp_side_bearish_24h=285; fvp.ed.poc_pct_in_range=275; xctx.minutes_since_last_psp_side_bullish_24h=268; xctx.minutes_since_last_psp_same_primary_7d=259 |
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | fvp.ed.close_vs_vwap_sd=40433; fvp.ed.close_vs_poc_pts=5549; fvp.ed.poc_pct_in_range=2791; fvp.ed.close_vs_vwap_pts=2115; fvp.ed.poc_bin_idx=1698; xctx.minutes_since_last_smt_same_primary_7d=971; fvp.ed.value_area_range_pts=816; fvp.ed.total_volume_so_far=615; xctx.n_eql_side_low_7d=548; xctx.minutes_since_last_psp_side_bullish_24h=509 |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | fvp.ed.close_vs_vwap_pts=4959; fvp.ed.close_band_vwap_to_1sd_below=4241; fvp.ed.close_vs_vwap_sd=2206; xctx.minutes_since_last_sweep_side_low_24h=299; xctx.minutes_since_last_fvg_side_bearish_4h=292; xctx.n_vp_side_buying_7d=268; xctx.minutes_since_last_smt_side_low_7d=268; xctx.n_disp_side_bearish_24h=264; xctx.minutes_since_last_smt_same_primary_7d=251; xctx.minutes_since_last_smt_24h=226 |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | fvp.ed.close_vs_vwap_sd=9744; fvp.ed.close_vs_vwap_pts=1564; xctx.minutes_since_last_smt_same_primary_7d=493; fvp.ed.poc_pct_in_range=321; xctx.n_sweep_7d=316; xctx.minutes_since_last_smt_side_low_7d=314; xctx.n_fvg_same_primary_7d=313; xctx.minutes_since_last_psp_side_bearish_24h=308; xctx.minutes_since_last_psp_side_bullish_24h=282; xctx.minutes_since_last_psp_same_primary_7d=270 |
| at_fire | buying | label.next_60m.took_profile_low_so_far | fvp.ed.close_vs_vwap_sd=24740; fvp.ed.close_vs_vwap_pts=3764; fvp.ed.close_band_vwap_to_1sd_below=931; xctx.minutes_since_last_disp_side_bullish_24h=742; fvp.ed.close_vs_poc_pts=664; xctx.n_swing_4h=580; xctx.minutes_since_last_disp_24h=510; xctx.n_swing_side_high_4h=473; xctx.minutes_since_last_orb_24h=412; xctx.total_events_1h=388 |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | fvp.ed.close_vs_vwap_sd=30142; fvp.ed.close_vs_poc_pts=5032; fvp.ed.poc_pct_in_range=2465; fvp.ed.close_vs_vwap_pts=1693; fvp.ed.poc_bin_idx=1169; xctx.minutes_since_last_smt_same_primary_7d=905; fvp.ed.value_area_range_pts=847; xctx.n_fvg_side_bullish_7d=814; xctx.n_eql_side_low_7d=710; xctx.minutes_since_last_psp_side_bullish_24h=593 |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | fvp.ed.close_vs_vwap_sd=31790; fvp.ed.close_vs_poc_pts=3984; fvp.ed.close_vs_vwap_pts=2612; fvp.ed.poc_pct_in_range=1666; fvp.ed.poc_bin_idx=1096; fvp.ed.close_above_poc=765; xctx.minutes_since_last_ob_side_bearish_24h=666; xctx.minutes_since_last_smt_side_high_7d=567; xctx.minutes_since_last_ob_side_bullish_24h=559; fvp.ed.value_area_range_pts=544 |
| at_fire | all | label.next_240m.vah_touch.resistance_break_acceptance_3bar | fvp.ed.close_vs_vwap_sd=39672; fvp.ed.close_vs_poc_pts=4931; fvp.ed.close_vs_vwap_pts=3105; fvp.ed.poc_pct_in_range=2949; fvp.ed.poc_bin_idx=1177; fvp.ed.total_volume_so_far=1106; fvp.ed.close_above_poc=695; xctx.minutes_since_last_ob_side_bearish_24h=668; fvp.ed.value_area_range_pts=651; xctx.minutes_since_last_smt_side_low_7d=593 |
| at_fire | balanced | label.next_240m.vah_touch.resistance_rejection_3bar | fvp.ed.close_vs_vwap_sd=24022; fvp.ed.close_vs_poc_pts=2722; fvp.ed.close_band_1sd_2sd_below=2568; fvp.ed.poc_pct_in_range=1202; fvp.ed.close_vs_vwap_pts=757; xctx.minutes_since_last_smt_same_primary_7d=672; fvp.ed.poc_volume=598; fvp.ed.close_band_2sd_3sd_below=563; xctx.minutes_since_last_psp_side_bullish_24h=528; xctx.minutes_since_last_disp_side_bullish_24h=499 |
| at_fire | all | label.next_60m.took_profile_high_so_far | fvp.ed.close_vs_vwap_sd=126924; fvp.ed.close_vs_vwap_pts=12450; fvp.ed.poc_pct_in_range=5450; xctx.n_fvg_side_bearish_4h=2506; fvp.ed.close_band_vwap_to_1sd_above=2169; xctx.has_orb_1h=1871; xctx.minutes_since_last_orb_side_bullish_24h=1334; fvp.ed.poc_bin_idx=1310; xctx.n_fvg_7d=1231; xctx.has_vp_1h=1173 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
