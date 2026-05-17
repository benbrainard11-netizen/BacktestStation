# ML Timeframe Stack Context

_Generated 2026-05-17T19:28:33+00:00 by `backend/scripts/ml/build_timeframe_stack_context.py`._

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
| disp | 187,595 |
| eql | 61,185 |
| fvg | 1,243,757 |
| ob | 198,069 |
| psp | 73,278 |
| sweep | 237,569 |
| swing | 345,702 |

## Best Pre-Context Buckets

| parent | side | child | child_tf | relation | window | label | n | base | with_child | lift | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 1h | next_30m.thesis_confirmed | 32 | 14.6% | 46.9% | +32.2% | 1.3% |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 1h | next_15m.thesis_confirmed | 32 | 10.6% | 40.6% | +30.0% | 1.3% |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 1h | next_60m.thesis_confirmed | 32 | 20.4% | 50.0% | +29.6% | 1.3% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 175 | 20.4% | 49.1% | +28.7% | 7.1% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 175 | 14.6% | 40.0% | +25.4% | 7.1% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 255 | 23.4% | 48.6% | +25.3% | 11.2% |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 1h | next_240m.thesis_confirmed | 32 | 40.7% | 65.6% | +25.0% | 1.3% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 229 | 40.7% | 65.5% | +24.8% | 9.2% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 255 | 48.1% | 72.9% | +24.8% | 11.2% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 229 | 20.4% | 43.2% | +22.8% | 9.2% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_15m.thesis_confirmed | 175 | 10.6% | 33.1% | +22.6% | 7.1% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_240m.thesis_confirmed | 175 | 40.7% | 62.3% | +21.6% | 7.1% |
| 4h_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 427 | 28.3% | 49.6% | +21.3% | 12.1% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 255 | 16.7% | 37.6% | +21.0% | 11.2% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 419 | 23.9% | 44.2% | +20.3% | 11.0% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 384 | 28.3% | 48.4% | +20.1% | 10.9% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 384 | 21.3% | 41.1% | +19.8% | 10.9% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 419 | 17.5% | 37.0% | +19.5% | 11.0% |
| 4h_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 427 | 21.3% | 40.7% | +19.4% | 12.1% |
| 4h_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_15m.thesis_confirmed | 427 | 16.3% | 35.1% | +18.8% | 12.1% |
| 6h_prev_candle_smt_high | high | psp | 4h | aligned | 4h | next_1d.thesis_confirmed | 29 | 67.5% | 86.2% | +18.8% | 1.2% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 384 | 51.1% | 69.8% | +18.6% | 10.8% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_15m.thesis_confirmed | 419 | 13.9% | 32.2% | +18.3% | 11.0% |
| 90m_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 534 | 36.9% | 54.9% | +17.9% | 6.0% |
| 6h_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 202 | 23.4% | 41.1% | +17.7% | 8.9% |
| 4h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 363 | 43.9% | 61.4% | +17.5% | 9.4% |
| 90m_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_15m.thesis_confirmed | 534 | 28.2% | 45.5% | +17.3% | 6.0% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 229 | 14.6% | 31.9% | +17.2% | 9.2% |
| 6h_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 202 | 16.7% | 33.7% | +17.0% | 8.9% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_15m.thesis_confirmed | 255 | 12.5% | 29.4% | +16.9% | 11.2% |

## Best Post-Formation Buckets

| parent | side | child | child_tf | relation | window | label | n | base | with_child | lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4h_prev_candle_smt_high | high | sweep | 1h | opposed | 1h | next_60m.thesis_confirmed | 56 | 23.9% | 89.3% | +65.4% |
| 4h_prev_candle_smt_low | low | sweep | 1h | opposed | 1h | next_60m.thesis_confirmed | 68 | 28.3% | 89.7% | +61.4% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 122 | 20.4% | 80.3% | +59.9% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 122 | 14.6% | 71.3% | +56.7% |
| 6h_prev_candle_smt_high | high | disp | 4h | aligned | 4h | next_240m.thesis_confirmed | 163 | 40.7% | 95.7% | +55.0% |
| 6h_prev_candle_smt_high | high | sweep | 4h | opposed | 4h | next_240m.thesis_confirmed | 148 | 40.7% | 93.2% | +52.6% |
| 4h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 252 | 23.9% | 74.6% | +50.7% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 149 | 20.4% | 71.1% | +50.7% |
| 90m_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 567 | 40.7% | 90.8% | +50.1% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 295 | 21.3% | 70.2% | +48.8% |
| 4h_prev_candle_smt_high | high | sweep | 1h | opposed | 1h | next_30m.thesis_confirmed | 56 | 17.5% | 66.1% | +48.6% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 295 | 28.3% | 76.6% | +48.3% |
| 4h_prev_candle_smt_low | low | sweep | 1h | opposed | 1h | next_30m.thesis_confirmed | 68 | 21.3% | 69.1% | +47.8% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_15m.thesis_confirmed | 122 | 10.6% | 58.2% | +47.6% |
| 4h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 252 | 17.5% | 65.1% | +47.6% |
| 4h_prev_candle_smt_high | high | sweep | 1h | opposed | 1h | next_240m.thesis_confirmed | 56 | 43.9% | 91.1% | +47.2% |
| 6h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_240m.thesis_confirmed | 122 | 40.7% | 87.7% | +47.0% |
| 6h_prev_candle_smt_low | low | sweep | 4h | opposed | 4h | next_240m.thesis_confirmed | 151 | 48.1% | 94.7% | +46.6% |
| 6h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_240m.thesis_confirmed | 149 | 40.7% | 86.6% | +45.9% |
| 4h_prev_candle_smt_high | high | fvg | 1h | aligned | 1h | next_15m.thesis_confirmed | 251 | 13.9% | 59.0% | +45.0% |
| 4h_prev_candle_smt_high | high | sweep | 1h | opposed | 1h | next_15m.thesis_confirmed | 56 | 13.9% | 58.9% | +45.0% |
| 4h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_15m.thesis_confirmed | 295 | 16.3% | 60.7% | +44.3% |
| 90m_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_30m.thesis_confirmed | 567 | 31.2% | 75.5% | +44.3% |
| 6h_prev_candle_smt_low | low | disp | 4h | aligned | 4h | next_240m.thesis_confirmed | 160 | 48.1% | 91.2% | +43.1% |
| 90m_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_30m.thesis_confirmed | 361 | 36.9% | 78.9% | +42.0% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_240m.thesis_confirmed | 214 | 43.9% | 85.5% | +41.6% |
| 4h_prev_candle_smt_high | high | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 214 | 23.9% | 65.4% | +41.6% |
| 4h_prev_candle_smt_low | low | sweep | 1h | opposed | 1h | next_240m.thesis_confirmed | 68 | 51.1% | 92.6% | +41.5% |
| 6h_prev_candle_smt_low | low | fvg | 1h | aligned | 1h | next_60m.thesis_confirmed | 165 | 23.4% | 63.6% | +40.3% |
| 90m_prev_candle_smt_low | low | disp | 1h | aligned | 1h | next_60m.thesis_confirmed | 591 | 46.8% | 87.0% | +40.2% |

## Files

- Summary CSV: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_summary.csv`
- Summary parquet: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_summary.parquet`
- Manifest: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_manifest.json`

## Status

All requested parent matrices were available. `phase=pre` rows are the legal context candidates for parent-signal ML; `phase=post` rows are descriptive only.
