# Claude Context: Mira Gate Harness

This is the compact context packet for reviewing the current Mira gate before model expansion.

## Direct Answers

### 1. Is the champion gate frozen?

Yes. The champion gate is frozen.

- `live_engine/engine/gate.py` loads `live_engine/model/mira_structure_smt_final_2026.joblib`.
- It does not fit on the evaluation slice.
- The bundle contains:
  - `model`: sklearn `Pipeline(SimpleImputer(median) -> RandomForestClassifier)`
  - `raw_features`: 139 raw feature names
  - `encoded_columns`: 251 post-one-hot columns
  - `threshold`: frozen prev-q75 threshold, documented as `0.5818010299926861`
- `Gate.score()` only encodes rows and calls `model.predict_proba`.
- `Gate.passes()` applies `score >= threshold`.

Relevant file:
- `live_engine/engine/gate.py`

Harness usage:
- `experiments/mira_gate_harness/harness.py` imports `gate as G`.
- `--eval-champion` creates `G.Gate()`, scores the OOS dataset, and evaluates against `gate.threshold`.
- No fit occurs for `champion_frozen`.

Challenger behavior is separate:
- `train_challenger()` in `harness.py` trains a new `RandomForestClassifier` on the named train window.
- Challenger modes are currently `retrain_same` and `drop_smt`.

### 2. What is the label?

The harness label is:

`target.60m.extreme_hold_move`

In `experiments/mira_gate_harness/harness.py`, `build_dataset()` copies that pipeline-generated target into `df["label"]`.

The target is produced by:

`live_engine/vendor/bs_mira/mira_trigger_v0/build_trigger_candidates.py::_target_features`

Definition:

- Look forward from `trigger_ts.floor("min")` to `trigger_ts + 60 minutes`.
- For a low-side anchor:
  - `max_away = high.max() - extreme_price`
  - `max_rebreak = extreme_price - low.min()`
  - `rebreak = max_rebreak > 1 tick`
  - success if `not rebreak` and `max_away >= 8 ticks`
- For a high-side anchor:
  - `max_away = extreme_price - low.min()`
  - `max_rebreak = high.max() - extreme_price`
  - `rebreak = max_rebreak > 1 tick`
  - success if `not rebreak` and `max_away >= 8 ticks`

So the label means:

The swept/known extreme holds without more than a 1-tick rebreak, and price moves at least 8 ticks away from that extreme within 60 minutes.

### 3. What does realized-R measure?

`experiments/mira_gate_harness/realized_r.py` computes trade outcome R independent of the model.

It replays live-style entry and exit:

- Uses MBP-1 top-of-book data.
- Entry:
  - long fills at ask when bid >= trigger
  - short fills at bid when ask <= trigger
  - waits up to 10 minutes
- Stop reference:
  - `feed.MBP1Buffer.local_extreme(180s)`
  - passed into `ReclaimTrade.reset_stop()`
- Exit:
  - `trail_2R`
  - max 60-minute hold through live `signal.py`
- Costs:
  - commission = `$3.80`
  - entry slip = 1 tick
  - exit slip = 1 tick for stop/trail/time exits

The gate selects candidates; `realized_r` is then summarized over gated, one-per-opportunity-deduped rows.

### 4. How does evaluation dedupe trades?

In `harness.eval_model()`:

- Score all rows.
- Filter `scores >= threshold`.
- Sort by `trigger_ts_utc`, `trigger_id`.
- Group by `combined.sweep_setup_event_id`.
- Keep the first trigger per opportunity.

This same dedupe appears in `gex_filter_test.py` and `add_tf_smt_test.py`.

### 5. Current cached windows and scoreboard anchors

Cached datasets:

- `jan_oos`: `2026-01-02` to `2026-02-04`, 950 rows, label pos rate 0.3695
- `oos_holdout`: `2026-05-21` to `2026-06-05`, 458 rows, label pos rate 0.441
- `jan_plus`: Jan with added 3m/10m SMT

Scoreboard highlights from `runs/scoreboard.csv`:

- `jan_oos`, champion frozen, deduped realized-R: 138 filled / 139 gated, meanR `+0.456`, win `50.7%`, sumR `+63.0`
- corrected `oos_holdout`, champion frozen after 5m SMT fix: 83 filled / 83 gated, meanR `+0.298`, win `48.2%`, sumR `+24.8`

Interpretation from handoff:

- Base edge is positive but lumpy.
- Jan is strong; corrected recent holdout is still positive but lower.
- Need monthly/rolling OOS slices before adding features.

## Important Gotchas

1. Use the vendored detector path.
   - `live_engine/engine/detect.py` defaults to `live_engine/vendor`.
   - The repo backend detector dropped 5m SMT; the vendored/live copy has it.
   - Missing 5m caused a false degraded-edge read.

2. MBO reads can hang if uncached.
   - `harness.py` patches `build_trigger_candidates.v0._read_mbo_window` with a day-read cache.

3. The model is not GBM.
   - The current frozen artifact is documented as RandomForest inside a sklearn pipeline.

4. Per-asset decomposition is not currently in the harness output.
   - It should be added in the first diagnostic runner.

## Recommended First Diagnostic

Before adding levels/options/GEX:

Build a monthly and rolling-slice diagnostic over the frozen champion:

- Jan 2026
- Feb 2026
- Mar 2026
- Apr 2026
- May 2026
- Jun 1-5 2026
- optional rolling 2-week slices

For each slice, report:

- candidate rows
- label base rate
- AUC
- gated count
- gated label success
- realized-R count
- mean R
- win rate
- sum R
- per-symbol breakdown: ES, NQ, YM, RTY
- drop-one-symbol totals
- drop-Jan cumulative total
- top-decile contribution / concentration if easy

This answers whether the base edge is robust or carried by one month/symbol before expanding the model.

## Files To Read

Primary:

- `experiments/mira_gate_harness/harness.py`
- `experiments/mira_gate_harness/realized_r.py`
- `live_engine/engine/gate.py`
- `live_engine/engine/detect.py`
- `live_engine/vendor/bs_mira/mira_trigger_v0/build_trigger_candidates.py`

Useful context:

- `experiments/mira_gate_harness/EXPANSION_PLAN.md`
- `experiments/mira_gate_harness/README.md`
- `experiments/mira_gate_harness/runs/scoreboard.csv`
- `experiments/mira_gate_harness/gex_filter_test.py`
- `experiments/mira_gate_harness/add_tf_smt_test.py`
