# SMT State Timeline

_Generated `2026-05-17T23:14:23+00:00` by `backend/scripts/ml/build_smt_state_timeline.py`._

## What This Is

SMT state timeline converts SMT events into active intervals that can be joined to lower-timeframe events as-of their feature cutoff.

- `forming`: HTF reference SMT was known before the HTF period closed.
- `confirmed`: HTF SMT survived the period close. If `--include-mtf` is enabled, previous-candle MTF SMT closes are also represented as confirmed states.
- Joins use `state_start_ts <= asof.feature_cutoff_ts < state_end_ts` for the same `member_symbol`.
- `smtstate.*` columns are legal context features; they do not use future labels.

## Timeline Counts

- Timeline rows: `55,704`
- Source events: `10,889`
- Member symbols: `21`
- Source mode: `features`
- SMT feature source: `C:\Users\benbr\BacktestStation\data\ml\features\smt.parquet`
- Include MTF previous-candle SMT: `False`
- MTF TTL periods: `4`

| scope | stage | rows |
| --- | --- | --- |
| htf_reference | confirmed | 15,920 |
| htf_reference | forming | 39,784 |

## By Event Type

| event_type | stage | side | rows |
| --- | --- | --- | --- |
| previous_day_smt | forming | high | 15,262 |
| previous_day_smt | forming | low | 14,171 |
| weekly_smt | forming | high | 5,342 |
| weekly_smt | forming | low | 5,009 |
| previous_day_smt | confirmed | high | 4,911 |
| previous_day_smt | confirmed | low | 4,701 |
| weekly_smt | confirmed | high | 3,270 |
| weekly_smt | confirmed | low | 3,038 |

## Anchor Context Outputs

| anchor | status | rows | context cols | active | aligned | merged path |
| --- | --- | --- | --- | --- | --- | --- |
| disp | ok | 214,599 | 85 | 61.3% | 50.6% | C:\Users\benbr\BacktestStation\data\ml\anchors\disp_snapshots_smtstate.parquet |
| psp | ok | 77,933 | 85 | 69.5% | 58.5% | C:\Users\benbr\BacktestStation\data\ml\anchors\psp_snapshots_smtstate.parquet |
| fvg | ok | 1,243,757 | 85 | 77.3% | 61.2% | C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_smtstate.parquet |
| sweep | ok | 237,569 | 85 | 77.5% | 61.3% | C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_smtstate.parquet |
| ob | ok | 198,069 | 85 | 78.5% | 62.0% | C:\Users\benbr\BacktestStation\data\ml\anchors\ob_snapshots_smtstate.parquet |

## Files

- Timeline parquet: `C:\Users\benbr\BacktestStation\data\ml\context\smt_state_timeline.parquet`
- Timeline CSV: `C:\Users\benbr\BacktestStation\data\ml\context\smt_state_timeline.csv`
- Context summary: `C:\Users\benbr\BacktestStation\data\ml\context\smt_state_context_summary.csv`
