# ML Timeframe Stack Context

_Generated 2026-05-17T22:08:25+00:00 by `backend/scripts/ml/build_timeframe_stack_context.py`._

## What This Tests

This tests parent SMT events against lower-timeframe child concepts.
Example: weekly SMT with daily/4H/1H OB/FVG/sweep/PSP context, or 4H SMT with 1H/30m/15m child context once `smt_mtf.parquet` exists.

- `phase=pre`: child concept was already knowable before or at the parent cutoff. This is safe as ML context.
- `phase=post`: child concept formed after the parent cutoff. This is useful descriptive research, but not legal as an input to the parent signal.
- `aligned`: child direction matches SMT thesis. High-side SMT implies down; low-side SMT implies up.
- `opposed`: child direction goes against SMT thesis.
- Only child timeframes shorter than the parent timeframe are counted.

## Inputs

- Parents requested: `smt_mtf`
- Children requested: `all`
- Minimum bucket size: `25`
- Missing/skipped parent matrices: `none`

Child rows loaded:

| child | rows |
| --- | --- |
| disp | 214,599 |
| eql | 61,185 |
| fvg | 1,243,757 |
| ob | 198,069 |
| psp | 77,933 |
| sweep | 237,569 |
| swing | 345,702 |

## Best Pre-Context Buckets

| parent | side | child | child_tf | relation | window | label | n | base | with_child | lift | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 1h | next_240m.thesis_confirmed | 43 | 40.7% | 74.4% | +33.8% | 1.7% |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 1h | next_30m.thesis_confirmed | 43 | 14.6% | 44.2% | +29.5% | 1.7% |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 1h | next_60m.thesis_confirmed | 43 | 20.4% | 48.8% | +28.4% | 1.7% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 244 | 20.4% | 48.4% | +27.9% | 9.8% |
| 6h_prev_candle_smt_high | high | disp | 30m | aligned | 1h | next_60m.thesis_confirmed | 370 | 20.4% | 47.6% | +27.2% | 14.9% |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 1h | next_15m.thesis_confirmed | 43 | 10.6% | 37.2% | +26.6% | 1.7% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 255 | 23.4% | 48.6% | +25.3% | 11.2% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 229 | 40.7% | 65.5% | +24.8% | 9.2% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 255 | 48.1% | 72.9% | +24.8% | 11.2% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 244 | 14.6% | 39.3% | +24.7% | 9.8% |
| 6h_prev_candle_smt_high | high | disp | 30m | aligned | 1h | next_240m.thesis_confirmed | 370 | 40.7% | 65.1% | +24.5% | 14.9% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 229 | 20.4% | 43.2% | +22.8% | 9.2% |
| 6h_prev_candle_smt_low | low | disp | 30m | aligned | 1h | next_240m.thesis_confirmed | 351 | 48.1% | 70.4% | +22.3% | 15.4% |
| 6h_prev_candle_smt_high | high | disp | 30m | aligned | 1h | next_30m.thesis_confirmed | 370 | 14.6% | 36.2% | +21.6% | 14.9% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_15m.thesis_confirmed | 244 | 10.6% | 32.0% | +21.4% | 9.9% |
| 6h_prev_candle_smt_low | low | disp | 4h | aligned | 1h | next_60m.thesis_confirmed | 36 | 23.4% | 44.4% | +21.1% | 1.6% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 586 | 23.9% | 44.9% | +21.0% | 15.3% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 255 | 16.7% | 37.6% | +21.0% | 11.2% |
| 6h_prev_candle_smt_high | high | disp | 15m | aligned | 1h | next_60m.thesis_confirmed | 449 | 20.4% | 41.0% | +20.6% | 18.1% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 586 | 17.5% | 37.9% | +20.4% | 15.3% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 384 | 28.3% | 48.4% | +20.1% | 10.9% |
| 4h_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 599 | 28.3% | 48.2% | +19.9% | 17.0% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 384 | 21.3% | 41.1% | +19.8% | 10.9% |
| 6h_prev_candle_smt_high | high | disp | 15m | aligned | 1h | next_240m.thesis_confirmed | 449 | 40.7% | 60.1% | +19.5% | 18.1% |
| 6h_prev_candle_smt_high | high | disp | 30m | aligned | 1h | next_15m.thesis_confirmed | 369 | 10.6% | 29.8% | +19.2% | 14.9% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_240m.thesis_confirmed | 244 | 40.7% | 59.8% | +19.2% | 9.8% |
| 4h_prev_candle_smt_high | high | disp | 30m | aligned | 1h | next_60m.thesis_confirmed | 838 | 23.9% | 42.6% | +18.7% | 21.9% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 384 | 51.1% | 69.8% | +18.6% | 10.8% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_15m.thesis_confirmed | 586 | 13.9% | 32.6% | +18.6% | 15.3% |
| 6h_prev_candle_smt_low | low | disp | 4h | aligned | 1h | next_240m.thesis_confirmed | 36 | 48.1% | 66.7% | +18.6% | 1.6% |

