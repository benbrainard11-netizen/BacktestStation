# SMT - Previous-Candle MTF Divergence

Lower-timeframe SMT events where one index sweeps its own previous candle
high/low while peers do not.

## Modes

The detector currently scans the NQ/ES/YM index group on:

- `15m_prev_candle_smt`
- `30m_prev_candle_smt`
- `1h_prev_candle_smt`
- `90m_prev_candle_smt`
- `4h_prev_candle_smt`
- `6h_prev_candle_smt`

Stored event types are side-specific, for example
`15m_prev_candle_smt_high` and `15m_prev_candle_smt_low`. The unsuffixed mode
is kept in `event_data.base_event_type`.

## Real-Time Rule

An event fires at the close of the current candle. It only knows:

- the current candle high/low/close,
- the previous candle high/low,
- whether the primary symbol swept that previous candle level,
- whether peer symbols did not confirm that same sweep by the current close.

The lookahead audit treats these events as knowable at `bar_end_utc`.

## Outcomes

`smt_prev_candle_reactions_v1` computes future reactions from real 1m bars:

- `next_15m`
- `next_30m`
- `next_60m`
- `next_240m`
- `next_1d`

Primary labels are `thesis_confirmed` over each horizon. High-side SMT implies
a downside thesis; low-side SMT implies an upside thesis.

## Code

- Detector: `backend/app/research/detectors/smt_prev_candle_divergence.py`
- Outcomes: `backend/app/research/outcomes/smt_prev_candle_reactions.py`
- Tests: `backend/tests/test_smt_prev_candle_divergence.py`
- Feature matrix: `data/ml/features/smt_mtf.parquet`
- Current numbers: `backend/app/research/features/smt_mtf/stats.md`

## Research Use

Use this as the first real bridge from HTF concepts into intraday structure.
The raw event is intentionally broad; the stronger research question is which
timeframe works best when combined with known-before context such as lower-timeframe
FVG, OB, sweep, PSP, swing, equal levels, and displacement.
