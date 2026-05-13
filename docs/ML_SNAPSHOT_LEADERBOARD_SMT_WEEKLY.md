# ML snapshot leaderboard

_Generated `2026-05-11T20:37:11.175551+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_weekly_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_weekly_snapshots.schema.json`
- Event type: `weekly_smt`
- Snapshots: `at_fire, at_period_close`
- Sides: `low, high, all`
- Labels searched: `10` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_weekly_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_weekly_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 1060 |
| schema_feature_columns | 281 |
| schema_label_columns | 18 |
| grid_attempts | 60 |
| trained_ok | 40 |
| skipped | 20 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | all | label.n1_thesis_confirmed_strict | 107 | 46.7% | 0.861 | 0.794 | 0.533 | 11 | 81.8% | 35.1% |
| at_period_close | high | label.n1_primary_took_period_n_high | 66 | 60.6% | 0.855 | 0.758 | 0.606 | 7 | 100.0% | 39.4% |
| at_period_close | all | label.n1_primary_took_period_n_high | 107 | 57.9% | 0.843 | 0.738 | 0.579 | 11 | 100.0% | 42.1% |
| at_period_close | all | label.n1_primary_took_period_n_low | 107 | 40.2% | 0.834 | 0.738 | 0.598 | 11 | 81.8% | 41.6% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 66 | 42.4% | 0.820 | 0.758 | 0.576 | 7 | 71.4% | 29.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 66 | 42.4% | 0.820 | 0.758 | 0.576 | 7 | 71.4% | 29.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 107 | 56.1% | 0.772 | 0.682 | 0.561 | 11 | 90.9% | 34.8% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 66 | 53.0% | 0.763 | 0.682 | 0.530 | 7 | 85.7% | 32.7% |
| at_period_close | all | label.n1_close_moved_with_thesis | 107 | 49.5% | 0.746 | 0.664 | 0.495 | 11 | 81.8% | 32.3% |
| at_period_close | all | label.n2_primary_took_period_n_high | 104 | 62.5% | 0.721 | 0.663 | 0.625 | 11 | 72.7% | 10.2% |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | 107 | 61.7% | 0.714 | 0.654 | 0.617 | 11 | 90.9% | 29.2% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 104 | 44.2% | 0.710 | 0.673 | 0.558 | 11 | 81.8% | 37.6% |
| at_period_close | high | label.n1_close_moved_with_thesis | 66 | 39.4% | 0.708 | 0.667 | 0.606 | 7 | 71.4% | 32.0% |
| at_period_close | all | label.n2_primary_took_period_n_low | 104 | 36.5% | 0.699 | 0.577 | 0.635 | 11 | 81.8% | 45.3% |
| at_period_close | high | label.n2_primary_took_period_n_high | 64 | 67.2% | 0.680 | 0.641 | 0.672 | 7 | 85.7% | 18.5% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 64 | 37.5% | 0.675 | 0.703 | 0.625 | 7 | 57.1% | 19.6% |
| at_period_close | high | label.n2_primary_took_period_n_low | 64 | 37.5% | 0.675 | 0.703 | 0.625 | 7 | 57.1% | 19.6% |
| at_period_close | all | label.n2_close_moved_with_thesis | 104 | 51.0% | 0.672 | 0.644 | 0.490 | 11 | 81.8% | 30.9% |
| at_fire | high | label.n1_or_n2_thesis_confirmed_strict | 66 | 53.0% | 0.668 | 0.621 | 0.530 | 7 | 85.7% | 32.7% |
| at_fire | high | label.n2_thesis_confirmed_strict | 64 | 37.5% | 0.656 | 0.625 | 0.625 | 7 | 57.1% | 19.6% |
| at_fire | high | label.n2_primary_took_period_n_low | 64 | 37.5% | 0.656 | 0.625 | 0.625 | 7 | 57.1% | 19.6% |
| at_fire | all | label.n1_thesis_confirmed_strict | 107 | 46.7% | 0.656 | 0.533 | 0.533 | 11 | 27.3% | -19.5% |
| at_fire | all | label.n1_or_n2_thesis_confirmed_strict | 107 | 56.1% | 0.644 | 0.673 | 0.561 | 11 | 90.9% | 34.8% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 66 | 48.5% | 0.624 | 0.591 | 0.485 | 7 | 42.9% | -5.6% |
| at_fire | all | label.n1_primary_took_period_n_high | 107 | 57.9% | 0.623 | 0.626 | 0.579 | 11 | 90.9% | 33.0% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_period_close | all | label.n1_thesis_confirmed_strict | pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=412; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=295; pc.n_4h_fvg_bullish_same_primary_in_window=260; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=215; pc.minutes_since_last_sweep_asia_low_1h_low_same_primary_in_window=171; pc.n_1h_fvg_bearish_same_primary_in_window=161; pc.minutes_since_last_sweep_london_high_1h_high_same_primary_in_window=158; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=157; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=148; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=146 |
| at_period_close | high | label.n1_primary_took_period_n_high | pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=352; pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=267; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=232; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=170; pc.n_ob_swept_pdh_4h_bearish_same_primary_in_window=114; pc.minutes_since_last_sweep_high_same_primary_in_window=99; pc.minutes_since_last_ob_swept_london_high_1h_bearish_same_primary_in_window=98; pc.n_4h_fvg_bearish_same_primary_in_window=95; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=68; pc.n_1h_fvg_bearish_same_primary_in_window=63 |
| at_period_close | all | label.n1_primary_took_period_n_high | pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=562; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=368; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=207; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=187; pc.minutes_since_last_sweep_asia_low_1h_low_same_primary_in_window=154; pc.n_4h_fvg_bullish_same_primary_in_window=135; pc.n_ob_swept_pdh_4h_bearish_same_primary_in_window=134; pc.minutes_since_last_sweep_london_high_1h_high_same_primary_in_window=129; smt.ed.first_break_price=124; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=118 |
| at_period_close | all | label.n1_primary_took_period_n_low | pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=452; pc.n_4h_fvg_bullish_same_primary_in_window=444; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=261; pc.minutes_since_last_sweep_pdl_1h_low_same_primary_in_window=212; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=180; pc.n_1h_fvg_bearish_same_primary_in_window=159; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=131; pc.minutes_since_last_ob_swept_london_high_1h_bearish_same_primary_in_window=131; pc.minutes_since_last_sweep_london_high_1h_high_same_primary_in_window=126; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=122 |
| at_period_close | high | label.n1_thesis_confirmed_strict | pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=594; pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=305; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=176; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=127; pc.n_15m_fvg_bearish_same_primary_in_window=124; pc.n_1h_disp_bearish_same_primary_in_window=91; pc.n_1h_fvg_bearish_same_primary_in_window=88; pc.minutes_since_last_sweep_london_high_1h_high_same_primary_in_window=86; pc.minutes_since_last_ob_swept_pwh_4h_bearish_same_primary_in_window=63; pc.minutes_since_last_sweep_high_same_primary_in_window=45 |
| at_period_close | high | label.n1_primary_took_period_n_low | pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=594; pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=305; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=176; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=127; pc.n_15m_fvg_bearish_same_primary_in_window=124; pc.n_1h_disp_bearish_same_primary_in_window=91; pc.n_1h_fvg_bearish_same_primary_in_window=88; pc.minutes_since_last_sweep_london_high_1h_high_same_primary_in_window=86; pc.minutes_since_last_ob_swept_pwh_4h_bearish_same_primary_in_window=63; pc.minutes_since_last_sweep_high_same_primary_in_window=45 |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=439; pc.minutes_since_last_ob_swept_london_high_1h_bearish_same_primary_in_window=199; pc.n_4h_fvg_bullish_same_primary_in_window=183; smt.ed.first_break_price=171; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=168; smt.ed.symbol_states.YM.c.0.reference_high=132; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=132; pc.minutes_since_last_sweep_pdl_4h_low_same_primary_in_window=122; pc.minutes_since_last_ob_swept_pwl_4h_bullish_same_primary_in_window=118; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=116 |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=288; pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=286; pc.n_1h_disp_bearish_same_primary_in_window=203; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=177; pc.minutes_since_last_ob_swept_london_high_1h_bearish_same_primary_in_window=117; pc.minutes_since_last_4h_psp_bearish_in_window=92; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=79; smt.ed.first_break_price=73; pc.n_1h_fvg_bearish_same_primary_in_window=66; pc.n_4h_fvg_bearish_same_primary_in_window=57 |
| at_period_close | all | label.n1_close_moved_with_thesis | pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=235; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=158; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=109; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=104; pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=93; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=81; pc.minutes_since_last_ob_swept_london_low_1h_bullish_same_primary_in_window=71; pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window=70; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=59; pc.n_ob_swept_ny_high_1h_bearish_same_primary_in_window=53 |
| at_period_close | all | label.n2_primary_took_period_n_high | smt.ed.symbol_states.NQ.c.0.reference_high=215; smt.ed.symbol_states.ES.c.0.reference_high=189; smt.ed.symbol_states.YM.c.0.reference_high=161; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=131; smt.ed.symbol_states.ES.c.0.reference_low=109; pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=103; pc.minutes_since_last_sweep_pdl_4h_low_same_primary_in_window=91; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=91; pc.minutes_since_last_sweep_high_same_primary_in_window=81; smt.ed.symbol_states.NQ.c.0.reference_low=74 |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=319; pc.minutes_since_last_ob_swept_london_low_1h_bullish_same_primary_in_window=149; pc.minutes_since_last_sweep_london_high_1h_high_same_primary_in_window=132; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=109; xd.has_psp_in_24h=109; pc.minutes_since_last_ob_swept_ny_high_1h_bearish_same_primary_in_window=108; pc.n_ob_swept_ny_high_1h_bearish_same_primary_in_window=95; pc.minutes_since_last_sweep_pdl_4h_low_same_primary_in_window=87; pc.n_ob_bearish_same_primary_in_window=85; pc.minutes_since_last_sweep_ny_low_1h_low_same_primary_in_window=73 |
| at_period_close | all | label.n2_thesis_confirmed_strict | pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=166; smt.ed.first_break_price=151; pc.minutes_since_last_sweep_pdl_4h_low_same_primary_in_window=141; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=136; pc.n_4h_fvg_bullish_same_primary_in_window=132; pc.minutes_since_last_4h_psp_bullish_in_window=123; pc.minutes_since_last_ob_swept_ny_high_1h_bearish_same_primary_in_window=119; pc.minutes_since_last_1h_psp_bearish_in_window=91; pc.minutes_since_last_sweep_high_same_primary_in_window=90; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=90 |
| at_period_close | high | label.n1_close_moved_with_thesis | pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=227; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=164; pc.minutes_since_last_sweep_ny_high_1h_high_same_primary_in_window=109; pc.n_ob_swept_ny_high_1h_bearish_same_primary_in_window=70; pc.n_ob_bearish_same_primary_in_window=50; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=49; pc.n_1h_fvg_bearish_same_primary_in_window=33; pc.minutes_since_last_sweep_london_high_1h_high_same_primary_in_window=29; pc.minutes_since_last_ob_bearish_same_primary_in_window=27; pc.minutes_since_last_ob_swept_pwh_4h_bearish_same_primary_in_window=26 |
| at_period_close | all | label.n2_primary_took_period_n_low | smt.ed.symbol_states.ES.c.0.reference_low=287; smt.ed.symbol_states.NQ.c.0.reference_low=248; smt.ed.symbol_states.NQ.c.0.reference_high=207; pc.minutes_since_last_ob_swept_ny_high_1h_bearish_same_primary_in_window=169; pc.n_15m_fvg_bullish_same_primary_in_window=142; smt.year=119; smt.ed.symbol_states.YM.c.0.reference_high=115; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=114; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=106; pc.minutes_since_last_ob_swept_pdh_4h_bearish_same_primary_in_window=102 |
| at_period_close | high | label.n2_primary_took_period_n_high | pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=360; pc.minutes_since_last_ob_swept_ny_high_1h_bearish_same_primary_in_window=187; smt.ed.symbol_states.NQ.c.0.reference_high=175; smt.ed.first_break_price=92; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=90; pc.minutes_since_last_ob_bearish_same_primary_in_window=68; pc.minutes_since_last_daily_disp_bearish_same_primary_in_window=66; pc.n_1h_disp_bearish_same_primary_in_window=63; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=61; pc.n_ob_swept_pdh_4h_bearish_same_primary_in_window=60 |

## Skipped Summary

| status | count |
|---|---|
| skip_small_split | 20 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