## Best Post-Formation Buckets

| parent | side | child | child_tf | relation | window | label | n | base | with_child | lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4h_prev_candle_smt_high | high | sweep | 1h | opposed | 1h | next_60m.thesis_confirmed | 56 | 23.9% | 89.3% | +65.4% |
| 4h_prev_candle_smt_low | low | sweep | 1h | opposed | 1h | next_60m.thesis_confirmed | 68 | 28.3% | 89.7% | +61.4% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 122 | 20.4% | 80.3% | +59.9% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 122 | 14.6% | 71.3% | +56.7% |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 4h | next_240m.thesis_confirmed | 212 | 40.7% | 93.4% | +52.7% |
| 6h_prev_candle_smt_high | high | sweep | 4h | opposed | 4h | next_240m.thesis_confirmed | 148 | 40.7% | 93.2% | +52.6% |
| 4h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 252 | 23.9% | 74.6% | +50.7% |
| 90m_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 782 | 40.7% | 90.2% | +49.5% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 194 | 20.4% | 69.6% | +49.2% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 295 | 21.3% | 70.2% | +48.8% |
| 4h_prev_candle_smt_high | high | sweep | 1h | opposed | 1h | next_30m.thesis_confirmed | 56 | 17.5% | 66.1% | +48.6% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 295 | 28.3% | 76.6% | +48.3% |
| 4h_prev_candle_smt_low | low | sweep | 1h | opposed | 1h | next_30m.thesis_confirmed | 68 | 21.3% | 69.1% | +47.8% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_15m.thesis_confirmed | 122 | 10.6% | 58.2% | +47.6% |
| 4h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 252 | 17.5% | 65.1% | +47.6% |
| 4h_prev_candle_smt_high | high | sweep | 1h | opposed | 1h | next_240m.thesis_confirmed | 56 | 43.9% | 91.1% | +47.2% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 122 | 40.7% | 87.7% | +47.0% |
| 6h_prev_candle_smt_low | low | sweep | 4h | opposed | 4h | next_240m.thesis_confirmed | 151 | 48.1% | 94.7% | +46.6% |
| 4h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_15m.thesis_confirmed | 251 | 13.9% | 59.0% | +45.0% |
| 4h_prev_candle_smt_high | high | sweep | 1h | opposed | 1h | next_15m.thesis_confirmed | 56 | 13.9% | 58.9% | +45.0% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_15m.thesis_confirmed | 295 | 16.3% | 60.7% | +44.3% |
| 6h_prev_candle_smt_low | low | disp | 4h | aligned | 4h | next_240m.thesis_confirmed | 216 | 48.1% | 92.1% | +44.0% |
| 90m_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 782 | 31.2% | 75.2% | +44.0% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_240m.thesis_confirmed | 194 | 40.7% | 84.5% | +43.9% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 278 | 23.9% | 66.5% | +42.7% |
| 90m_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 361 | 36.9% | 78.9% | +42.0% |
| 4h_prev_candle_smt_low | low | sweep | 1h | opposed | 1h | next_240m.thesis_confirmed | 68 | 51.1% | 92.6% | +41.5% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_240m.thesis_confirmed | 278 | 43.9% | 85.3% | +41.3% |
| 6h_prev_candle_smt_high | high | disp | 30m | aligned | 1h | next_240m.thesis_confirmed | 322 | 40.7% | 81.1% | +40.4% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 165 | 23.4% | 63.6% | +40.3% |

## Files

- Summary CSV: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_summary.csv`
- Summary parquet: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_summary.parquet`
- Manifest: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_manifest.json`

## Status

All requested parent matrices were available. `phase=pre` rows are the legal context candidates for parent-signal ML; `phase=post` rows are descriptive only.
