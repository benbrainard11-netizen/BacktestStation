# ML snapshot leaderboard

_Generated `2026-05-13T03:01:31.874659+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshots_xctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `buying, selling, balanced, all`
- Labels searched: `12` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshot_leaderboard_v2_xctx.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshot_leaderboard_v2_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 36095 |
| schema_feature_columns | 657 |
| schema_label_columns | 139 |
| grid_attempts | 48 |
| trained_ok | 47 |
| skipped | 1 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | 1134 | 3.3% | 0.912 | 0.967 | 0.967 | 114 | 18.4% | 15.2% |
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | 1806 | 4.7% | 0.912 | 0.951 | 0.953 | 181 | 23.2% | 18.5% |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | 1806 | 5.0% | 0.909 | 0.950 | 0.950 | 181 | 27.6% | 22.6% |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | 6552 | 4.4% | 0.908 | 0.956 | 0.956 | 656 | 23.9% | 19.5% |
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | 6552 | 4.7% | 0.906 | 0.953 | 0.953 | 656 | 24.1% | 19.4% |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | 1806 | 5.9% | 0.906 | 0.942 | 0.941 | 181 | 27.6% | 21.8% |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | 1134 | 5.6% | 0.904 | 0.943 | 0.944 | 114 | 27.2% | 21.5% |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | 3612 | 5.2% | 0.893 | 0.948 | 0.948 | 362 | 22.7% | 17.4% |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | 3612 | 4.9% | 0.890 | 0.951 | 0.951 | 362 | 22.1% | 17.2% |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | 1806 | 6.4% | 0.888 | 0.935 | 0.936 | 181 | 22.1% | 15.7% |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | 1134 | 7.4% | 0.881 | 0.924 | 0.926 | 114 | 29.8% | 22.4% |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | 6552 | 5.8% | 0.879 | 0.942 | 0.942 | 656 | 23.8% | 18.0% |
| at_fire | buying | label.val_touch.support_break_acceptance_3bar | 1806 | 4.0% | 0.872 | 0.960 | 0.960 | 181 | 17.7% | 13.7% |
| at_fire | selling | label.poc_touch.resistance_break_acceptance_3bar | 1134 | 9.7% | 0.866 | 0.901 | 0.903 | 114 | 31.6% | 21.9% |
| at_fire | balanced | label.val_touch.support_break_acceptance_3bar | 3612 | 6.8% | 0.862 | 0.932 | 0.932 | 362 | 21.0% | 14.2% |
| at_fire | selling | label.val_touch.support_rejection_3bar | 1134 | 6.2% | 0.859 | 0.940 | 0.938 | 114 | 23.7% | 17.5% |
| at_fire | selling | label.poc_touch.resistance_rejection_3bar | 1134 | 7.0% | 0.850 | 0.929 | 0.930 | 114 | 21.1% | 14.1% |
| at_fire | all | label.val_touch.support_rejection_3bar | 6552 | 5.5% | 0.849 | 0.945 | 0.945 | 656 | 20.0% | 14.5% |
| at_fire | buying | label.poc_touch.support_break_acceptance_3bar | 1806 | 10.4% | 0.844 | 0.895 | 0.896 | 181 | 32.0% | 21.7% |
| at_fire | selling | label.vwap_touch.support_rejection_3bar | 1134 | 6.6% | 0.842 | 0.934 | 0.934 | 114 | 19.3% | 12.7% |
| at_fire | balanced | label.val_touch.support_rejection_3bar | 3612 | 6.0% | 0.842 | 0.940 | 0.940 | 362 | 20.2% | 14.2% |
| at_fire | all | label.vwap_touch.resistance_rejection_3bar | 6552 | 10.5% | 0.827 | 0.895 | 0.895 | 656 | 25.8% | 15.3% |
| at_fire | buying | label.poc_touch.support_rejection_3bar | 1806 | 10.8% | 0.826 | 0.894 | 0.892 | 181 | 23.2% | 12.4% |
| at_fire | all | label.vwap_touch.resistance_break_acceptance_3bar | 6552 | 10.4% | 0.821 | 0.896 | 0.896 | 656 | 26.4% | 16.0% |
| at_fire | buying | label.val_touch.support_rejection_3bar | 1806 | 4.1% | 0.817 | 0.959 | 0.959 | 181 | 14.9% | 10.8% |
| at_fire | all | label.poc_touch.resistance_rejection_3bar | 6552 | 12.1% | 0.816 | 0.879 | 0.879 | 656 | 26.5% | 14.5% |
| at_fire | balanced | label.poc_touch.resistance_rejection_3bar | 3612 | 12.3% | 0.815 | 0.877 | 0.877 | 362 | 32.0% | 19.8% |
| at_fire | balanced | label.vwap_touch.resistance_rejection_3bar | 3612 | 11.5% | 0.810 | 0.884 | 0.885 | 362 | 29.8% | 18.3% |
| at_fire | all | label.poc_touch.resistance_break_acceptance_3bar | 6552 | 11.3% | 0.810 | 0.887 | 0.887 | 656 | 27.9% | 16.6% |
| at_fire | balanced | label.vwap_touch.resistance_break_acceptance_3bar | 3612 | 10.9% | 0.805 | 0.890 | 0.891 | 362 | 25.7% | 14.8% |
| at_fire | balanced | label.poc_touch.resistance_break_acceptance_3bar | 3612 | 10.1% | 0.798 | 0.897 | 0.899 | 362 | 19.6% | 9.5% |
| at_fire | balanced | label.vwap_touch.support_rejection_3bar | 3612 | 13.4% | 0.794 | 0.866 | 0.866 | 362 | 30.1% | 16.7% |
| at_fire | all | label.poc_touch.support_break_acceptance_3bar | 6552 | 12.6% | 0.789 | 0.874 | 0.874 | 656 | 28.2% | 15.6% |
| at_fire | all | label.vwap_touch.support_break_acceptance_3bar | 6552 | 12.8% | 0.780 | 0.872 | 0.872 | 656 | 26.1% | 13.3% |
| at_fire | all | label.poc_touch.support_rejection_3bar | 6552 | 13.0% | 0.778 | 0.870 | 0.870 | 656 | 25.5% | 12.4% |
| at_fire | balanced | label.vwap_touch.support_break_acceptance_3bar | 3612 | 12.5% | 0.777 | 0.874 | 0.875 | 362 | 27.1% | 14.5% |
| at_fire | all | label.vwap_touch.support_rejection_3bar | 6552 | 13.7% | 0.776 | 0.863 | 0.863 | 656 | 24.8% | 11.2% |
| at_fire | buying | label.poc_touch.resistance_rejection_3bar | 1806 | 14.9% | 0.775 | 0.850 | 0.851 | 181 | 33.7% | 18.8% |
| at_fire | buying | label.poc_touch.resistance_break_acceptance_3bar | 1806 | 14.6% | 0.772 | 0.852 | 0.854 | 181 | 33.1% | 18.6% |
| at_fire | balanced | label.poc_touch.support_break_acceptance_3bar | 3612 | 13.5% | 0.763 | 0.865 | 0.865 | 362 | 25.1% | 11.6% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=3690; vp.ed.close_vs_poc_pts=1688; vp.ed.poc_pct_in_range=249; xctx.n_vp_side_buying_7d=194; xctx.n_psp_7d=180; xctx.n_fvg_side_bullish_7d=177; xctx.n_ob_7d=173; xctx.total_events_4h=172; xctx.minutes_since_last_psp_side_bearish_24h=171; vp.ed.poc_volume=166 |
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=11853; vp.ed.close_vs_vwap_pts=1307; vp.ed.poc_pct_in_range=411; xctx.minutes_since_last_tp_side_bearish_7d=399; xctx.minutes_since_last_orb_side_doji_7d=321; xctx.total_same_primary_events_7d=310; vp.ed.value_area_range_pts=305; xctx.minutes_since_last_psp_same_primary_7d=293; xctx.n_fvg_7d=269; vp.ed.poc_volume=259 |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | vp.ed.close_vs_vwap_sd=11348; vp.ed.close_vs_vwap_pts=1198; vp.ed.value_area_range_pts=291; xctx.n_fvg_side_bullish_24h=286; xctx.n_fvg_4h=276; vp.ed.poc_volume=260; xctx.n_disp_side_bearish_7d=252; vp.ed.poc_pct_in_range=241; xctx.n_swing_7d=237; xctx.n_vp_side_selling_7d=237 |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | vp.ed.close_vs_vwap_sd=32761; vp.ed.close_vs_poc_pts=5385; vp.ed.poc_pct_in_range=3848; vp.ed.close_vs_vwap_pts=1444; xctx.minutes_since_last_psp_same_primary_24h=614; vp.ed.poc_bin_idx=601; vp.ed.poc_volume=503; xctx.minutes_since_last_eql_side_low_24h=486; vp.ed.value_area_range_pts=483; xctx.n_swing_7d=449 |
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=31929; vp.ed.close_vs_poc_pts=6514; vp.ed.poc_pct_in_range=3141; vp.ed.close_vs_vwap_pts=1497; vp.ed.poc_bin_idx=644; vp.ed.total_volume=637; vp.ed.close_above_poc=607; xctx.n_fvg_side_bearish_7d=545; xctx.n_swing_side_low_7d=542; xctx.n_fvg_same_primary_7d=515 |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | vp.ed.close_vs_vwap_pts=9863; vp.ed.close_vs_vwap_sd=5932; vp.ed.n_bars=348; xctx.minutes_since_last_tp_side_bearish_7d=319; vp.ed.poc_pct_in_range=282; xctx.minutes_since_last_ob_side_bullish_24h=277; vp.ed.poc_volume=273; xctx.minutes_since_last_psp_side_bullish_24h=272; xctx.minutes_since_last_disp_side_bullish_24h=260; vp.ed.total_volume=243 |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=7263; vp.ed.close_vs_vwap_pts=1877; xctx.minutes_since_last_psp_same_primary_24h=357; xctx.n_fvg_side_bearish_24h=269; xctx.n_disp_side_bullish_7d=241; vp.ed.total_volume=218; xctx.n_swing_same_primary_7d=218; xctx.n_ft_side_bullish_7d=217; xctx.n_swing_side_high_7d=213; xctx.minutes_since_last_psp_side_bearish_24h=211 |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=19972; vp.ed.close_vs_poc_pts=3484; vp.ed.poc_pct_in_range=1515; vp.ed.close_vs_vwap_pts=594; vp.ed.total_volume=526; xctx.n_fvg_side_bearish_7d=490; xctx.minutes_since_last_psp_side_bearish_24h=375; xctx.total_same_primary_events_7d=349; xctx.n_vp_side_balanced_7d=322; xctx.minutes_since_last_tp_side_bearish_7d=311 |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | vp.ed.close_vs_vwap_sd=20375; vp.ed.close_vs_poc_pts=3085; vp.ed.poc_pct_in_range=1244; vp.ed.close_band_1sd_2sd_below=787; xctx.n_ob_side_bearish_7d=481; vp.ed.close_vs_vwap_pts=422; xctx.minutes_since_last_psp_same_primary_24h=415; xctx.total_same_primary_events_4h=372; xctx.n_eql_side_low_7d=366; xctx.total_events_1h=359 |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=7815; vp.ed.close_vs_vwap_pts=7579; vp.ed.total_volume=398; xctx.n_fvg_side_bearish_7d=371; vp.ed.poc_volume=291; xctx.minutes_since_last_ob_side_bullish_24h=274; xctx.total_same_primary_events_7d=272; xctx.n_eql_same_primary_7d=263; vp.ed.poc_pct_in_range=253; xctx.minutes_since_last_ob_same_primary_24h=245 |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | vp.ed.close_vs_vwap_pts=6634; vp.ed.close_vs_vwap_sd=4622; vp.ed.value_area_range_pts=388; xctx.minutes_since_last_psp_same_primary_24h=339; xctx.n_swing_side_high_7d=325; vp.ed.n_bars=286; xctx.minutes_since_last_vp_7d=286; xctx.n_eql_side_high_7d=265; xctx.n_orb_side_bullish_7d=255; vp.ed.poc_pct_in_range=254 |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=27473; vp.ed.close_vs_poc_pts=9050; vp.ed.poc_pct_in_range=3535; vp.ed.close_vs_vwap_pts=1185; vp.ed.value_area_range_pts=963; vp.ed.poc_bin_idx=902; vp.ed.n_bars=737; vp.ed.total_volume=653; vp.ed.poc_volume=598; vp.ed.close_above_poc=589 |
| at_fire | buying | label.val_touch.support_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=6724; vp.ed.close_vs_poc_pts=1820; xctx.minutes_since_last_psp_side_bullish_24h=391; vp.ed.total_volume=327; vp.ed.value_area_range_pts=274; xctx.minutes_since_last_eql_24h=238; xctx.n_ob_7d=210; xctx.minutes_since_last_psp_same_primary_7d=210; xctx.total_events_7d=205; xctx.n_ob_side_bullish_7d=197 |
| at_fire | selling | label.poc_touch.resistance_break_acceptance_3bar | vp.ed.close_vs_poc_pts=11385; vp.ed.close_vs_vwap_sd=456; vp.ed.poc_volume=368; vp.ed.close_vs_vwap_pts=351; vp.ed.close_above_poc=331; xctx.minutes_since_last_psp_same_primary_24h=328; vp.ed.poc_pct_in_range=292; xctx.minutes_since_last_swing_side_low_24h=273; vp.ed.period_range_pts=267; xctx.minutes_since_last_disp_same_primary_24h=252 |
| at_fire | balanced | label.val_touch.support_break_acceptance_3bar | vp.ed.close_vs_vwap_sd=18398; vp.ed.close_vs_poc_pts=2034; vp.ed.poc_pct_in_range=1398; vp.ed.close_vs_vwap_pts=1205; vp.ed.value_area_range_pts=446; xctx.minutes_since_last_orb_side_doji_7d=410; xctx.minutes_since_last_psp_side_bearish_24h=381; vp.ed.close_band_vwap_to_1sd_above=375; xctx.n_sweep_side_high_7d=372; xctx.minutes_since_last_disp_same_primary_24h=367 |

## Skipped Summary

| status | count |
|---|---|
| skip_test_imbalance | 1 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
