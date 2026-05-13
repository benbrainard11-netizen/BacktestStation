# ML Phase 3 - composite SMT anchor

_Generated `2026-05-11T03:20:51.449097+00:00`._

## Setup

- Anchor: `previous_day_smt` with side=`low`
- Prediction timestamp: period N close (`period_close.ts_utc`)
- Label: `oc.next_period.thesis_confirmed_strict`
- Split: train <= 2022 / val = 2023 / test >= 2024
- Features: filtered SMT fire-time fields, chronological/context metadata, all coarse `xd.has_*_in_24h` flags, `pc.active_at_close`, and exact period-close `pc.has_*_in_window` aligned-detector flags
- No N+1/N+2 `oc.*` columns are model features. The manual 89 percent cell is computed only as a comparison benchmark and is explicitly dropped before model training.

## Metrics

| split | n | positives | actual_rate | auc | accuracy |
|---|---|---|---|---|---|
| train | 761 | 367 | 48.2% | 0.977 | 0.903 |
| val | 125 | 67 | 53.6% | 0.823 | 0.704 |
| test | 251 | 124 | 49.4% | 0.880 | 0.805 |

Majority-class test accuracy: `0.506`. Top-decile test rate: `100.0%` on n=26.

## Per-symbol Breakdown

| symbol | test_n | actual_rate | auc | top_decile_n | top_decile_rate | manual_cell_n | manual_cell_rate |
|---|---|---|---|---|---|---|---|
| ES.c.0 | 102 | 51.0% | 0.893 | 11 | 100.0% | 13 | 100.0% |
| NQ.c.0 | 63 | 47.6% | 0.847 | 8 | 100.0% | 7 | 100.0% |
| YM.c.0 | 86 | 48.8% | 0.887 | 7 | 100.0% | 8 | 87.5% |

## Top-20 LightGBM Features

| rank | feature | gain |
|---|---|---|
| 1 | pc.has_sweep_ny_low_1h_low_same_primary_in_window | 2145 |
| 2 | pc.has_4h_disp_bullish_same_primary_in_window | 992 |
| 3 | pc.has_1h_fvg_bullish_same_primary_in_window | 918 |
| 4 | pc.has_4h_fvg_bullish_same_primary_in_window | 709 |
| 5 | ed.first_break_price | 485 |
| 6 | day_of_week | 414 |
| 7 | pc.active_at_close | 398 |
| 8 | hour_of_day_utc | 368 |
| 9 | ed.symbol_states.ES.c.0.reference_high | 328 |
| 10 | month | 293 |
| 11 | pc.has_1h_disp_bullish_same_primary_in_window | 290 |
| 12 | ed.symbol_states.YM.c.0.reference_high | 288 |
| 13 | pc.has_ob_swept_ny_low_1h_bullish_same_primary_in_window | 256 |
| 14 | ed.symbol_states.NQ.c.0.reference_high | 241 |
| 15 | ctx.hour_of_day_et | 234 |
| 16 | ctx.day_of_week_et | 226 |
| 17 | pc.has_sweep_low_same_primary_in_window | 222 |
| 18 | ed.symbol_states.YM.c.0.reference_low | 162 |
| 19 | pc.has_ob_swept_pdl_4h_bullish_same_primary_in_window | 162 |
| 20 | ed.symbol_states.NQ.c.0.reference_low | 157 |

## Manual 89 Percent Cell Comparison

Manual cell: `active_at_close=1` plus bullish `1h_psp` and bullish same-primary `4h_fvg` in the zero-look-ahead window `(smt_knowable_ts, period_close]`.

| slice | n | n1_rate | n1_or_n2_rate |
|---|---|---|---|
| all_test | 251 | 49.4% | 64.9% |
| model_top_decile | 26 | 100.0% | 100.0% |
| manual_cell | 28 | 96.4% | 100.0% |
| overlap | 11 | 100.0% | 100.0% |
| model_only | 15 | 100.0% | 100.0% |
| manual_only | 17 | 94.1% | 100.0% |

- Top-decile vs manual-cell overlap, as percent of top decile: `42.3%`.
- Top-decile vs manual-cell overlap, as percent of manual cell: `39.3%`.
- Boolean agreement rate over all test events: `87.3%`.

## Calibration

| decile | n | mean_pred | actual_rate | plot |
|---|---|---|---|---|
| 1 | 26 | 0.042 | 0.0% | . |
| 2 | 25 | 0.108 | 16.0% | ### |
| 3 | 25 | 0.162 | 28.0% | ###### |
| 4 | 25 | 0.258 | 16.0% | ### |
| 5 | 25 | 0.352 | 32.0% | ###### |
| 6 | 25 | 0.468 | 60.0% | ############ |
| 7 | 25 | 0.651 | 76.0% | ############### |
| 8 | 25 | 0.770 | 76.0% | ############### |
| 9 | 25 | 0.869 | 92.0% | ################## |
| 10 | 25 | 0.939 | 100.0% | #################### |

## Notes

- The model found a different period-close composite subset with equal-or-better N+1 rate than the manual cell on this test split.
- `active_at_close` is included only because this is a period-close decision model. It is not valid for an entry-at-SMT-fire model.
- The exact `pc.has_*_in_window` flags are recomputed from event-store knowability timestamps and period-close caps; they are stronger and cleaner than the coarse Phase 1 `xd.has_*_in_24h` prior-event flags.
