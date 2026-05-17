# SMT - HTF Reference Divergence

> One index takes a higher-timeframe reference high/low. The others don't (yet). That divergence is the signal.

## What it is

Smart Money Technique. The original HTF detector has two modes:

| Mode | Reference | Tracking candles |
|---|---|---|
| `weekly_smt` | previous Globex week H/L | 4H |
| `previous_day_smt` | previous Globex day H/L | 1H |

A SMT event fires the instant exactly one symbol breaks its prior-period reference (high or low) while peers haven't broken theirs yet. If all symbols break on the same candle, that is correlated breakout, not divergence. One event per mode, side, and period.

The leading symbol is `first_break_symbol`. Lagging, unconfirmed symbols are recorded too. After firing, the detector walks forward to record `later_confirmations` for laggers. Those fields are fill-after-fire and must NOT feed ML (see leakage caveat below).

## Previous-candle / MTF SMT

There is now a separate lower/multi-timeframe detector: `smt_prev_candle_divergence`.

It compares each symbol against its own previous candle high/low. A high-side event means at least one symbol swept its previous candle high while at least one peer did not. A low-side event is the mirror against previous candle lows.

Supported modes:

| Mode | Tracking candles |
|---|---|
| `15m_prev_candle_smt` | 15m |
| `30m_prev_candle_smt` | 30m |
| `1h_prev_candle_smt` | 1H |
| `90m_prev_candle_smt` | 90m |
| `4h_prev_candle_smt` | 4H |
| `6h_prev_candle_smt` | 6H |

These events are only stamped after the current candle closes. The detector records wick-based SMT and whether it was confirmed by candle close through:

- `event_data.close_confirmed_at_close`
- `event_data.primary_close_confirmed`
- `event_data.close_confirmed_symbols`

Persisted MTF `event_type` values add `_high` or `_low` to the scan mode, for
example `15m_prev_candle_smt_high`. This prevents high-side and low-side SMT on
the same candle from colliding in the research-event id.

The MTF feature matrix short name is `smt_mtf`, so ML output should land at `data/ml/features/smt_mtf.parquet` once the detector is scanned and the feature matrix builder is run.

## Where the code lives

| Component | Path |
|---|---|
| HTF detector | `backend/app/research/detectors/smt_htf_reference_divergence.py` |
| HTF outcomes | `backend/app/research/outcomes/smt_htf_reactions.py` |
| MTF detector | `backend/app/research/detectors/smt_prev_candle_divergence.py` |
| MTF outcomes | `backend/app/research/outcomes/smt_prev_candle_reactions.py` |
| HTF feature matrix (ML) | `data/ml/features/smt.parquet` |
| MTF feature matrix (ML) | `data/ml/features/smt_mtf.parquet` |
| Tests | `backend/tests/test_*smt*` |
| Live stats | `./stats.md` (this folder) |

## What the HTF outcomes record

For each HTF event, the outcomes computer scores three windows:

- **period_close** - what happened by the end of the SMT period (did all symbols eventually break? did the primary still hold its sweep?)
- **intra_period** - MFE/MAE in points for the thesis direction
- **next_period** - N+1: did the next period's price action confirm the thesis (price moved away from the broken level)?

The headline HTF label is `oc.next_period.thesis_confirmed_strict` - did the next period confirm the divergence call?

## What the MTF outcomes record

For each previous-candle MTF event, the outcomes computer scores forward windows from the candle close:

- `next_15m`
- `next_30m`
- `next_60m`
- `next_240m`
- `next_1d`

Each window records thesis-direction MFE/MAE, whether price confirmed the thesis by taking the current candle's opposite side, whether the close moved with the thesis, and whether price swept the current candle high/low.

## Known caveat: SMT feature leakage

Several HTF `event_data.*` fields are enriched within the period by walking forward, for example `did_all_confirm_by_window_end`, `later_confirmations`, and `symbol_states.<sym>.broke_high`. Those are not knowable at the event's fire timestamp.

The Phase-2 baseline (`backend/scripts/ml/baseline_per_detector.py`) drops them via a per-detector exclude list. Do not add them back without thinking. Full audit: [`docs/ML_BASELINE_LEAKAGE_AUDIT.md`](../../../../../docs/ML_BASELINE_LEAKAGE_AUDIT.md).

For MTF SMT, the event timestamp is the current candle close. Close-confirmation fields are knowable at that timestamp. Future reaction outcomes are still labels, not input features.

## Related findings docs

- [`docs/SMT_FVG_FINDINGS.md`](../../../../../docs/SMT_FVG_FINDINGS.md) - SMT x FVG composite cell (89% N+1 on low-side)
- [`docs/SMT_OB_FINDINGS.md`](../../../../../docs/SMT_OB_FINDINGS.md) - SMT x OB composite cell (~70% N+1 on high-side)
- [`docs/COMPOSITE_FINDINGS.md`](../../../../../docs/COMPOSITE_FINDINGS.md) - triple-stack and other crosses

## Tuning knobs

The HTF detector is parameterless beyond mode selection. Reference periods and tracking timeframes are hardcoded per mode. To change behavior, edit the detector directly.

The MTF detector is also parameterless beyond mode selection. To add or remove tracking timeframes, edit `backend/app/research/detectors/smt_prev_candle_divergence.py` and ensure `app.data.reader.read_bars` supports the timeframe.

For ML-side knobs, see `backend/scripts/ml/baseline_per_detector.py` (`DETECTOR_EVENT_DATA_EXCLUDE_PREFIXES["smt"]`) and the feature matrix mappings in `backend/scripts/ml/build_feature_matrix.py`.
