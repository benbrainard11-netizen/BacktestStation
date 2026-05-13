# ML baseline event_data leakage audit

_Generated `2026-05-10` during the SMT leakage fix pass._

Scope: reviewed `backend/app/research/detectors/*.py` for fields written to
`event_data` after the event's firing timestamp, then mapped those fields to
Phase 2 feature selection in `backend/scripts/ml/baseline_per_detector.py`.

## Applied excludes

### `smt`

Detector: `smt_htf_reference_divergence`

Reason: the detector fires at the first divergent break, then records whether
lagging symbols later confirmed before the current period ended. Those fields
are useful for research and replay, but they are not valid event-time ML
features.

Excluded from Phase 2:

| field/pattern | reason |
|---|---|
| `ed.did_all_confirm_by_window_end` | Set only after checking the rest of the current period. |
| `ed.later_confirmations*` | Direct list/count of laggers that confirmed after event fire. |
| `ed.divergence_duration_seconds` | Derived from the last later confirmation timestamp. |
| `ed.symbol_states.*.broke_high` / `broke_low` | For laggers, this can flip only after event fire. |
| `ed.symbol_states.*.high_break_*` / `low_break_*` | Forward break timestamp/price for laggers. |

Kept:

| field/pattern | reason |
|---|---|
| `ed.symbol_states.*.reference_high` / `reference_low` | Prior-period reference levels, knowable before event fire. |
| `ed.first_break_*` | The event fires on this break. |
| `ed.lagging_symbols_at_break__len` | Known at the event's break candle. |
| `ed.confirming_symbols_at_break__len` | Known at the event's break candle. |

## Reviewed detectors with no Phase 2 excludes

| detector | event-time assessment |
|---|---|
| `psp` | Per-symbol candle states are from the PSP candle that confirms the event. |
| `fvg` | Three-candle gap data is known when candle 3 confirms the event. |
| `ob` | Walks forward to find confirmation, but the event itself is emitted at the confirmation candle. Confirmation candle fields are known at event fire. |
| `sweep` | Emits at the manipulation/sweep candle; stored reference and sweep candle fields are event-time known. |
| `disp` | Rolling mean explicitly shifts by one bar; displacement candle fields are known at the event candle. |
| `swing` | Uses right-side bars to confirm the pivot and stores `knowable_ts_utc`; no post-knowable forward outcome fields are used as model features. |
| `eql` | Joins already-confirmed swing pivots and emits when the current pivot makes the equal-level cluster knowable. |
| `ft` | Emits after the first-third range is complete; rest-of-period behavior lives in outcomes, not `event_data`. |
| `orb` | Emits when the opening range has completed; later breakouts live in outcomes. |
| `tp` | Whole-period classifier. `bar_end_utc` is the parent start, but `parent_period_end_utc` is the knowability point. Phase 2's chronological split is by year, not an intraperiod trading simulation. |
| `vp` | Whole-period volume/VWAP profile. Like `tp`, fields are complete-period descriptors with `parent_period_end_utc` as knowability point. |

## Notes

- The audit intentionally does not modify detector code. The within-period
  enrichment is valid for non-ML research use.
- Phase 2 now excludes only the SMT post-fire fields while keeping prior-period
  reference levels.
- Any future detector that emits before its analysis window is complete should
  either put forward descriptors in `outcomes` or add detector-specific ML
  exclusions here and in `baseline_per_detector.py`.
