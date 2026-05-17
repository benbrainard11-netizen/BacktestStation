# ML Timeframe Stack Context

_Generated 2026-05-17T18:21:02+00:00 by `backend/scripts/ml/build_timeframe_stack_context.py`._

## What This Tests

This tests parent SMT events against lower-timeframe child concepts.
Example: weekly SMT with daily/4H/1H OB/FVG/sweep/PSP context, or 4H SMT with 1H/30m/15m child context once `smt_mtf.parquet` exists.

- `phase=pre`: child concept was already knowable before or at the parent cutoff. This is safe as ML context.
- `phase=post`: child concept formed after the parent cutoff. This is useful descriptive research, but not legal as an input to the parent signal.
- `aligned`: child direction matches SMT thesis. High-side SMT implies down; low-side SMT implies up.
- `opposed`: child direction goes against SMT thesis.
- Only child timeframes shorter than the parent timeframe are counted.

## Inputs

- Parents requested: `all`
- Children requested: `all`
- Minimum bucket size: `25`
- Missing/skipped parent matrices: `smt_mtf`

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
| weekly_smt | high | ob | 1h | opposed | 1h | n_plus_2.thesis_confirmed_strict | 28 | 44.7% | 64.3% | +19.6% | 1.8% |
| weekly_smt | high | psp | 1d | aligned | 3d | next_period.close_moved_with_thesis | 52 | 50.1% | 69.2% | +19.2% | 3.4% |
| weekly_smt | low | eql | 1d | any | 3d | n_plus_2.thesis_confirmed_strict | 31 | 47.8% | 64.5% | +16.7% | 2.1% |
| weekly_smt | low | eql | 1d | opposed | 3d | n_plus_2.thesis_confirmed_strict | 28 | 47.8% | 64.3% | +16.5% | 1.9% |
| weekly_smt | low | eql | 1h | opposed | 4h | n_plus_2.thesis_confirmed_strict | 55 | 47.8% | 61.8% | +14.0% | 3.8% |
| previous_day_smt | low | psp | 4h | aligned | 1h | next_period.close_moved_with_thesis | 81 | 50.6% | 64.2% | +13.6% | 2.1% |
| weekly_smt | low | disp | 4h | aligned | 4h | n_plus_2.thesis_confirmed_strict | 49 | 47.8% | 61.2% | +13.4% | 3.4% |
| weekly_smt | low | disp | 4h | aligned | 1h | n_plus_2.thesis_confirmed_strict | 36 | 47.8% | 61.1% | +13.3% | 2.5% |
| weekly_smt | low | eql | 4h | opposed | 4h | n_plus_2.thesis_confirmed_strict | 35 | 47.8% | 60.0% | +12.2% | 2.4% |
| weekly_smt | low | psp | 1d | any | 1h | next_period.thesis_confirmed_strict | 31 | 45.9% | 58.1% | +12.2% | 2.1% |
| weekly_smt | low | eql | 1d | any | 3d | next_period.thesis_confirmed_strict | 31 | 45.9% | 58.1% | +12.2% | 2.1% |
| weekly_smt | low | psp | 1h | opposed | 1h | next_period.close_moved_with_thesis | 74 | 52.8% | 64.9% | +12.0% | 5.1% |
| weekly_smt | low | eql | 1h | any | 4h | n_plus_2.thesis_confirmed_strict | 77 | 47.8% | 59.7% | +11.9% | 5.3% |
| previous_day_smt | low | sweep | 4h | aligned | 1h | next_period.close_moved_with_thesis | 61 | 50.6% | 62.3% | +11.7% | 1.6% |
| weekly_smt | low | eql | 1d | any | 3d | next_period.close_moved_with_thesis | 31 | 52.8% | 64.5% | +11.7% | 2.1% |
| weekly_smt | low | eql | 1d | opposed | 3d | next_period.thesis_confirmed_strict | 28 | 45.9% | 57.1% | +11.3% | 1.9% |
| weekly_smt | low | eql | 1h | any | 1d | n_plus_2.thesis_confirmed_strict | 109 | 47.8% | 58.7% | +10.9% | 7.5% |
| weekly_smt | low | psp | 1h | aligned | 4h | next_period.thesis_confirmed_strict | 127 | 45.9% | 56.7% | +10.8% | 8.7% |
| weekly_smt | high | ob | 1h | opposed | 1h | next_period.close_moved_with_thesis | 28 | 50.1% | 60.7% | +10.6% | 1.8% |
| weekly_smt | low | eql | 1h | opposed | 1d | n_plus_2.thesis_confirmed_strict | 101 | 47.8% | 58.4% | +10.6% | 7.0% |
| weekly_smt | high | swing | 1d | opposed | 4h | next_period.thesis_confirmed_strict | 84 | 43.4% | 53.6% | +10.2% | 5.5% |
| weekly_smt | high | fvg | 1d | aligned | 1d | next_period.close_moved_with_thesis | 25 | 50.1% | 60.0% | +9.9% | 1.6% |
| weekly_smt | low | eql | 1h | opposed | 7d | n_plus_2.thesis_confirmed_strict | 201 | 47.8% | 57.7% | +9.9% | 13.9% |
| previous_day_smt | low | eql | 4h | opposed | 4h | next_period.close_moved_with_thesis | 43 | 50.6% | 60.5% | +9.9% | 1.1% |
| weekly_smt | low | eql | 1h | any | 7d | n_plus_2.thesis_confirmed_strict | 203 | 47.8% | 57.6% | +9.8% | 14.0% |
| weekly_smt | low | eql | 1h | aligned | 7d | n_plus_2.thesis_confirmed_strict | 200 | 47.8% | 57.5% | +9.7% | 13.8% |
| weekly_smt | low | disp | 4h | aligned | 1h | next_period.thesis_confirmed_strict | 36 | 45.9% | 55.6% | +9.7% | 2.5% |
| weekly_smt | high | swing | 1d | any | 4h | next_period.thesis_confirmed_strict | 85 | 43.4% | 52.9% | +9.5% | 5.6% |
| weekly_smt | low | eql | 1d | opposed | 7d | n_plus_2.thesis_confirmed_strict | 49 | 47.8% | 57.1% | +9.3% | 3.4% |
| weekly_smt | low | disp | 4h | aligned | 4h | next_period.thesis_confirmed_strict | 49 | 45.9% | 55.1% | +9.2% | 3.4% |

