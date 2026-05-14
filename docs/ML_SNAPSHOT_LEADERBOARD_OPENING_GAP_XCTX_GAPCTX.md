# ML snapshot leaderboard

_Generated `2026-05-14T04:11:15.208937+00:00`._

## Setup

- Matrix: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx.parquet`
- Schema: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `all, gap_up, gap_down`
- Labels searched: `15` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\opening_gap_snapshot_leaderboard_xctx_gapctx.csv | CSV leaderboard |
| data\ml\anchors\opening_gap_snapshot_leaderboard_xctx_gapctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 9438 |
| schema_feature_columns | 1047 |
| schema_label_columns | 396 |
| grid_attempts | 45 |
| trained_ok | 45 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 1032 | 27.3% | 0.850 | 0.828 | 0.727 | 104 | 90.4% | 63.1% |
| at_fire | gap_up | label.next_240m.fully_filled | 1032 | 72.7% | 0.850 | 0.828 | 0.727 | 104 | 94.2% | 21.6% |
| at_fire | all | label.next_1d.fully_filled | 1854 | 90.2% | 0.849 | 0.905 | 0.902 | 186 | 98.9% | 8.7% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 1032 | 37.1% | 0.849 | 0.793 | 0.629 | 104 | 97.1% | 60.0% |
| at_fire | gap_up | label.next_60m.fully_filled | 1032 | 62.9% | 0.849 | 0.793 | 0.629 | 104 | 95.2% | 32.3% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 1854 | 23.7% | 0.841 | 0.836 | 0.763 | 186 | 81.2% | 57.5% |
| at_fire | all | label.next_240m.fully_filled | 1854 | 76.3% | 0.841 | 0.836 | 0.763 | 186 | 95.7% | 19.4% |
| at_fire | gap_down | label.next_240m.fully_filled | 822 | 80.9% | 0.836 | 0.841 | 0.809 | 83 | 96.4% | 15.5% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 822 | 19.1% | 0.836 | 0.841 | 0.809 | 83 | 66.3% | 47.2% |
| at_fire | all | label.next_60m.fully_filled | 1854 | 67.3% | 0.831 | 0.808 | 0.673 | 186 | 96.2% | 28.9% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 1854 | 32.7% | 0.831 | 0.808 | 0.673 | 186 | 89.2% | 56.6% |
| at_fire | gap_up | label.next_1d.fully_filled | 1032 | 86.5% | 0.817 | 0.865 | 0.865 | 104 | 97.1% | 10.6% |
| at_fire | gap_down | label.next_60m.fully_filled | 822 | 72.9% | 0.813 | 0.824 | 0.729 | 83 | 94.0% | 21.1% |
| at_fire | gap_down | label.next_60m.unfilled_at_window_end | 822 | 27.1% | 0.813 | 0.824 | 0.729 | 83 | 81.9% | 54.8% |
| at_fire | gap_down | label.next_1d.fully_filled | 822 | 94.8% | 0.725 | 0.948 | 0.948 | 83 | 97.6% | 2.8% |
| at_fire | all | label.next_240m.closed_outside_gap_range | 1854 | 87.9% | 0.722 | 0.880 | 0.879 | 186 | 98.4% | 10.5% |
| at_fire | all | label.next_240m.closed_inside_gap_range | 1854 | 12.1% | 0.722 | 0.880 | 0.879 | 186 | 28.5% | 16.4% |
| at_fire | gap_up | label.next_60m.took_gap_high_rejected_inside | 1032 | 19.2% | 0.683 | 0.808 | 0.808 | 104 | 31.7% | 12.5% |
| at_fire | gap_up | label.next_1d.closed_inside_gap_range | 1032 | 3.9% | 0.682 | 0.961 | 0.961 | 104 | 8.7% | 4.8% |
| at_fire | gap_down | label.next_60m.took_gap_low_rejected_inside | 822 | 18.1% | 0.676 | 0.819 | 0.819 | 83 | 30.1% | 12.0% |
| at_fire | gap_up | label.next_1d.swept_both_gap_closed_inside | 1032 | 3.3% | 0.672 | 0.967 | 0.967 | 104 | 9.6% | 6.3% |
| at_fire | all | label.next_1d.closed_inside_gap_range | 1854 | 4.2% | 0.669 | 0.958 | 0.958 | 186 | 11.3% | 7.1% |
| at_fire | all | label.next_60m.took_gap_low_rejected_inside | 1854 | 13.4% | 0.667 | 0.866 | 0.866 | 186 | 25.3% | 11.9% |
| at_fire | all | label.next_60m.took_gap_high_rejected_inside | 1854 | 15.5% | 0.644 | 0.845 | 0.845 | 186 | 31.2% | 15.6% |
| at_fire | gap_down | label.next_240m.closed_outside_gap_range | 822 | 90.6% | 0.625 | 0.909 | 0.906 | 83 | 98.8% | 8.2% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | ogap.ed.gap_size_pts=4249; xctx.minutes_since_last_fvg_side_bullish_24h=2895; xctx.minutes_since_last_swing_side_high_7d=1632; xctx.active_same_primary_concepts_1h=1117; ogap.ed.previous_close_price=1039; ts.month=696; xctx.n_disp_7d=663; xctx.minutes_since_last_sweep_same_primary_7d=621; xctx.minutes_since_last_swing_side_low_7d=561; xctx.n_psp_7d=509 |
| at_fire | gap_up | label.next_240m.fully_filled | ogap.ed.gap_size_pts=4249; xctx.minutes_since_last_fvg_side_bullish_24h=2895; xctx.minutes_since_last_swing_side_high_7d=1632; xctx.active_same_primary_concepts_1h=1117; ogap.ed.previous_close_price=1039; ts.month=696; xctx.n_disp_7d=663; xctx.minutes_since_last_sweep_same_primary_7d=621; xctx.minutes_since_last_swing_side_low_7d=561; xctx.n_psp_7d=509 |
| at_fire | all | label.next_1d.fully_filled | ogap.ed.gap_size_pts=5728; xctx.minutes_since_last_disp_24h=3517; xctx.minutes_since_last_tp_7d=2170; xctx.minutes_since_last_disp_7d=1035; xctx.minutes_since_last_tp_same_primary_7d=997; ogap.ed.previous_close_price=733; xd.has_swing_in_24h=718; xctx.n_vp_side_selling_7d=699; xctx.minutes_since_last_smt_side_low_7d=584; xctx.minutes_since_last_orb_side_bullish_7d=567 |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | ogap.ed.gap_size_pts=8622; ogap.ed.previous_close_price=1648; xctx.minutes_since_last_eql_24h=1346; xctx.minutes_since_last_swing_side_high_7d=870; xctx.minutes_since_last_itr_side_bullish_7d=840; xctx.minutes_since_last_psp_7d=777; xctx.minutes_since_last_eql_side_high_7d=600; ogap.ed.gap_mid=551; ogap.ed.current_open_price=547; xctx.minutes_since_last_eql_7d=381 |
| at_fire | gap_up | label.next_60m.fully_filled | ogap.ed.gap_size_pts=8622; ogap.ed.previous_close_price=1648; xctx.minutes_since_last_eql_24h=1346; xctx.minutes_since_last_swing_side_high_7d=870; xctx.minutes_since_last_itr_side_bullish_7d=840; xctx.minutes_since_last_psp_7d=777; xctx.minutes_since_last_eql_side_high_7d=600; ogap.ed.gap_mid=551; ogap.ed.current_open_price=547; xctx.minutes_since_last_eql_7d=381 |
| at_fire | all | label.next_240m.unfilled_at_window_end | ogap.ed.gap_size_pts=16788; ogap.ed.previous_close_price=2011; xctx.minutes_since_last_swing_side_high_24h=1967; xctx.minutes_since_last_swing_24h=1774; ogap.ed.current_open_price=1422; xctx.minutes_since_last_fvg_side_bullish_7d=1420; xctx.minutes_since_last_swing_7d=1073; xctx.minutes_since_last_disp_side_bearish_24h=925; xctx.minutes_since_last_sweep_7d=918; xctx.minutes_since_last_fvg_side_bullish_24h=746 |
| at_fire | all | label.next_240m.fully_filled | ogap.ed.gap_size_pts=16788; ogap.ed.previous_close_price=2011; xctx.minutes_since_last_swing_side_high_24h=1967; xctx.minutes_since_last_swing_24h=1774; ogap.ed.current_open_price=1422; xctx.minutes_since_last_fvg_side_bullish_7d=1420; xctx.minutes_since_last_swing_7d=1073; xctx.minutes_since_last_disp_side_bearish_24h=925; xctx.minutes_since_last_sweep_7d=918; xctx.minutes_since_last_fvg_side_bullish_24h=746 |
| at_fire | gap_down | label.next_240m.fully_filled | ogap.ed.gap_size_pts=10977; ogap.ed.previous_close_price=1487; xctx.minutes_since_last_swing_side_low_7d=1146; ogap.ed.current_open_price=846; xctx.minutes_since_last_eql_side_low_7d=723; xctx.minutes_since_last_macro_side_high_7d=672; xctx.minutes_since_last_swing_side_high_24h=586; xctx.n_eql_side_low_7d=469; xctx.minutes_since_last_smt_side_low_7d=422; xctx.minutes_since_last_sweep_7d=405 |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | ogap.ed.gap_size_pts=10977; ogap.ed.previous_close_price=1487; xctx.minutes_since_last_swing_side_low_7d=1146; ogap.ed.current_open_price=846; xctx.minutes_since_last_eql_side_low_7d=723; xctx.minutes_since_last_macro_side_high_7d=672; xctx.minutes_since_last_swing_side_high_24h=586; xctx.n_eql_side_low_7d=469; xctx.minutes_since_last_smt_side_low_7d=422; xctx.minutes_since_last_sweep_7d=405 |
| at_fire | all | label.next_60m.fully_filled | ogap.ed.gap_size_pts=24837; ogap.ed.gap_low=3447; ogap.ed.previous_close_price=2493; xctx.minutes_since_last_swing_side_high_24h=1522; ogap.ed.current_open_price=1263; ogap.ed.gap_high=675; xctx.minutes_since_last_disp_24h=670; xctx.minutes_since_last_smt_side_low_7d=657; xctx.minutes_since_last_eql_7d=587; xctx.n_eql_7d=526 |
| at_fire | all | label.next_60m.unfilled_at_window_end | ogap.ed.gap_size_pts=24837; ogap.ed.gap_low=3447; ogap.ed.previous_close_price=2493; xctx.minutes_since_last_swing_side_high_24h=1522; ogap.ed.current_open_price=1263; ogap.ed.gap_high=675; xctx.minutes_since_last_disp_24h=670; xctx.minutes_since_last_smt_side_low_7d=657; xctx.minutes_since_last_eql_7d=587; xctx.n_eql_7d=526 |
| at_fire | gap_up | label.next_1d.fully_filled | xctx.minutes_since_last_swing_side_high_7d=3623; xctx.n_disp_side_bullish_7d=742; xctx.minutes_since_last_orb_side_bullish_7d=649; xd.has_tp_in_24h=643; ogap.ed.gap_size_pts=610; ts.year=536; xctx.n_psp_7d=493; xctx.n_vp_side_selling_7d=424; xctx.n_eql_24h=382; xctx.minutes_since_last_vp_side_buying_7d=322 |
| at_fire | gap_down | label.next_60m.fully_filled | ogap.ed.gap_size_pts=12374; ogap.ed.previous_close_price=2245; ogap.ed.current_open_price=1485; ts.year=658; xctx.n_swing_side_high_24h=654; xctx.minutes_since_last_smt_side_low_7d=495; xctx.minutes_since_last_orb_side_doji_7d=493; xctx.minutes_since_last_eql_side_low_7d=470; xctx.n_sweep_side_high_7d=426; xctx.minutes_since_last_swing_side_high_24h=358 |
| at_fire | gap_down | label.next_60m.unfilled_at_window_end | ogap.ed.gap_size_pts=12374; ogap.ed.previous_close_price=2245; ogap.ed.current_open_price=1485; ts.year=658; xctx.n_swing_side_high_24h=654; xctx.minutes_since_last_smt_side_low_7d=495; xctx.minutes_since_last_orb_side_doji_7d=493; xctx.minutes_since_last_eql_side_low_7d=470; xctx.n_sweep_side_high_7d=426; xctx.minutes_since_last_swing_side_high_24h=358 |
| at_fire | gap_down | label.next_1d.fully_filled | ogap.ed.gap_size_pts=4509; xctx.minutes_since_last_swing_side_low_7d=780; xctx.minutes_since_last_eql_side_low_7d=731; xctx.minutes_since_last_fvg_same_primary_7d=614; xctx.minutes_since_last_disp_side_bearish_7d=323; xctx.minutes_since_last_ob_same_primary_7d=295; xctx.minutes_since_last_macro_side_high_7d=286; xctx.minutes_since_last_eql_side_low_24h=266; xctx.total_events_7d=261; xctx.minutes_since_last_orb_side_bullish_7d=257 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
