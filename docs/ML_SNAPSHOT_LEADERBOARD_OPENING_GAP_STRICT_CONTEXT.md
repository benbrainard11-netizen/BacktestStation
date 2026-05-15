# ML snapshot leaderboard

_Generated `2026-05-15T04:43:37.790501+00:00`._

## Setup

- Matrix: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.parquet`
- Schema: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `gap_up, gap_down, all`
- Labels searched: `20` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\opening_gap_strict_context_leaderboard.csv | CSV leaderboard |
| data\ml\anchors\opening_gap_strict_context_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 9438 |
| schema_feature_columns | 2873 |
| schema_label_columns | 423 |
| grid_attempts | 60 |
| trained_ok | 57 |
| skipped | 3 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | 1032 | 37.1% | 0.872 | 0.809 | 0.629 | 104 | 96.2% | 59.0% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 1032 | 27.3% | 0.856 | 0.821 | 0.727 | 104 | 92.3% | 65.0% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 1854 | 9.8% | 0.849 | 0.904 | 0.902 | 186 | 44.6% | 34.8% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 1854 | 23.7% | 0.846 | 0.836 | 0.763 | 186 | 81.2% | 57.5% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 1854 | 32.7% | 0.836 | 0.807 | 0.673 | 186 | 89.2% | 56.6% |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | 822 | 19.1% | 0.828 | 0.858 | 0.809 | 83 | 71.1% | 52.0% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 1032 | 13.5% | 0.822 | 0.865 | 0.865 | 104 | 51.9% | 38.5% |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | 822 | 27.1% | 0.805 | 0.820 | 0.729 | 83 | 80.7% | 53.6% |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | 1032 | 83.5% | 0.786 | 0.835 | 0.835 | 104 | 96.2% | 12.6% |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | 1854 | 87.4% | 0.783 | 0.876 | 0.874 | 186 | 95.7% | 8.3% |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | 1032 | 62.6% | 0.779 | 0.726 | 0.626 | 104 | 86.5% | 23.9% |
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | 1854 | 7.6% | 0.777 | 0.924 | 0.924 | 186 | 23.7% | 16.1% |
| at_fire | gap_up | label.strict.next_60m.filled_then_continued_through | 1032 | 47.0% | 0.754 | 0.679 | 0.530 | 104 | 71.2% | 24.2% |
| at_fire | gap_down | label.strict.next_240m.midpoint_hold_rejection | 822 | 8.6% | 0.751 | 0.914 | 0.914 | 83 | 22.9% | 14.3% |
| at_fire | all | label.strict.next_240m.filled_then_continued_through | 1854 | 65.9% | 0.745 | 0.757 | 0.659 | 186 | 84.4% | 18.6% |
| at_fire | gap_down | label.strict.next_1d.partial_touch_rejected | 822 | 5.2% | 0.745 | 0.950 | 0.948 | 83 | 18.1% | 12.8% |
| at_fire | all | label.strict.next_240m.failed_fill_expanded_away | 1854 | 16.7% | 0.740 | 0.831 | 0.833 | 186 | 44.6% | 27.9% |
| at_fire | gap_up | label.strict.next_60m.gap_held_rejection | 1032 | 65.9% | 0.737 | 0.679 | 0.659 | 104 | 98.1% | 32.2% |
| at_fire | gap_up | label.strict.next_240m.gap_held_rejection | 1032 | 65.9% | 0.737 | 0.679 | 0.659 | 104 | 98.1% | 32.2% |
| at_fire | gap_up | label.strict.next_1d.gap_held_rejection | 1032 | 65.9% | 0.737 | 0.679 | 0.659 | 104 | 98.1% | 32.2% |
| at_fire | all | label.strict.next_60m.gap_held_rejection | 1854 | 63.7% | 0.733 | 0.676 | 0.637 | 186 | 96.8% | 33.1% |
| at_fire | all | label.strict.next_240m.gap_held_rejection | 1854 | 63.7% | 0.733 | 0.676 | 0.637 | 186 | 96.8% | 33.1% |
| at_fire | all | label.strict.next_1d.gap_held_rejection | 1854 | 63.7% | 0.733 | 0.676 | 0.637 | 186 | 96.8% | 33.1% |
| at_fire | all | label.strict.next_60m.gap_failed_acceptance | 1854 | 19.3% | 0.731 | 0.806 | 0.807 | 186 | 39.8% | 20.5% |
| at_fire | all | label.strict.next_240m.gap_failed_acceptance | 1854 | 19.3% | 0.731 | 0.806 | 0.807 | 186 | 39.8% | 20.5% |
| at_fire | all | label.strict.next_1d.gap_failed_acceptance | 1854 | 19.3% | 0.731 | 0.806 | 0.807 | 186 | 39.8% | 20.5% |
| at_fire | all | label.strict.next_60m.filled_then_continued_through | 1854 | 51.0% | 0.730 | 0.689 | 0.490 | 186 | 71.0% | 19.9% |
| at_fire | gap_down | label.strict.next_240m.failed_fill_expanded_away | 822 | 15.2% | 0.725 | 0.848 | 0.848 | 83 | 54.2% | 39.0% |
| at_fire | gap_up | label.strict.next_1d.failed_fill_expanded_away | 1032 | 9.6% | 0.722 | 0.904 | 0.904 | 104 | 23.1% | 13.5% |
| at_fire | gap_down | label.strict.next_1d.failed_fill_expanded_away | 822 | 5.0% | 0.721 | 0.950 | 0.950 | 83 | 18.1% | 13.1% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | ogap.ed.gap_size_pts=8522; xctx.minutes_since_last_eql_24h=1142; xctx.minutes_since_last_itr_side_bullish_7d=1069; xctx.minutes_since_last_swing_side_high_7d=729; regime.last_range_pts_same_primary_daily_itr=706; xctx.minutes_since_last_eql_side_high_7d=574; xctx.minutes_since_last_psp_7d=542; ogap.ed.previous_close_price=513; regime.last_range_pts_same_primary_london_itr=498; xctx.minutes_since_last_eql_7d=386 |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | ogap.ed.gap_size_pts=4070; xctx.minutes_since_last_swing_side_high_7d=1765; xctx.minutes_since_last_fvg_side_bullish_24h=1560; xctx.active_same_primary_concepts_1h=701; xctx.minutes_since_last_fvg_side_bullish_7d=647; xctx.n_disp_7d=559; xctx.minutes_since_last_sweep_same_primary_7d=461; liqgeom.age_min_any_source_same_primary_high_fresh_above=421; ts.month=414; xctx.minutes_since_last_disp_side_bullish_7d=402 |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | ogap.ed.gap_size_pts=5591; xctx.minutes_since_last_tp_7d=2828; xctx.minutes_since_last_disp_24h=2695; xctx.minutes_since_last_disp_side_bullish_7d=980; xd.has_swing_in_24h=864; xctx.minutes_since_last_disp_7d=688; xctx.n_disp_side_bullish_7d=444; liqgeom.distance_pts_eql_any_symbol_low_fresh_above=435; xctx.n_eql_24h=430; xctx.minutes_since_last_psp_7d=385 |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | ogap.ed.gap_size_pts=18024; xctx.minutes_since_last_swing_24h=3110; xctx.minutes_since_last_fvg_side_bullish_24h=1419; xctx.minutes_since_last_swing_side_high_24h=1025; regime.last_range_pts_same_primary_daily_itr=983; xctx.minutes_since_last_swing_side_high_7d=843; regime.last_range_pts_same_primary_any_itr=721; xctx.minutes_since_last_swing_7d=653; xctx.minutes_since_last_sweep_7d=588; xctx.minutes_since_last_disp_side_bearish_24h=533 |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | ogap.ed.gap_size_pts=23726; ogap.ed.gap_low=2070; xctx.minutes_since_last_swing_side_high_24h=1439; regime.last_range_pts_same_primary_daily_itr=1205; ogap.ed.previous_close_price=985; regime.last_true_range_pts_same_primary_daily_itr=778; xctx.minutes_since_last_disp_24h=652; xctx.minutes_since_last_swing_side_high_7d=600; ogap.ed.current_open_price=513; regime.last_range_pts_same_primary_asia_itr=497 |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | ogap.ed.gap_size_pts=11073; xctx.minutes_since_last_swing_side_low_7d=1036; xctx.minutes_since_last_eql_side_low_7d=723; xctx.minutes_since_last_sweep_7d=704; regime.last_range_pts_same_primary_asia_itr=670; xctx.minutes_since_last_macro_side_high_7d=668; xctx.n_swing_side_high_24h=663; ogap.ed.previous_close_price=637; regime.last_range_pts_same_primary_london_itr=488; xctx.minutes_since_last_fvg_4h=481 |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | xctx.minutes_since_last_swing_side_high_7d=3330; xctx.minutes_since_last_orb_side_bullish_7d=765; ts.year=726; ogap.ed.gap_size_pts=627; xctx.n_psp_7d=491; xctx.n_eql_24h=465; xd.has_tp_in_24h=465; liqgeom.age_min_eql_any_symbol_low_fresh_below=364; xctx.minutes_since_last_orb_side_bearish_7d=336; xctx.n_disp_side_bullish_7d=330 |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | ogap.ed.gap_size_pts=11286; ogap.ed.previous_close_price=1148; ogap.ed.current_open_price=1003; xctx.minutes_since_last_eql_side_low_7d=797; regime.last_range_pts_same_primary_asia_itr=583; ts.year=530; xctx.n_swing_side_high_24h=515; xctx.minutes_since_last_disp_side_bearish_24h=355; xctx.minutes_since_last_orb_side_doji_7d=320; xctx.minutes_since_last_swing_side_high_7d=255 |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | xctx.minutes_since_last_swing_side_high_7d=3950; xd.has_swing_in_24h=730; ts.year=651; ogap.ed.gap_size_pts=461; xctx.n_disp_side_bullish_7d=458; liqgeom.age_min_eql_same_primary_any_side_fresh_above=385; liqgeom.age_min_eql_same_primary_high_fresh_above=360; xctx.minutes_since_last_eql_24h=353; liqgeom.age_min_eql_any_symbol_low_fresh_below=284; liqgeom.age_min_eql_any_symbol_high_wick_taken_below=278 |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | ogap.ed.gap_size_pts=4372; xd.has_swing_in_24h=2208; xctx.minutes_since_last_disp_24h=2127; xctx.minutes_since_last_orb_24h=1222; xctx.minutes_since_last_disp_7d=564; xctx.minutes_since_last_orb_side_bullish_7d=536; xctx.n_disp_side_bullish_7d=529; xctx.minutes_since_last_tp_7d=511; xctx.minutes_since_last_orb_7d=472; xctx.minutes_since_last_eql_side_low_7d=410 |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | xctx.minutes_since_last_fvg_side_bearish_7d=2350; ogap.ed.gap_size_pts=1977; xctx.minutes_since_last_psp_7d=875; liqgeom.age_min_any_source_same_primary_high_fresh_above=859; xctx.minutes_since_last_swing_side_high_7d=806; xctx.minutes_since_last_sweep_same_primary_7d=643; xctx.n_ob_side_bullish_7d=623; xctx.minutes_since_last_swing_side_low_7d=447; xd.has_swing_in_24h=437; xctx.n_vp_side_balanced_7d=359 |
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | xd.has_swing_in_24h=4398; ogap.ed.gap_size_pts=2866; xctx.minutes_since_last_disp_24h=1704; xctx.n_disp_side_bullish_7d=607; xctx.minutes_since_last_psp_7d=512; xctx.minutes_since_last_disp_7d=511; xctx.n_eql_24h=376; xctx.minutes_since_last_itr_side_doji_7d=329; ogap.side_gap_down=313; obgeom.age_min_any_symbol_bearish_body_filled_below=286 |
| at_fire | gap_up | label.strict.next_60m.filled_then_continued_through | ogap.ed.gap_size_pts=2432; xctx.minutes_since_last_fvg_side_bearish_7d=1800; xctx.minutes_since_last_swing_side_high_7d=581; regime.last_close_location_same_primary_ny_itr=536; xctx.minutes_since_last_fvg_side_bearish_24h=418; liqgeom.age_min_any_source_same_primary_high_fresh_above=404; xctx.n_sweep_7d=319; regime.last_true_range_pts_same_primary_london_itr=310; xctx.minutes_since_last_fvg_side_bullish_24h=299; xctx.n_psp_7d=265 |
| at_fire | gap_down | label.strict.next_240m.midpoint_hold_rejection | ogap.ed.gap_size_pts=2080; xctx.minutes_since_last_ob_side_bearish_7d=422; liqgeom.age_min_any_source_same_primary_any_side_fresh_above=288; regime.last_true_range_pts_any_symbol_asia_itr=247; regime.n_expansion_7d_any_symbol_ny_itr=217; regime.last_range_pts_any_symbol_asia_itr=197; liqgeom.age_min_any_source_same_primary_low_horizon_expired_above=190; regime.last_range_pts_same_primary_london_itr=187; obgeom.body_width_pts_any_symbol_bullish_invalidated_below=185; liqgeom.age_min_eql_any_symbol_high_horizon_expired_below=180 |
| at_fire | all | label.strict.next_240m.filled_then_continued_through | ogap.ed.gap_size_pts=9283; xctx.minutes_since_last_swing_side_high_24h=2910; xctx.n_fvg_same_primary_24h=1695; xctx.minutes_since_last_fvg_side_bullish_24h=1494; xctx.minutes_since_last_disp_same_primary_24h=1322; regime.last_range_pts_same_primary_any_itr=1007; xctx.minutes_since_last_swing_side_high_7d=761; regime.last_range_pts_any_symbol_asia_itr=532; regime.last_range_pts_same_primary_daily_itr=406; regime.last_range_percentile_prev10_any_symbol_weekly_itr=336 |

## Skipped Summary

| status | count |
|---|---|
| skip_train_imbalance | 2 |
| skip_test_imbalance | 1 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
