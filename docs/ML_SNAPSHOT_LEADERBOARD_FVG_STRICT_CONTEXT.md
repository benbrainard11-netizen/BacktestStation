# ML snapshot leaderboard

_Generated `2026-05-15T16:59:08.695884+00:00`._

## Setup

- Matrix: `data\ml\anchors\fvg_snapshots_xctx_fvggeom_obgeom_strict.parquet`
- Schema: `data\ml\anchors\fvg_snapshots_xctx_fvggeom_obgeom_strict.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `all`
- Labels searched: `4` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\fvg_snapshot_leaderboard_strict_context.csv | CSV leaderboard |
| data\ml\anchors\fvg_snapshot_leaderboard_strict_context.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 1969 |
| schema_label_columns | 133 |
| grid_attempts | 4 |
| trained_ok | 4 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.no_touch_continuation | 41590 | 5.0% | 0.717 | 0.950 | 0.950 | 4159 | 13.2% | 8.2% |
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | 41590 | 12.4% | 0.714 | 0.876 | 0.876 | 4159 | 25.3% | 12.9% |
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | 41590 | 7.3% | 0.693 | 0.927 | 0.927 | 4159 | 15.5% | 8.2% |
| at_fire | all | label.strict.tap_wick_rejected | 41590 | 44.8% | 0.530 | 0.552 | 0.552 | 4159 | 48.3% | 3.5% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.strict.no_touch_continuation | fvg.ed.fvg_width_pts=21763; xctx.minutes_since_last_ogap_7d=15222; xctx.minutes_since_last_tp_7d=2911; xctx.minutes_since_last_ogap_24h=2745; xctx.n_eql_same_primary_7d=2140; xctx.n_disp_side_bearish_24h=1537; fvg.event_type_15m_fvg=1530; xctx.minutes_since_last_ob_side_bullish_24h=1419; xctx.minutes_since_last_vp_side_balanced_24h=1406; xctx.n_disp_side_bullish_7d=1388 |
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | fvg.ed.fvg_width_pts=82038; fvg.event_type_15m_fvg=7697; fvg.ed.candle_1.high=4046; fvg.ed.candle_2.open=3925; xctx.minutes_since_last_ogap_24h=3419; fvg.ctx.hour_of_day_et=2696; obgeom.n_same_primary_bearish_invalidated_within_100pts=2498; fvg.ed.candle_3.high=2251; fvg.ed.fvg_high=2238; fvg.ed.candle_3.open=2145 |
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | fvg.ed.fvg_width_pts=36278; fvg.event_type_15m_fvg=6167; fvg.ctx.hour_of_day_et=2103; xctx.n_eql_same_primary_7d=1945; xctx.minutes_since_last_ogap_24h=1845; ts.year=1788; xctx.minutes_since_last_orb_24h=1680; fvg.ed.fvg_mid=1663; fvg.ed.candle_3.high=1370; xctx.minutes_since_last_ogap_side_gap_down_24h=1341 |
| at_fire | all | label.strict.tap_wick_rejected | xctx.minutes_since_last_ogap_7d=4295; xctx.minutes_since_last_ogap_24h=2386; fvg.day_of_week=1257; fvg.event_type_15m_fvg=716; xctx.minutes_since_last_psp_side_bearish_7d=528; xctx.minutes_since_last_vp_side_balanced_24h=525; xctx.minutes_since_last_sweep_24h=357; xctx.minutes_since_last_psp_24h=354; ts.day_of_week=350; xctx.minutes_since_last_smt_side_high_7d=340 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