## Best Post-Formation Buckets

| parent | side | child | child_tf | relation | window | label | n | base | with_child | lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| weekly_smt | high | sweep | 1d | opposed | 7d | next_period.thesis_confirmed_strict | 321 | 43.4% | 73.8% | +30.4% |
| weekly_smt | low | sweep | 1d | opposed | 7d | next_period.thesis_confirmed_strict | 325 | 45.9% | 72.6% | +26.7% |
| weekly_smt | low | eql | 1d | aligned | 7d | n_plus_2.thesis_confirmed_strict | 28 | 47.8% | 71.4% | +23.6% |
| weekly_smt | high | eql | 1d | aligned | 7d | next_period.thesis_confirmed_strict | 30 | 43.4% | 66.7% | +23.3% |
| weekly_smt | low | eql | 1d | aligned | 7d | next_period.thesis_confirmed_strict | 28 | 45.9% | 67.9% | +22.0% |
| weekly_smt | low | swing | 1d | aligned | 7d | next_period.thesis_confirmed_strict | 606 | 45.9% | 66.3% | +20.5% |
| weekly_smt | low | fvg | 1d | aligned | 7d | next_period.thesis_confirmed_strict | 608 | 45.9% | 66.1% | +20.3% |
| weekly_smt | low | sweep | 1d | opposed | 7d | n_plus_2.thesis_confirmed_strict | 325 | 47.8% | 67.7% | +19.9% |
| weekly_smt | high | swing | 1d | aligned | 7d | next_period.thesis_confirmed_strict | 588 | 43.4% | 63.3% | +19.9% |
| weekly_smt | high | sweep | 4h | opposed | 4h | n_plus_2.thesis_confirmed_strict | 28 | 44.7% | 64.3% | +19.6% |
| weekly_smt | high | psp | 1h | aligned | 1h | n_plus_2.thesis_confirmed_strict | 39 | 44.7% | 64.1% | +19.4% |
| weekly_smt | high | fvg | 1d | aligned | 7d | next_period.thesis_confirmed_strict | 622 | 43.4% | 62.2% | +18.8% |
| weekly_smt | high | sweep | 1d | opposed | 7d | n_plus_2.thesis_confirmed_strict | 321 | 44.7% | 63.2% | +18.5% |
| weekly_smt | high | disp | 1d | aligned | 7d | next_period.thesis_confirmed_strict | 501 | 43.4% | 61.3% | +17.9% |
| weekly_smt | low | disp | 1d | aligned | 7d | next_period.thesis_confirmed_strict | 512 | 45.9% | 63.1% | +17.2% |
| weekly_smt | low | disp | 1d | aligned | 3d | next_period.thesis_confirmed_strict | 316 | 45.9% | 63.0% | +17.1% |
| previous_day_smt | low | disp | 4h | aligned | 1d | next_period.thesis_confirmed_strict | 1,292 | 49.1% | 65.9% | +16.9% |
| previous_day_smt | high | fvg | 4h | opposed | 1h | next_period.close_moved_with_thesis | 39 | 47.4% | 64.1% | +16.7% |
| weekly_smt | low | psp | 1h | opposed | 1h | n_plus_2.thesis_confirmed_strict | 31 | 47.8% | 64.5% | +16.7% |
| previous_day_smt | high | disp | 4h | aligned | 1d | next_period.thesis_confirmed_strict | 1,406 | 45.3% | 61.9% | +16.6% |
| weekly_smt | low | eql | 1h | aligned | 4h | n_plus_2.thesis_confirmed_strict | 56 | 47.8% | 64.3% | +16.5% |
| previous_day_smt | high | fvg | 4h | aligned | 1d | next_period.thesis_confirmed_strict | 1,577 | 45.3% | 61.5% | +16.2% |
| weekly_smt | low | eql | 1h | opposed | 4h | n_plus_2.thesis_confirmed_strict | 36 | 47.8% | 63.9% | +16.1% |
| weekly_smt | low | sweep | 1d | opposed | 3d | next_period.thesis_confirmed_strict | 157 | 45.9% | 61.8% | +15.9% |
| weekly_smt | low | eql | 1h | any | 4h | n_plus_2.thesis_confirmed_strict | 77 | 47.8% | 63.6% | +15.8% |
| weekly_smt | low | fvg | 1d | aligned | 3d | next_period.thesis_confirmed_strict | 253 | 45.9% | 61.7% | +15.8% |
| previous_day_smt | high | fvg | 4h | any | 1h | next_period.close_moved_with_thesis | 62 | 47.4% | 62.9% | +15.5% |
| weekly_smt | low | swing | 1d | aligned | 7d | n_plus_2.thesis_confirmed_strict | 605 | 47.8% | 63.3% | +15.5% |
| weekly_smt | low | sweep | 1d | opposed | 3d | n_plus_2.thesis_confirmed_strict | 157 | 47.8% | 63.1% | +15.3% |
| weekly_smt | low | eql | 4h | any | 1d | n_plus_2.thesis_confirmed_strict | 81 | 47.8% | 63.0% | +15.2% |

## Files

- Summary CSV: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_summary.csv`
- Summary parquet: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_summary.parquet`
- Manifest: `C:\Users\benbr\BacktestStation\data\ml\context\timeframe_stack_context_manifest.json`

## Current Gap

`smt_mtf.parquet` will stay missing until the new previous-candle SMT detector is scanned, outcomes are computed, and `build_feature_matrix.py --detectors smt_prev_candle_divergence` is run. After that, rerun this script to rank 4H/6H/1H/90m/30m/15m SMT stacks directly.
