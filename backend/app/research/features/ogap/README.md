# Opening Gap Levels

> NDOG/NWOG gap zones recorded at the moment a new day or week opens away from the prior close.

## What It Is

Opening gaps are support/resistance context levels:

- `ndog`: new day opening gap, built from current Globex day open versus previous Globex day close.
- `nwog`: new week opening gap, built from current Globex week open versus previous Globex week close.

Each event stores the gap zone, midpoint, size, direction, previous close, and current open. The event is knowable at the gap open. Fill and reaction outcomes are future labels only.

## Where The Code Lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/opening_gap_levels.py` |
| Outcomes | `backend/app/research/outcomes/opening_gap_reactions.py` |
| Batch outcome backfill | `backend/scripts/backfill_opening_gap_outcomes.py` |
| Feature matrix | `data/ml/features/ogap.parquet` |
| Snapshot matrix | `data/ml/anchors/opening_gap_snapshots_xctx_gapctx.parquet` |
| Gap-memory context | `backend/scripts/ml/build_opening_gap_context.py` |
| Tests | `backend/tests/test_opening_gap_levels.py` |
| Live stats | `./stats.md` |

## What The Event Records

- Gap high, low, midpoint, size, and direction.
- Current open and previous close.
- Gap open timestamp used as the model feature cutoff.
- Event type split between daily gaps and weekly gaps.

## What The Outcomes Record

Outcome `v2` keeps the original fill labels and adds universal reaction labels:

- Filled, unfilled, midpoint touch, and close-through timing.
- Final close inside, above, or below the gap zone.
- Took gap high/low, one-sided takes, and swept-both-sides labels.
- Held-above, held-below, and rejected-back-inside labels.
- First-bar impulse and first-move reversal labels.

## Leakage Notes

Do not feed `oc.*` or `label.*` columns to a model. The safe ML path is the snapshot matrix, where `asof.feature_cutoff_ts` equals `ed.gap_open_ts_utc`, and gap-memory context only uses gaps created before that cutoff.

Current audit: `docs/ML_SNAPSHOT_AUDIT_OPENING_GAP_XCTX_GAPCTX.md`.

## How To Refresh

```powershell
python backend/scripts/backfill_opening_gap_outcomes.py --force
python backend/scripts/ml/build_feature_matrix.py --detectors opening_gap_levels
python backend/scripts/ml/build_generic_anchor_snapshots.py --anchors ogap
python backend/scripts/ml/build_cross_concept_context.py --matrix data/ml/anchors/opening_gap_snapshots.parquet --schema data/ml/anchors/opening_gap_snapshots.schema.json --output data/ml/anchors/opening_gap_snapshots_xctx.parquet --schema-output data/ml/anchors/opening_gap_snapshots_xctx.schema.json --context-output data/ml/context/opening_gap_cross_concept_context.parquet --exclude-anchor-short ogap
python backend/scripts/ml/build_opening_gap_context.py --matrix data/ml/anchors/opening_gap_snapshots_xctx.parquet --schema data/ml/anchors/opening_gap_snapshots_xctx.schema.json --output data/ml/anchors/opening_gap_snapshots_xctx_gapctx.parquet --schema-output data/ml/anchors/opening_gap_snapshots_xctx_gapctx.schema.json --context-output data/ml/context/opening_gap_opening_gap_context.parquet
python backend/scripts/ml/audit_snapshot_matrix.py --matrix C:\Users\benbr\BacktestStation\data\ml\anchors\opening_gap_snapshots_xctx_gapctx.parquet --schema C:\Users\benbr\BacktestStation\data\ml\anchors\opening_gap_snapshots_xctx_gapctx.schema.json --doc C:\Users\benbr\BacktestStation\docs\ML_SNAPSHOT_AUDIT_OPENING_GAP_XCTX_GAPCTX.md
```
