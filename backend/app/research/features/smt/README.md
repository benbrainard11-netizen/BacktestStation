# SMT — HTF Reference Divergence

> One index takes a higher-timeframe reference high/low. The others don't (yet). That divergence is the signal.

## What it is

Smart Money Technique. Two modes:

| Mode | Reference | Tracking candles |
|---|---|---|
| `weekly_smt` | previous Globex week H/L | 4H |
| `previous_day_smt` | previous Globex day H/L | 1H |

A SMT event fires the instant **exactly one symbol** breaks its prior-period reference (high or low) while peers haven't broken theirs yet. If all symbols break on the same candle → no event (that's correlated breakout, not divergence). One event per (mode, side, period).

The leading symbol is `first_break_symbol`. Lagging (unconfirmed) symbols are recorded too. After firing, the detector walks forward to record `later_confirmations` for laggers — those fields are **fill-after-fire** and must NOT feed ML (see leakage caveat below).

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/smt_htf_reference_divergence.py` |
| Outcomes | `backend/app/research/outcomes/smt_htf_reactions.py` |
| Feature matrix (ML) | `data/ml/features/smt.parquet` |
| Tests | `backend/tests/test_*smt*` |
| Live stats | `./stats.md` (this folder) |

## What the outcomes record

For each event, the outcomes computer scores three windows:

- **period_close** — what happened by the end of the SMT period (did all symbols eventually break? did the primary still hold its sweep?)
- **intra_period** — MFE/MAE in points for the thesis direction
- **next_period** — N+1: did the next period's price action confirm the thesis (price moved AWAY from the broken level)?

The headline label is `oc.next_period.thesis_confirmed_strict` — did the *next* period confirm the divergence call?

## Known caveat: SMT feature leakage

Several `event_data.*` fields are *enriched within the period by walking forward* (e.g. `did_all_confirm_by_window_end`, `later_confirmations`, `symbol_states.<sym>.broke_high`). Those are **not** knowable at the event's fire timestamp.

The Phase-2 baseline (`backend/scripts/ml/baseline_per_detector.py`) drops them via a per-detector exclude list. Don't add them back without thinking. Full audit: [`docs/ML_BASELINE_LEAKAGE_AUDIT.md`](../../../../../docs/ML_BASELINE_LEAKAGE_AUDIT.md).

## Related findings docs

- [`docs/SMT_FVG_FINDINGS.md`](../../../../../docs/SMT_FVG_FINDINGS.md) — SMT × FVG composite cell (89% N+1 on low-side)
- [`docs/SMT_OB_FINDINGS.md`](../../../../../docs/SMT_OB_FINDINGS.md) — SMT × OB composite cell (~70% N+1 on high-side)
- [`docs/COMPOSITE_FINDINGS.md`](../../../../../docs/COMPOSITE_FINDINGS.md) — triple-stack and other crosses

## Tuning knobs (in detector config)

The detector is parameterless beyond mode selection. Reference periods + tracking timeframes are hardcoded per mode. To change behavior, edit the detector directly.

For ML-side knobs, see `backend/scripts/ml/baseline_per_detector.py` (`DETECTOR_EVENT_DATA_EXCLUDE_PREFIXES["smt"]`).
