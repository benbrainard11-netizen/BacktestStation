# ML snapshot leaderboard

_Generated `2026-05-16T01:07:39.295848+00:00`._

## Setup

- Matrix: `data\ml\anchors\swing_snapshots_strict.parquet`
- Schema: `data\ml\anchors\swing_snapshots_strict.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `high, low, all`
- Labels searched: `10` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\swing_snapshot_leaderboard_strict_context.csv | CSV leaderboard |
| data\ml\anchors\swing_snapshot_leaderboard_strict_context.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 76786 |
| schema_feature_columns | 37 |
| schema_label_columns | 39 |
| grid_attempts | 30 |
| trained_ok | 30 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | 14747 | 5.2% | 0.805 | 0.948 | 0.948 | 1475 | 18.9% | 13.7% |
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | 14747 | 18.1% | 0.804 | 0.822 | 0.819 | 1475 | 47.7% | 29.6% |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | 7337 | 17.7% | 0.803 | 0.822 | 0.823 | 734 | 46.6% | 28.9% |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | 7410 | 18.5% | 0.799 | 0.813 | 0.815 | 741 | 47.2% | 28.7% |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | 7410 | 5.4% | 0.799 | 0.946 | 0.946 | 741 | 18.1% | 12.7% |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | 7337 | 5.1% | 0.789 | 0.949 | 0.949 | 734 | 17.7% | 12.6% |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | 7337 | 5.8% | 0.772 | 0.941 | 0.942 | 734 | 17.2% | 11.3% |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | 14747 | 6.2% | 0.771 | 0.938 | 0.938 | 1475 | 19.2% | 13.0% |
| at_fire | all | label.strict.next_240m.pivot_failed_immediately | 14747 | 6.3% | 0.769 | 0.937 | 0.937 | 1475 | 18.2% | 11.9% |
| at_fire | low | label.strict.next_240m.pivot_failed_immediately | 7337 | 6.0% | 0.765 | 0.938 | 0.940 | 734 | 18.8% | 12.8% |
| at_fire | high | label.strict.next_60m.pivot_failed_immediately | 7410 | 6.6% | 0.760 | 0.934 | 0.934 | 741 | 16.3% | 9.7% |
| at_fire | high | label.strict.next_240m.pivot_failed_immediately | 7410 | 6.7% | 0.753 | 0.933 | 0.933 | 741 | 16.9% | 10.2% |
| at_fire | all | label.strict.next_240m.pivot_partial_test_rejected | 14747 | 20.7% | 0.664 | 0.792 | 0.793 | 1475 | 38.6% | 17.8% |
| at_fire | all | label.strict.next_60m.pivot_partial_test_rejected | 14747 | 20.2% | 0.664 | 0.798 | 0.798 | 1475 | 40.5% | 20.3% |
| at_fire | all | label.strict.next_60m.pivot_held_rejection | 14747 | 21.2% | 0.663 | 0.788 | 0.788 | 1475 | 41.6% | 20.4% |
| at_fire | high | label.strict.next_60m.pivot_partial_test_rejected | 7410 | 23.2% | 0.660 | 0.768 | 0.768 | 741 | 45.2% | 22.0% |
| at_fire | low | label.strict.next_60m.pivot_double_test_held | 7337 | 9.4% | 0.660 | 0.906 | 0.906 | 734 | 17.3% | 7.9% |
| at_fire | all | label.strict.next_60m.pivot_double_test_held | 14747 | 10.2% | 0.660 | 0.898 | 0.898 | 1475 | 17.8% | 7.7% |
| at_fire | high | label.strict.next_60m.pivot_held_rejection | 7410 | 24.2% | 0.655 | 0.757 | 0.758 | 741 | 45.9% | 21.6% |
| at_fire | all | label.strict.next_240m.pivot_held_rejection | 14747 | 22.4% | 0.654 | 0.775 | 0.776 | 1475 | 40.7% | 18.3% |
| at_fire | all | label.strict.next_240m.pivot_double_test_held | 14747 | 15.6% | 0.651 | 0.844 | 0.844 | 1475 | 28.0% | 12.4% |
| at_fire | high | label.strict.next_60m.pivot_double_test_held | 7410 | 11.0% | 0.648 | 0.890 | 0.890 | 741 | 15.0% | 4.0% |
| at_fire | high | label.strict.next_240m.pivot_partial_test_rejected | 7410 | 22.7% | 0.645 | 0.772 | 0.773 | 741 | 40.6% | 17.9% |
| at_fire | high | label.strict.next_240m.pivot_held_rejection | 7410 | 24.4% | 0.643 | 0.756 | 0.756 | 741 | 42.2% | 17.9% |
| at_fire | high | label.strict.next_240m.pivot_double_test_held | 7410 | 16.6% | 0.639 | 0.834 | 0.834 | 741 | 27.0% | 10.4% |
| at_fire | low | label.strict.next_60m.pivot_partial_test_rejected | 7337 | 17.2% | 0.638 | 0.828 | 0.828 | 734 | 30.5% | 13.4% |
| at_fire | low | label.strict.next_240m.pivot_partial_test_rejected | 7337 | 18.7% | 0.635 | 0.810 | 0.813 | 734 | 30.8% | 12.1% |
| at_fire | low | label.strict.next_60m.pivot_held_rejection | 7337 | 18.2% | 0.633 | 0.818 | 0.818 | 734 | 31.7% | 13.6% |
| at_fire | low | label.strict.next_240m.pivot_double_test_held | 7337 | 14.5% | 0.628 | 0.855 | 0.855 | 734 | 24.4% | 9.8% |
| at_fire | low | label.strict.next_240m.pivot_held_rejection | 7337 | 20.3% | 0.626 | 0.794 | 0.797 | 734 | 33.1% | 12.8% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | swing.hour_of_day_utc=15965; ts.hour_of_day_utc=15111; swing.ctx.hour_of_day_et=10301; swing.ed.tracking_timeframe_1h=5006; ts.month=3883; ts.year=2675; ts.day_of_week=2472; swing.ed.pivot_price=1964; swing.event_type_pivot_3_1h=1805; swing.ed.n=1354 |
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | swing.hour_of_day_utc=52371; swing.ed.tracking_timeframe_1h=28235; ts.hour_of_day_utc=16705; swing.ctx.hour_of_day_et=16638; ts.day_of_week=9528; ts.month=5722; ts.year=4590; swing.ctx.tracking_timeframe_1h=4222; swing.event_type_pivot_3_1h=4192; swing.ed.pivot_price=3095 |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | swing.hour_of_day_utc=35123; swing.ed.tracking_timeframe_1h=13123; ts.hour_of_day_utc=6900; swing.ctx.hour_of_day_et=6589; ts.day_of_week=4496; ts.month=3737; ts.year=3650; swing.day_of_week=2360; swing.ed.pivot_price=2236; swing.event_type_pivot_3_1h=2045 |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | swing.hour_of_day_utc=29041; swing.ed.tracking_timeframe_1h=16376; ts.hour_of_day_utc=9327; ts.day_of_week=6621; ts.month=5743; swing.ctx.hour_of_day_et=5712; ts.year=4250; swing.ed.pivot_price=3668; swing.ed.pivot_bar.open=2334; swing.month=2120 |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | ts.hour_of_day_utc=9257; swing.hour_of_day_utc=8238; swing.ctx.hour_of_day_et=4026; ts.month=3398; ts.year=2962; swing.ed.tracking_timeframe_1h=2194; ts.day_of_week=1937; swing.ed.pivot_price=1731; swing.event_type_pivot_3_1h=1049; swing.month=1040 |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | swing.hour_of_day_utc=9515; ts.hour_of_day_utc=5577; swing.ctx.hour_of_day_et=4172; swing.ed.tracking_timeframe_1h=2917; ts.month=1987; ts.year=1628; ts.day_of_week=1313; swing.ed.pivot_price=1114; swing.ed.n=1048; swing.event_type_pivot_3_1h=919 |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | swing.hour_of_day_utc=9725; ts.hour_of_day_utc=6768; swing.ctx.hour_of_day_et=3328; swing.ed.tracking_timeframe_1h=2897; ts.month=2655; ts.year=1692; ts.day_of_week=1643; swing.ed.pivot_price=1498; swing.day_of_week=685; swing.event_type_pivot_3_1h=675 |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | ts.hour_of_day_utc=17615; swing.hour_of_day_utc=14635; swing.ctx.hour_of_day_et=7121; swing.ed.tracking_timeframe_1h=5017; ts.month=4617; ts.day_of_week=3313; ts.year=2707; swing.event_type_pivot_3_1h=2121; swing.ed.pivot_price=1791; swing.ed.pivot_bar.open=1224 |
| at_fire | all | label.strict.next_240m.pivot_failed_immediately | ts.hour_of_day_utc=17103; swing.hour_of_day_utc=14392; swing.ctx.hour_of_day_et=8016; swing.ed.tracking_timeframe_1h=5070; ts.month=5006; ts.day_of_week=3765; ts.year=3363; swing.ed.pivot_price=2611; swing.event_type_pivot_3_1h=1904; swing.ed.pivot_bar.open=1598 |
| at_fire | low | label.strict.next_240m.pivot_failed_immediately | swing.hour_of_day_utc=9887; ts.hour_of_day_utc=6822; swing.ctx.hour_of_day_et=3505; ts.month=3313; swing.ed.tracking_timeframe_1h=2684; ts.day_of_week=2280; ts.year=2142; swing.ed.pivot_price=2007; swing.ed.pivot_bar.open=955; swing.month=852 |
| at_fire | high | label.strict.next_60m.pivot_failed_immediately | ts.hour_of_day_utc=9800; swing.hour_of_day_utc=6981; swing.ctx.hour_of_day_et=3790; ts.month=2831; swing.ed.tracking_timeframe_1h=2278; ts.day_of_week=1848; swing.ed.pivot_price=1700; ts.year=1616; swing.event_type_pivot_3_1h=1226; swing.ed.pivot_bar.open=996 |
| at_fire | high | label.strict.next_240m.pivot_failed_immediately | ts.hour_of_day_utc=9155; swing.hour_of_day_utc=6840; swing.ctx.hour_of_day_et=3561; ts.month=2755; swing.ed.tracking_timeframe_1h=1984; ts.day_of_week=1898; ts.year=1775; swing.ed.pivot_price=1403; swing.event_type_pivot_3_1h=1077; swing.ed.pivot_bar.open=899 |
| at_fire | all | label.strict.next_240m.pivot_partial_test_rejected | ts.day_of_week=21226; swing.hour_of_day_utc=10586; ts.hour_of_day_utc=10121; swing.ctx.hour_of_day_et=8873; ts.month=4516; swing.day_of_week=3867; ts.year=3581; swing.ed.pivot_price=2817; swing.side_high=2257; swing.ed.pivot_bar.open=2233 |
| at_fire | all | label.strict.next_60m.pivot_partial_test_rejected | ts.day_of_week=22634; ts.hour_of_day_utc=11291; swing.ctx.hour_of_day_et=10061; swing.hour_of_day_utc=8573; ts.month=4443; swing.ed.pivot_price=3446; ts.year=3415; swing.side_high=3239; swing.ed.n=2987; swing.day_of_week=2777 |
| at_fire | all | label.strict.next_60m.pivot_held_rejection | ts.day_of_week=22974; swing.ctx.hour_of_day_et=11990; ts.hour_of_day_utc=9825; swing.hour_of_day_utc=5024; swing.day_of_week=3219; swing.side_high=3127; ts.month=3014; ts.year=2726; swing.ed.tracking_timeframe_1h=2704; swing.event_type_pivot_3_1h=2519 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
