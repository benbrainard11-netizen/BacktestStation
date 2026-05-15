# ML snapshot leaderboard

_Generated `2026-05-15T03:46:40.458800+00:00`._

## Setup

- Matrix: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet`
- Schema: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `gap_up, gap_down, all`
- Labels searched: `228` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\opening_gap_snapshot_leaderboard_xctx_gapctx_obgeom_liqgeom_regime.csv | CSV leaderboard |
| data\ml\anchors\opening_gap_snapshot_leaderboard_xctx_gapctx_obgeom_liqgeom_regime.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 9438 |
| schema_feature_columns | 2873 |
| schema_label_columns | 396 |
| grid_attempts | 684 |
| trained_ok | 530 |
| skipped | 154 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | gap_up | label.next_240m.range_expanded_1x_gap | 1032 | 92.3% | 0.996 | 0.937 | 0.923 | 104 | 100.0% | 7.7% |
| at_fire | gap_up | label.next_1d.range_expanded_2x_gap | 1032 | 93.6% | 0.993 | 0.938 | 0.936 | 104 | 100.0% | 6.4% |
| at_fire | all | label.next_1d.range_expanded_2x_gap | 1854 | 96.2% | 0.984 | 0.962 | 0.962 | 186 | 100.0% | 3.8% |
| at_fire | all | label.next_240m.range_expanded_1x_gap | 1854 | 95.0% | 0.976 | 0.962 | 0.950 | 186 | 99.5% | 4.5% |
| at_fire | all | label.next_240m.range_expanded_2x_gap | 1854 | 88.0% | 0.974 | 0.950 | 0.880 | 186 | 100.0% | 12.0% |
| at_fire | gap_up | label.next_60m.range_expanded_1x_gap | 1032 | 89.1% | 0.972 | 0.914 | 0.891 | 104 | 100.0% | 10.9% |
| at_fire | all | label.next_60m.range_expanded_1x_gap | 1854 | 92.2% | 0.970 | 0.953 | 0.922 | 186 | 100.0% | 7.8% |
| at_fire | gap_down | label.next_240m.range_expanded_2x_gap | 822 | 90.6% | 0.963 | 0.942 | 0.906 | 83 | 100.0% | 9.4% |
| at_fire | gap_up | label.next_240m.range_expanded_2x_gap | 1032 | 85.9% | 0.961 | 0.922 | 0.859 | 104 | 100.0% | 14.1% |
| at_fire | gap_up | label.next_60m.range_expanded_2x_gap | 1032 | 75.3% | 0.959 | 0.877 | 0.753 | 104 | 100.0% | 24.7% |
| at_fire | all | label.next_60m.range_expanded_2x_gap | 1854 | 78.3% | 0.957 | 0.899 | 0.783 | 186 | 100.0% | 21.7% |
| at_fire | gap_down | label.next_60m.range_expanded_2x_gap | 822 | 82.1% | 0.952 | 0.911 | 0.821 | 83 | 100.0% | 17.9% |
| at_fire | all | label.full_horizon.resistance_rejection_3bar | 1854 | 27.0% | 0.932 | 0.848 | 0.730 | 186 | 88.2% | 61.1% |
| at_fire | all | label.next_60m.resistance_rejection_3bar | 1854 | 27.0% | 0.932 | 0.848 | 0.730 | 186 | 88.2% | 61.1% |
| at_fire | all | label.next_240m.resistance_rejection_3bar | 1854 | 27.0% | 0.932 | 0.848 | 0.730 | 186 | 88.2% | 61.1% |
| at_fire | all | label.next_1d.resistance_rejection_3bar | 1854 | 27.0% | 0.932 | 0.848 | 0.730 | 186 | 88.2% | 61.1% |
| at_fire | all | label.next_5d.resistance_rejection_3bar | 1854 | 27.0% | 0.932 | 0.848 | 0.730 | 186 | 88.2% | 61.1% |
| at_fire | all | label.next_20d.resistance_rejection_3bar | 1854 | 27.0% | 0.932 | 0.848 | 0.730 | 186 | 88.2% | 61.1% |
| at_fire | all | label.full_horizon.support_rejection_3bar | 1854 | 36.7% | 0.920 | 0.818 | 0.633 | 186 | 94.6% | 57.9% |
| at_fire | all | label.next_60m.support_rejection_3bar | 1854 | 36.7% | 0.920 | 0.818 | 0.633 | 186 | 94.6% | 57.9% |
| at_fire | all | label.next_240m.support_rejection_3bar | 1854 | 36.7% | 0.920 | 0.818 | 0.633 | 186 | 94.6% | 57.9% |
| at_fire | all | label.next_1d.support_rejection_3bar | 1854 | 36.7% | 0.920 | 0.818 | 0.633 | 186 | 94.6% | 57.9% |
| at_fire | all | label.next_5d.support_rejection_3bar | 1854 | 36.7% | 0.920 | 0.818 | 0.633 | 186 | 94.6% | 57.9% |
| at_fire | all | label.next_20d.support_rejection_3bar | 1854 | 36.7% | 0.920 | 0.818 | 0.633 | 186 | 94.6% | 57.9% |
| at_fire | gap_down | label.next_60m.range_expanded_1x_gap | 822 | 96.1% | 0.917 | 0.939 | 0.961 | 83 | 100.0% | 3.9% |
| at_fire | all | label.full_horizon.resistance_break_acceptance_3bar | 1854 | 9.3% | 0.886 | 0.907 | 0.907 | 186 | 37.6% | 28.4% |
| at_fire | all | label.next_60m.resistance_break_acceptance_3bar | 1854 | 9.3% | 0.886 | 0.907 | 0.907 | 186 | 37.6% | 28.4% |
| at_fire | all | label.next_240m.resistance_break_acceptance_3bar | 1854 | 9.3% | 0.886 | 0.907 | 0.907 | 186 | 37.6% | 28.4% |
| at_fire | all | label.next_1d.resistance_break_acceptance_3bar | 1854 | 9.3% | 0.886 | 0.907 | 0.907 | 186 | 37.6% | 28.4% |
| at_fire | all | label.next_5d.resistance_break_acceptance_3bar | 1854 | 9.3% | 0.886 | 0.907 | 0.907 | 186 | 37.6% | 28.4% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | gap_up | label.next_240m.range_expanded_1x_gap | ogap.ed.gap_size_pts=3831; regime.last_range_pts_same_primary_any_itr=834; xctx.minutes_since_last_orb_7d=550; liqgeom.n_swing_same_primary_any_side_fresh_within_100pts=399; xctx.minutes_since_last_disp_side_bullish_7d=308; regime.last_range_pts_same_primary_daily_itr=270; xctx.minutes_since_last_orb_side_bullish_7d=259; obgeom.age_min_any_symbol_bullish_body_filled_above=224; liqgeom.age_min_eql_any_symbol_any_side_horizon_expired_above=187; xctx.minutes_since_last_fvg_same_primary_7d=183 |
| at_fire | gap_up | label.next_1d.range_expanded_2x_gap | ogap.ed.gap_size_pts=3027; xctx.minutes_since_last_psp_side_bearish_7d=473; regime.last_true_range_pts_same_primary_ny_itr=348; regime.last_true_range_pts_same_primary_any_itr=345; xctx.minutes_since_last_orb_7d=288; regime.last_range_pts_same_primary_asia_itr=257; regime.last_range_pts_same_primary_any_itr=242; obgeom.age_min_any_symbol_any_side_body_filled_above=226; regime.last_true_range_pts_same_primary_london_itr=219; xctx.minutes_since_last_orb_side_bullish_7d=165 |
| at_fire | all | label.next_1d.range_expanded_2x_gap | ogap.ed.gap_size_pts=7474; regime.minutes_since_last_same_primary_any_itr=1759; regime.last_range_pts_same_primary_daily_itr=1005; regime.minutes_since_last_same_primary_ny_itr=789; regime.last_true_range_pts_same_primary_london_itr=653; regime.last_true_range_pts_same_primary_any_itr=525; regime.last_true_range_pts_same_primary_daily_itr=464; xctx.minutes_since_last_fvg_side_bullish_24h=461; regime.last_range_pts_same_primary_any_itr=449; regime.minutes_since_last_same_primary_daily_itr=379 |
| at_fire | all | label.next_240m.range_expanded_1x_gap | ogap.ed.gap_size_pts=12283; regime.minutes_since_last_same_primary_ny_itr=1382; regime.minutes_since_last_same_primary_any_itr=1208; regime.last_range_pts_same_primary_daily_itr=1164; regime.last_range_pts_same_primary_any_itr=855; xctx.minutes_since_last_disp_side_bullish_7d=836; regime.last_true_range_pts_same_primary_daily_itr=611; regime.last_true_range_pts_same_primary_london_itr=505; regime.minutes_since_last_same_primary_daily_itr=485; liqgeom.n_swing_same_primary_any_side_fresh_within_100pts=477 |
| at_fire | all | label.next_240m.range_expanded_2x_gap | ogap.ed.gap_size_pts=28675; regime.last_range_pts_same_primary_asia_itr=3168; regime.last_range_pts_same_primary_weekly_itr=1853; regime.last_true_range_pts_same_primary_daily_itr=1557; regime.last_range_pts_same_primary_london_itr=1260; regime.last_true_range_pts_same_primary_weekly_itr=1246; regime.last_range_pts_same_primary_any_itr=1177; xctx.n_fvg_24h=1171; regime.last_range_pts_same_primary_daily_itr=780; regime.last_true_range_pts_same_primary_asia_itr=580 |
| at_fire | gap_up | label.next_60m.range_expanded_1x_gap | ogap.ed.gap_size_pts=5121; xctx.minutes_since_last_swing_side_high_7d=493; liqgeom.n_any_source_same_primary_any_side_fresh_within_100pts=430; xctx.minutes_since_last_tp_7d=423; regime.last_range_pts_same_primary_daily_itr=387; regime.last_range_pts_same_primary_any_itr=372; xctx.minutes_since_last_orb_7d=351; regime.last_true_range_pts_same_primary_london_itr=280; regime.last_true_range_pts_same_primary_any_itr=275; regime.last_range_pts_same_primary_asia_itr=269 |
| at_fire | all | label.next_60m.range_expanded_1x_gap | ogap.ed.gap_size_pts=19460; regime.last_true_range_pts_same_primary_daily_itr=2374; regime.last_range_pts_same_primary_weekly_itr=1401; regime.last_true_range_pts_same_primary_weekly_itr=1186; regime.last_true_range_pts_same_primary_london_itr=768; regime.last_range_pts_same_primary_any_itr=724; ogap.ed.previous_close_price=666; regime.last_range_pts_same_primary_asia_itr=636; xctx.minutes_since_last_sweep_same_primary_7d=568; regime.last_range_pts_same_primary_daily_itr=517 |
| at_fire | gap_down | label.next_240m.range_expanded_2x_gap | ogap.ed.gap_size_pts=16180; regime.last_range_pts_same_primary_asia_itr=1274; regime.last_range_pts_same_primary_london_itr=1117; regime.last_range_pts_same_primary_daily_itr=900; xctx.n_fvg_24h=719; xctx.minutes_since_last_sweep_7d=686; xctx.minutes_since_last_sweep_same_primary_7d=611; regime.last_true_range_pts_same_primary_asia_itr=432; xctx.minutes_since_last_swing_side_high_24h=418; regime.last_range_pts_any_symbol_asia_itr=343 |
| at_fire | gap_up | label.next_240m.range_expanded_2x_gap | ogap.ed.gap_size_pts=8189; xctx.minutes_since_last_tp_7d=2754; regime.last_range_pts_same_primary_asia_itr=871; regime.last_range_pts_any_symbol_asia_itr=392; regime.last_true_range_pts_same_primary_ny_itr=385; xctx.minutes_since_last_orb_side_bullish_7d=371; regime.last_true_range_pts_same_primary_weekly_itr=361; xctx.minutes_since_last_tp_same_primary_7d=358; regime.last_range_pts_same_primary_london_itr=312; regime.last_true_range_pts_same_primary_asia_itr=310 |
| at_fire | gap_up | label.next_60m.range_expanded_2x_gap | ogap.ed.gap_size_pts=13469; regime.last_range_pts_same_primary_asia_itr=1810; regime.last_range_pts_same_primary_daily_itr=1501; xctx.minutes_since_last_swing_side_low_24h=1286; regime.last_range_pts_same_primary_weekly_itr=588; regime.last_true_range_pts_same_primary_any_itr=454; regime.last_true_range_pts_same_primary_ny_itr=390; regime.last_true_range_pts_same_primary_weekly_itr=327; xctx.minutes_since_last_sweep_same_primary_7d=284; liqgeom.n_swing_same_primary_high_close_taken_within_100pts=264 |
| at_fire | all | label.next_60m.range_expanded_2x_gap | ogap.ed.gap_size_pts=36541; regime.last_range_pts_same_primary_asia_itr=5154; regime.last_range_pts_same_primary_daily_itr=3274; regime.last_true_range_pts_same_primary_daily_itr=1980; regime.last_range_pts_same_primary_any_itr=1399; regime.last_true_range_pts_same_primary_any_itr=1140; regime.last_true_range_pts_same_primary_weekly_itr=1033; regime.last_range_pts_same_primary_ny_itr=733; regime.last_true_range_pts_same_primary_asia_itr=644; xctx.minutes_since_last_sweep_same_primary_7d=641 |
| at_fire | gap_down | label.next_60m.range_expanded_2x_gap | ogap.ed.gap_size_pts=20962; regime.last_range_pts_same_primary_asia_itr=1618; regime.last_range_pts_same_primary_daily_itr=1377; xctx.n_swing_side_high_24h=799; regime.last_true_range_pts_same_primary_daily_itr=789; regime.last_range_pts_same_primary_london_itr=676; liqgeom.distance_pts_eql_any_symbol_low_fresh_above=546; regime.last_range_pts_same_primary_ny_itr=537; regime.last_true_range_pts_same_primary_any_itr=492; xctx.minutes_since_last_sweep_same_primary_7d=484 |
| at_fire | all | label.full_horizon.resistance_rejection_3bar | ogap.side_gap_down=52923; ogap.side_gap_up=6581; ogap.ed.gap_size_pts=5802; ogap.ed.gap_direction_gap_down=1798; xctx.minutes_since_last_smt_side_high_7d=664; xctx.n_sweep_side_low_24h=522; xctx.minutes_since_last_smt_7d=513; regime.last_close_location_any_symbol_any_itr=478; xctx.n_psp_7d=467; ts.year=440 |
| at_fire | all | label.next_60m.resistance_rejection_3bar | ogap.side_gap_down=52923; ogap.side_gap_up=6581; ogap.ed.gap_size_pts=5802; ogap.ed.gap_direction_gap_down=1798; xctx.minutes_since_last_smt_side_high_7d=664; xctx.n_sweep_side_low_24h=522; xctx.minutes_since_last_smt_7d=513; regime.last_close_location_any_symbol_any_itr=478; xctx.n_psp_7d=467; ts.year=440 |
| at_fire | all | label.next_240m.resistance_rejection_3bar | ogap.side_gap_down=52923; ogap.side_gap_up=6581; ogap.ed.gap_size_pts=5802; ogap.ed.gap_direction_gap_down=1798; xctx.minutes_since_last_smt_side_high_7d=664; xctx.n_sweep_side_low_24h=522; xctx.minutes_since_last_smt_7d=513; regime.last_close_location_any_symbol_any_itr=478; xctx.n_psp_7d=467; ts.year=440 |

## Skipped Summary

| status | count |
|---|---|
| skip_train_imbalance | 123 |
| skip_test_imbalance | 31 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
