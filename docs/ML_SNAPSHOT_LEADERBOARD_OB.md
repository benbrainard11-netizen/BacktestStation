# ML snapshot leaderboard

_Generated `2026-05-11T23:26:04.067644+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshots.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `13` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 46331 |
| schema_feature_columns | 58 |
| schema_label_columns | 226 |
| grid_attempts | 39 |
| trained_ok | 39 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.level_tags.open.wick_tapped | 8764 | 95.3% | 0.872 | 0.953 | 0.953 | 877 | 100.0% | 4.7% |
| at_fire | bearish | label.level_tags.open.wick_tapped | 4679 | 96.2% | 0.868 | 0.958 | 0.962 | 468 | 100.0% | 3.8% |
| at_fire | bullish | label.level_tags.open.wick_tapped | 4085 | 94.2% | 0.858 | 0.941 | 0.942 | 409 | 100.0% | 5.8% |
| at_fire | bearish | label.level_tags.q25.wick_tapped | 4679 | 95.6% | 0.858 | 0.956 | 0.956 | 468 | 99.8% | 4.2% |
| at_fire | all | label.level_tags.q25.wick_tapped | 8764 | 94.5% | 0.850 | 0.945 | 0.945 | 877 | 99.4% | 5.0% |
| at_fire | bearish | label.level_tags.q50.wick_tapped | 4679 | 94.9% | 0.841 | 0.947 | 0.949 | 468 | 100.0% | 5.1% |
| at_fire | bullish | label.level_tags.q25.wick_tapped | 4085 | 93.2% | 0.830 | 0.932 | 0.932 | 409 | 99.5% | 6.3% |
| at_fire | all | label.level_tags.q50.wick_tapped | 8764 | 93.3% | 0.817 | 0.934 | 0.933 | 877 | 99.9% | 6.5% |
| at_fire | bearish | label.level_tags.q75.wick_tapped | 4679 | 94.0% | 0.808 | 0.939 | 0.940 | 468 | 99.8% | 5.8% |
| at_fire | bullish | label.level_tags.q50.wick_tapped | 4085 | 91.6% | 0.791 | 0.916 | 0.916 | 409 | 99.0% | 7.4% |
| at_fire | all | label.level_tags.q75.wick_tapped | 8764 | 91.9% | 0.780 | 0.919 | 0.919 | 877 | 99.7% | 7.8% |
| at_fire | bearish | label.level_tags.open.close_past | 4679 | 91.9% | 0.775 | 0.919 | 0.919 | 468 | 98.9% | 7.0% |
| at_fire | bearish | label.level_tags.q25.close_past | 4679 | 91.0% | 0.768 | 0.910 | 0.910 | 468 | 97.6% | 6.6% |
| at_fire | all | label.level_tags.open.close_past | 8764 | 89.6% | 0.761 | 0.896 | 0.896 | 877 | 98.7% | 9.2% |
| at_fire | bullish | label.level_tags.q75.wick_tapped | 4085 | 89.4% | 0.751 | 0.894 | 0.894 | 409 | 98.5% | 9.1% |
| at_fire | bearish | label.level_tags.close.wick_tapped | 4679 | 92.0% | 0.742 | 0.920 | 0.920 | 468 | 99.4% | 7.4% |
| at_fire | bearish | label.level_tags.q50.close_past | 4679 | 89.8% | 0.739 | 0.898 | 0.898 | 468 | 96.8% | 6.9% |
| at_fire | bullish | label.level_tags.open.close_past | 4085 | 86.9% | 0.739 | 0.869 | 0.869 | 409 | 98.5% | 11.7% |
| at_fire | all | label.level_tags.q25.close_past | 8764 | 88.2% | 0.734 | 0.883 | 0.882 | 877 | 97.5% | 9.3% |
| at_fire | all | label.level_tags.close.wick_tapped | 8764 | 89.2% | 0.731 | 0.894 | 0.892 | 877 | 99.3% | 10.1% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.level_tags.open.wick_tapped | ob.ed.confirms_close_gt_ob_high=24414; ob.ed.confirms_close_gt_ob_open=18632; ob.ed.ob_range_width_pts=4050; ts.month=3075; ob.ed.ob_body_width_pts=2987; ts.hour_of_day_utc=2878; ts.year=2424; ob.ed.bars_back_to_ob=2215; ob.ed.swept_reference.level_price=1784; ts.day_of_week=1683 |
| at_fire | bearish | label.level_tags.open.wick_tapped | ob.ed.confirms_close_gt_ob_high=13903; ob.ed.confirms_close_gt_ob_open=4834; ts.month=2201; ob.ed.ob_body_width_pts=1771; ts.year=1732; ob.ed.ob_range_width_pts=1704; ts.hour_of_day_utc=1475; ts.day_of_week=1306; ob.ed.bars_back_to_ob=1066; ob.ed.bars_to_confirm=967 |
| at_fire | bullish | label.level_tags.open.wick_tapped | ob.ed.confirms_close_gt_ob_high=12038; ob.ed.confirms_close_gt_ob_open=11638; ob.ed.ob_range_width_pts=3586; ob.ed.ob_body_width_pts=2859; ts.month=2364; ob.ed.swept_reference.level_price=2110; ts.year=2088; ob.hour_of_day_utc=1689; ts.hour_of_day_utc=1484; ob.ctx.hour_of_day_et=1392 |
| at_fire | bearish | label.level_tags.q25.wick_tapped | ob.ed.confirms_close_gt_ob_high=12840; ob.ed.confirms_close_gt_ob_open=5415; ts.month=1916; ts.hour_of_day_utc=1785; ts.year=1733; ob.ed.ob_body_width_pts=1598; ob.ed.ob_range_width_pts=1399; ts.day_of_week=1297; ob.ed.bars_back_to_ob=900; ob.ed.swept_reference.level_price=798 |
| at_fire | all | label.level_tags.q25.wick_tapped | ob.ed.confirms_close_gt_ob_open=23827; ob.ed.confirms_close_gt_ob_high=19376; ts.hour_of_day_utc=3329; ob.ed.ob_range_width_pts=3119; ts.month=2887; ts.year=2738; ob.ed.ob_body_width_pts=2726; ob.ed.bars_back_to_ob=2441; ts.day_of_week=2081; ob.ed.swept_reference.level_price=1758 |
| at_fire | bearish | label.level_tags.q50.wick_tapped | ob.ed.confirms_close_gt_ob_high=12339; ob.ed.confirms_close_gt_ob_open=3918; ts.month=2545; ts.hour_of_day_utc=2227; ts.year=1655; ob.ed.ob_body_width_pts=1570; ob.ed.ob_range_width_pts=1426; ts.day_of_week=1397; ob.hour_of_day_utc=1009; ob.ed.bars_back_to_ob=963 |
| at_fire | bullish | label.level_tags.q25.wick_tapped | ob.ed.confirms_close_gt_ob_open=17170; ob.ed.confirms_close_gt_ob_high=7112; ob.ed.ob_range_width_pts=3627; ob.ed.ob_body_width_pts=3122; ts.year=2551; ts.month=2522; ob.ed.swept_reference.level_price=2262; ts.hour_of_day_utc=2024; ob.ed.bars_back_to_ob=1767; ts.day_of_week=1761 |
| at_fire | all | label.level_tags.q50.wick_tapped | ob.ed.confirms_close_gt_ob_high=19192; ob.ed.confirms_close_gt_ob_open=17591; ob.ed.ob_body_width_pts=4639; ts.hour_of_day_utc=4566; ts.month=3683; ob.ed.ob_range_width_pts=3591; ts.year=3178; ob.ed.bars_back_to_ob=2958; ts.day_of_week=2591; ob.ed.swept_reference.level_price=2109 |
| at_fire | bearish | label.level_tags.q75.wick_tapped | ob.ed.confirms_close_gt_ob_high=10906; ob.ed.ob_body_width_pts=2819; ts.month=2541; ob.ed.confirms_close_gt_ob_open=2230; ts.year=2218; ob.ed.ob_range_width_pts=2143; ts.hour_of_day_utc=2023; ob.ctx.hour_of_day_et=1614; ts.day_of_week=1477; ob.ed.bars_back_to_ob=1355 |
| at_fire | bullish | label.level_tags.q50.wick_tapped | ob.ed.confirms_close_gt_ob_open=14091; ob.ed.confirms_close_gt_ob_high=6320; ob.ed.ob_body_width_pts=3883; ob.ed.ob_range_width_pts=3321; ts.hour_of_day_utc=2789; ts.month=2326; ob.ed.swept_reference.level_price=2215; ts.year=2163; ob.ed.bars_back_to_ob=1987; ob.hour_of_day_utc=1588 |
| at_fire | all | label.level_tags.q75.wick_tapped | ob.ed.confirms_close_gt_ob_high=18851; ob.ed.confirms_close_gt_ob_open=8820; ts.hour_of_day_utc=3896; ob.ed.ob_body_width_pts=3809; ts.year=2815; ob.ed.ob_range_width_pts=2540; ts.day_of_week=2490; ob.ed.bars_back_to_ob=2474; ts.month=2163; ob.side_bearish=1669 |
| at_fire | bearish | label.level_tags.open.close_past | ob.ed.confirms_close_gt_ob_high=9237; ob.ed.confirms_close_gt_ob_open=3501; ts.month=1681; ts.hour_of_day_utc=1536; ob.ed.ob_range_width_pts=1429; ts.day_of_week=1386; ts.year=1071; ob.ed.bars_to_confirm=989; ob.ed.ob_body_width_pts=964; ob.ctx.hour_of_day_et=912 |
| at_fire | bearish | label.level_tags.q25.close_past | ob.ed.confirms_close_gt_ob_high=10168; ob.ed.confirms_close_gt_ob_open=1784; ob.ed.ob_range_width_pts=1649; ts.month=1586; ts.day_of_week=1486; ts.year=1484; ts.hour_of_day_utc=1432; ob.ctx.hour_of_day_et=1099; ob.ed.bars_to_confirm=1057; ob.ed.ob_body_width_pts=1013 |
| at_fire | all | label.level_tags.open.close_past | ob.ed.confirms_close_gt_ob_open=19138; ob.ed.confirms_close_gt_ob_high=12632; ob.ed.ob_body_width_pts=4168; ts.month=3803; ts.year=3638; ob.ed.ob_range_width_pts=3627; ts.hour_of_day_utc=3229; ts.day_of_week=2431; ob.ctx.hour_of_day_et=2316; ob.ctx.day_of_week_et=2051 |
| at_fire | bullish | label.level_tags.q75.wick_tapped | ob.ed.confirms_close_gt_ob_open=8483; ob.ed.confirms_close_gt_ob_high=6904; ob.ed.ob_body_width_pts=3178; ts.year=2509; ts.hour_of_day_utc=2395; ob.ed.ob_range_width_pts=2256; ob.ed.swept_reference.level_price=1947; ts.month=1938; ob.ed.bars_back_to_ob=1654; ob.ctx.hour_of_day_et=1435 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
