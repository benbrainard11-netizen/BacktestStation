# ML snapshot leaderboard

_Generated `2026-05-16T17:01:00.876205+00:00`._

## Setup

- Matrix: `data\ml\anchors\ob_snapshots_xctx_strict.parquet`
- Schema: `data\ml\anchors\ob_snapshots_xctx_strict.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `10` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\ob_snapshot_leaderboard_strict_context.csv | CSV leaderboard |
| data\ml\anchors\ob_snapshot_leaderboard_strict_context.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 46331 |
| schema_feature_columns | 650 |
| schema_label_columns | 236 |
| grid_attempts | 30 |
| trained_ok | 30 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | 4085 | 5.5% | 0.811 | 0.944 | 0.945 | 409 | 21.3% | 15.8% |
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | 8764 | 19.5% | 0.803 | 0.819 | 0.805 | 877 | 57.1% | 37.7% |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | 4679 | 20.6% | 0.803 | 0.812 | 0.794 | 468 | 59.8% | 39.2% |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | 4085 | 18.2% | 0.792 | 0.827 | 0.818 | 409 | 55.7% | 37.6% |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | 8764 | 5.4% | 0.790 | 0.944 | 0.946 | 877 | 18.7% | 13.3% |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | 4679 | 39.6% | 0.776 | 0.708 | 0.604 | 468 | 75.6% | 36.0% |
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | 8764 | 38.3% | 0.776 | 0.716 | 0.617 | 877 | 77.7% | 39.4% |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | 8764 | 31.9% | 0.771 | 0.729 | 0.681 | 877 | 66.5% | 34.6% |
| at_fire | bullish | label.strict.next_240m.ob_broken_through_continuation | 4085 | 36.7% | 0.770 | 0.714 | 0.633 | 409 | 77.0% | 40.3% |
| at_fire | all | label.strict.next_240m.ob_failed_immediately | 8764 | 32.1% | 0.770 | 0.723 | 0.679 | 877 | 65.8% | 33.7% |
| at_fire | bearish | label.strict.next_240m.ob_failed_immediately | 4679 | 33.3% | 0.767 | 0.717 | 0.667 | 468 | 69.2% | 36.0% |
| at_fire | bearish | label.strict.next_60m.ob_failed_immediately | 4679 | 33.0% | 0.767 | 0.715 | 0.670 | 468 | 65.0% | 31.9% |
| at_fire | bearish | label.strict.next_60m.ob_swept_and_recovered | 4679 | 5.3% | 0.763 | 0.946 | 0.947 | 468 | 15.0% | 9.7% |
| at_fire | bullish | label.strict.next_240m.ob_failed_immediately | 4085 | 30.8% | 0.762 | 0.718 | 0.692 | 409 | 62.6% | 31.8% |
| at_fire | bullish | label.strict.next_60m.ob_failed_immediately | 4085 | 30.6% | 0.762 | 0.715 | 0.694 | 409 | 65.5% | 35.0% |
| at_fire | all | label.strict.next_240m.ob_swept_and_recovered | 8764 | 14.6% | 0.742 | 0.854 | 0.854 | 877 | 34.2% | 19.6% |
| at_fire | bullish | label.strict.next_240m.ob_swept_and_recovered | 4085 | 14.1% | 0.742 | 0.856 | 0.859 | 409 | 35.2% | 21.1% |
| at_fire | bullish | label.strict.next_60m.ob_respected_deep_test | 4085 | 5.0% | 0.730 | 0.950 | 0.950 | 409 | 10.8% | 5.7% |
| at_fire | bearish | label.strict.next_240m.ob_swept_and_recovered | 4679 | 15.1% | 0.723 | 0.848 | 0.849 | 468 | 31.2% | 16.1% |
| at_fire | all | label.strict.next_60m.ob_respected_deep_test | 8764 | 5.6% | 0.698 | 0.944 | 0.944 | 877 | 10.3% | 4.7% |
| at_fire | bullish | label.strict.next_60m.ob_respected_partial_test | 4085 | 17.5% | 0.682 | 0.825 | 0.825 | 409 | 30.3% | 12.8% |
| at_fire | all | label.strict.next_60m.ob_respected_partial_test | 8764 | 17.5% | 0.657 | 0.824 | 0.825 | 877 | 31.4% | 13.8% |
| at_fire | bearish | label.strict.next_60m.ob_respected_deep_test | 4679 | 6.1% | 0.639 | 0.939 | 0.939 | 468 | 9.2% | 3.1% |
| at_fire | bullish | label.strict.next_240m.ob_respected_partial_test | 4085 | 19.0% | 0.633 | 0.809 | 0.810 | 409 | 34.7% | 15.7% |
| at_fire | all | label.strict.next_240m.ob_respected_partial_test | 8764 | 18.1% | 0.633 | 0.819 | 0.819 | 877 | 31.0% | 12.9% |
| at_fire | bearish | label.strict.next_60m.ob_respected_partial_test | 4679 | 17.6% | 0.620 | 0.824 | 0.824 | 468 | 27.6% | 10.0% |
| at_fire | all | label.strict.next_240m.ob_respected_deep_test | 8764 | 7.0% | 0.612 | 0.930 | 0.930 | 877 | 10.7% | 3.8% |
| at_fire | bullish | label.strict.next_240m.ob_respected_deep_test | 4085 | 7.1% | 0.608 | 0.929 | 0.929 | 409 | 11.2% | 4.2% |
| at_fire | bearish | label.strict.next_240m.ob_respected_partial_test | 4679 | 17.2% | 0.601 | 0.828 | 0.828 | 468 | 25.0% | 7.8% |
| at_fire | bearish | label.strict.next_240m.ob_respected_deep_test | 4679 | 6.9% | 0.598 | 0.931 | 0.931 | 468 | 8.3% | 1.5% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | ob.ed.ob_body_width_pts=7012; ob.ed.confirms_close_gt_ob_high=1759; xctx.n_eql_same_primary_7d=1396; ob.ed.swept_reference.level_price=1123; ob.ed.ob_range_width_pts=1030; xctx.n_vp_side_buying_7d=785; ob.ed.confirms_close_gt_ob_open=781; xctx.minutes_since_last_smt_side_high_7d=776; xctx.minutes_since_last_vp_side_buying_24h=730; ob.ed.bars_to_confirm=721 |
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | ob.ed.ob_body_width_pts=27675; ob.ed.confirms_close_gt_ob_high=12944; ob.ed.tracking_timeframe_1h=5395; ob.ed.confirms_close_gt_ob_open=4809; xctx.n_eql_same_primary_7d=3388; xctx.n_fvg_same_primary_7d=3042; ob.ed.manipulation_candle.close=2903; xctx.minutes_since_last_tp_24h=2816; ob.ed.ob_range_width_pts=2483; ob.ed.bars_to_confirm=2366 |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | ob.ed.ob_body_width_pts=18008; ob.ed.confirms_close_gt_ob_high=6330; ob.ed.tracking_timeframe_1h=3431; ob.ed.confirms_close_gt_ob_open=2631; xctx.n_eql_same_primary_7d=2308; ob.ed.bars_to_confirm=2069; xctx.n_fvg_same_primary_7d=1698; ob.ed.ob_body_mid=1666; ob.ed.manipulation_candle.open=1538; xctx.minutes_since_last_tp_24h=1512 |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | ob.ed.ob_body_width_pts=13309; ob.ed.confirms_close_gt_ob_high=4814; ob.ed.swept_reference.level_price=2814; ob.ed.confirms_close_gt_ob_open=2449; ob.ed.tracking_timeframe_1h=2302; xctx.minutes_since_last_disp_side_bullish_24h=1420; xctx.n_eql_same_primary_7d=1411; xctx.n_fvg_same_primary_7d=1103; xctx.minutes_since_last_orb_24h=1005; xctx.minutes_since_last_orb_side_bullish_24h=976 |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | ob.ed.ob_body_width_pts=12470; ob.ed.confirms_close_gt_ob_high=4389; xctx.n_eql_same_primary_7d=2355; ob.ed.ob_range_width_pts=1800; ob.ed.swept_reference.level_price=1621; ob.ed.bars_to_confirm=1578; xctx.minutes_since_last_smt_side_high_7d=1431; xctx.minutes_since_last_psp_side_bullish_24h=1373; ob.ed.confirms_close_gt_ob_open=1371; xctx.n_eql_side_low_7d=1278 |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | ob.ed.ob_body_width_pts=17502; ob.ed.confirms_close_gt_ob_high=7202; ob.ed.tracking_timeframe_1h=5162; xctx.minutes_since_last_orb_24h=4288; ts.hour_of_day_utc=2678; ob.ed.bars_back_to_ob=2307; xctx.n_eql_same_primary_7d=2232; ob.ed.confirms_close_gt_ob_open=2074; ob.ctx.hour_of_day_et=1979; xctx.minutes_since_last_tp_24h=1546 |
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | ob.ed.ob_body_width_pts=31825; ob.ed.confirms_close_gt_ob_high=12036; xctx.minutes_since_last_orb_24h=9227; ob.ed.tracking_timeframe_1h=8336; ob.ed.confirms_close_gt_ob_open=5163; ob.ed.bars_back_to_ob=4762; ts.hour_of_day_utc=4628; xctx.n_eql_same_primary_7d=3283; ob.ctx.hour_of_day_et=3084; xctx.minutes_since_last_tp_24h=2917 |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | ob.ed.confirms_close_gt_ob_high=44148; ob.ed.ob_body_width_pts=12190; ob.ed.confirms_close_gt_ob_open=10051; ob.ed.tracking_timeframe_1h=6199; ob.ed.bars_to_confirm=4435; ob.ed.bars_back_to_ob=3699; xctx.minutes_since_last_tp_24h=2168; xctx.minutes_since_last_disp_same_primary_24h=1763; xctx.minutes_since_last_vp_24h=1480; xctx.n_eql_same_primary_7d=1477 |
| at_fire | bullish | label.strict.next_240m.ob_broken_through_continuation | ob.ed.ob_body_width_pts=14153; xctx.minutes_since_last_orb_24h=4802; ob.ed.confirms_close_gt_ob_high=4090; ob.ed.tracking_timeframe_1h=4008; ob.ed.confirms_close_gt_ob_open=2732; ob.ed.bars_back_to_ob=2155; xctx.minutes_since_last_smt_side_high_7d=2013; ob.ed.ob_candle.low=1758; xctx.n_psp_side_bullish_7d=1582; ts.hour_of_day_utc=1397 |
| at_fire | all | label.strict.next_240m.ob_failed_immediately | ob.ed.confirms_close_gt_ob_high=44411; ob.ed.ob_body_width_pts=12070; ob.ed.confirms_close_gt_ob_open=10190; ob.ed.tracking_timeframe_1h=6679; ob.ed.bars_to_confirm=4372; ob.ed.bars_back_to_ob=3822; xctx.minutes_since_last_disp_same_primary_24h=1874; xctx.minutes_since_last_tp_24h=1686; xctx.n_eql_same_primary_7d=1467; xctx.minutes_since_last_smt_side_high_7d=1372 |
| at_fire | bearish | label.strict.next_240m.ob_failed_immediately | ob.ed.confirms_close_gt_ob_high=24204; ob.ed.confirms_close_gt_ob_open=8348; ob.ed.ob_body_width_pts=5207; ob.ed.bars_to_confirm=3407; ob.ed.tracking_timeframe_1h=3072; ob.ed.bars_back_to_ob=1521; xctx.minutes_since_last_fvg_side_bullish_24h=1171; xctx.minutes_since_last_smt_side_high_7d=882; xctx.n_eql_same_primary_7d=882; xctx.n_disp_side_bullish_24h=863 |
| at_fire | bearish | label.strict.next_60m.ob_failed_immediately | ob.ed.confirms_close_gt_ob_high=24036; ob.ed.confirms_close_gt_ob_open=8457; ob.ed.ob_body_width_pts=5821; ob.ed.bars_to_confirm=3531; ob.ed.tracking_timeframe_1h=2812; ob.ed.bars_back_to_ob=1590; xctx.minutes_since_last_ft_side_bearish_7d=1148; xctx.minutes_since_last_smt_side_high_7d=1119; xctx.n_eql_same_primary_7d=1105; xctx.minutes_since_last_fvg_side_bullish_24h=1089 |
| at_fire | bearish | label.strict.next_60m.ob_swept_and_recovered | ob.ed.ob_body_width_pts=6456; ob.ed.confirms_close_gt_ob_high=2469; ob.ed.bars_to_confirm=1503; xctx.n_eql_same_primary_7d=1349; xctx.minutes_since_last_smt_side_high_7d=980; xctx.minutes_since_last_psp_side_bullish_24h=954; xctx.n_fvg_same_primary_7d=888; xctx.n_swing_side_high_7d=846; xctx.total_events_4h=832; xctx.n_fvg_side_bearish_7d=787 |
| at_fire | bullish | label.strict.next_240m.ob_failed_immediately | ob.ed.confirms_close_gt_ob_high=11542; ob.ed.confirms_close_gt_ob_open=10491; ob.ed.ob_body_width_pts=5479; ob.ed.tracking_timeframe_1h=3750; ob.ed.bars_to_confirm=2021; ob.ed.bars_back_to_ob=1747; xctx.n_fvg_side_bullish_4h=1538; xctx.minutes_since_last_disp_side_bullish_24h=1511; xctx.n_fvg_side_bullish_24h=1471; xctx.minutes_since_last_orb_side_bullish_24h=1404 |
| at_fire | bullish | label.strict.next_60m.ob_failed_immediately | ob.ed.confirms_close_gt_ob_high=11626; ob.ed.confirms_close_gt_ob_open=10206; ob.ed.ob_body_width_pts=5043; ob.ed.tracking_timeframe_1h=3520; ob.ed.bars_to_confirm=1817; ob.ed.bars_back_to_ob=1487; xctx.n_fvg_side_bullish_4h=1382; xctx.n_swing_side_high_7d=1334; xctx.minutes_since_last_orb_side_bearish_24h=1273; xctx.minutes_since_last_fvg_side_bearish_1h=1113 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
