# Codex handoff: SMT leakage fix + Phase 3 composite model

## Context

BacktestStation research lab is a feature DB for training local AI on
futures patterns. 12 detectors / 12 outcome computers / 603K events /
99.6% real outcome coverage. **Zero look-ahead is a hard rule** (per
`backend/.claude/feedback_zero_lookahead.md` and the audit script at
`backend/scripts/audit_lookahead.py`).

Today Claude built the ML pipeline (Phases 1 & 2) and ran the first
screening pass. The screening surfaced two issues that need fixing
before we can trust results:

1. **SMT feature leakage** (urgent): one label hit AUC 1.0, which is
   leakage from within-period event_data enrichment fields filled in
   by the detector after the event fires.
2. **Phase 3 — composite cross-detector model** is the next planned
   step, but should be done AFTER the leakage fix lands and the
   look-ahead audit is extended.

## Task 1 (must do): Fix SMT feature leakage

### Where the bug is

`backend/scripts/ml/baseline_per_detector.py` — function
`_feature_columns()` picks features for ML training. It correctly
excludes all `oc.*` columns (outcomes), but it includes `ed.*` columns
(event_data) wholesale. For the `smt_htf_reference_divergence`
detector, several `ed.*` fields are **enriched within the period by
walking forward**, i.e. they are NOT knowable at the event's actual
firing timestamp.

Concrete leakage offenders (visible in
`docs/ML_BASELINE.md` top-features for SMT labels):

- `ed.did_all_confirm_by_window_end` (top feature; binary "did all
  symbols eventually confirm by period close")
- `ed.later_confirmations__len` (count of post-event confirmations)
- `ed.symbol_states.<sym>.broke_high` / `broke_low` (whether other
  symbols broke their reference, set after walking the rest of the
  period)
- `ed.symbol_states.<sym>.high_break_price` /
  `low_break_price` / `high_break_ts` / `low_break_ts` (price/time
  of later breaks)

Other detectors may or may not have similar within-period enrichment
— audit each.

### Fix scope

1. **Edit `_feature_columns()`** to accept a per-detector excluded
   set of prefixes/columns. Apply for SMT:
   ```
   "smt": [
       "ed.did_all_confirm_by_window_end",
       "ed.later_confirmations",
       "ed.symbol_states",  # broad — drops the entire nested struct
   ]
   ```
   Be careful: dropping all of `ed.symbol_states.*` removes
   `ed.symbol_states.<sym>.reference_high` and `reference_low`, which
   ARE knowable at event time (they come from the PRIOR period).
   Either keep those two specifically, or accept the loss for v1.

2. **Audit other detectors' event_data for the same pattern.** Check
   the source (`backend/app/research/detectors/*.py`) for any
   detector that records info after walking forward through the
   period. Document findings in
   `docs/ML_BASELINE_LEAKAGE_AUDIT.md`. Apply per-detector excludes
   as needed.

3. **Re-run** `backend/scripts/ml/baseline_per_detector.py`. Verify
   the SMT row no longer shows AUC 1.0. Append a note to the existing
   `docs/ML_BASELINE.md` (or regenerate it) calling out the fix.

### Acceptance criteria

- SMT labels' lgb_test_auc all between 0.5 and 0.85 (anything > 0.85
  is highly suspect on n_train < 3000; verify by inspecting top
  features)
- No `ed.*` field appearing as a top-10 feature is "set by walking
  forward past the event timestamp"
- Re-run output written to `docs/ML_BASELINE.md`
- `pytest backend/tests/` still green (you shouldn't be touching
  tested code; this is script-level)

### Constraints

- Do NOT modify detector code — the within-period enrichment is by
  design for non-ML uses. Only the ML feature selection should
  exclude it.
- Zero look-ahead is law (`feedback_zero_lookahead.md`). The point of
  this fix IS enforcement of that.
- Keep changes scoped to `backend/scripts/ml/baseline_per_detector.py`
  + the audit doc. Don't refactor the rest of the script.

## Task 2 (optional, do after Task 1): Extend look-ahead audit script

`backend/scripts/audit_lookahead.py` currently only checks `outcomes`
fields. Extend it to also check `event_data` fields against
"knowable at event timestamp" — specifically flag fields whose
documented semantics say "filled in later." A heuristic:

- For each (detector, event_type), maintain a list of "fill-after-fire"
  field name patterns
- Sample N events; for each, check if event_data[field] has a value AND
  if the field's documented meaning requires walking forward

This is a soft check — the real source-of-truth is the detector code.
But a list-based audit would catch regressions.

## Task 3 (after Task 1): Phase 3 — composite cross-detector model

Goal: train a single model on the validated low-side anchor cell to
test whether ML rediscovers (or improves on) the manual 89% N+1 cell
we found earlier.

Anchor: low-side `previous_day_smt` events.
Label: `oc.next_period.thesis_confirmed_strict` (or
`thesis_confirmed_or_n+2_confirmed` — Codex may add the n_plus_2 OR
variant as a separate label).
Features:
- Filtered SMT event_data (post-leakage-fix)
- Chronological metadata
- All `xd.has_<other>_in_24h` flags (already in the feature matrix)
- Optional: per-other-detector ACTIVE flags by side + timeframe
  (e.g., `xd.has_fvg_bullish_4h_in_24h`) — requires re-running
  Phase 1 with finer flags. NICE-TO-HAVE, not required for v1.

Chronological split: same as Phase 2 (train ≤ 2022 / val 2023 /
test ≥ 2024).

Script: `backend/scripts/ml/phase3_composite_anchor.py`. Output to
`docs/ML_PHASE3.md` with:
- Per-symbol breakdown (NQ vs ES vs YM)
- LightGBM feature importance
- Comparison to the manual 89% cell: did the model find it? Did it
  find better?
- A small calibration plot (predicted prob vs actual rate)

### Acceptance criteria

- Test AUC printed in the doc
- Top-20 feature importance listed
- Comparison cell: model's top-decile of test predictions vs the
  manual 89%-cell predictions — overlap %, agreement rate
- pytest green

## Files to reference

- `backend/scripts/ml/build_feature_matrix.py` — Phase 1
- `backend/scripts/ml/baseline_per_detector.py` — Phase 2 (where the fix lives)
- `backend/scripts/walk_forward_oos.py` — chronological-split discipline
- `backend/scripts/audit_lookahead.py` — current look-ahead audit
- `docs/ML_BASELINE.md` — Phase 2 output
- `data/ml/features/*.parquet` — built feature matrices
- `backend/.claude/feedback_zero_lookahead.md` — the rule
- `backend/.claude/feedback_database_first.md` — strategic frame
- `backend/.claude/feedback_wide_reach_data.md` — recording convention
- `data/meta.sqlite` — main DB (read-only for this task)

## How to verify when you're done

```bash
cd C:\Users\benbr\BacktestStation\backend
pytest tests/ -q                              # green
python scripts/ml/baseline_per_detector.py    # no SMT AUC=1.0
python scripts/ml/phase3_composite_anchor.py  # Phase 3 output
```

Then point me at `docs/ML_BASELINE.md` and `docs/ML_PHASE3.md` and
let me decide next steps.
