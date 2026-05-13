# ITR - Interval True Range

> Completed daily, weekly, and session range memory. Each event describes one closed interval and labels what the next comparable interval did.

## What It Is

Interval True Range is a regime/context feature, not an entry rule. It records the shape of a completed interval, then asks whether the next interval expands, compresses, trades back through the midpoint, takes the prior high/low, or closes outside the prior range.

Supported modes:

| Mode | Interval |
|---|---|
| `daily_itr` | Completed Globex day |
| `weekly_itr` | Completed Globex week |
| `asia_itr` | Completed Asia session |
| `london_itr` | Completed London session |
| `ny_itr` | Completed NY session |

The detector fires only after the interval closes. That means current interval OHLC, range, true range, wick/body shape, and rolling range comparisons are known at the prediction timestamp.

## Where The Code Lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/interval_true_range.py` |
| Outcomes | `backend/app/research/outcomes/interval_true_range_reactions.py` |
| Batch outcome backfill | `backend/scripts/backfill_interval_true_range_outcomes.py` |
| Feature matrix | `data/ml/features/itr.parquet` |
| Snapshot matrix | `data/ml/anchors/itr_snapshots_xctx.parquet` |
| Tests | `backend/tests/test_interval_true_range.py` |
| Live stats | `./stats.md` |

## What The Event Records

Event fields include:

- Interval OHLC, midpoint, range, body, wick shares, close location, return, true range.
- Previous interval high/low/mid/range and whether the current interval took or closed outside the previous range.
- Rolling prior 1/3/5/10 interval range averages, medians, min/max, range ratios, and expansion/compression flags.
- Next interval start/end timestamps for outcome labeling.

## What The Outcomes Record

The `next_interval` labels include:

- Range expansion/compression versus the anchor interval.
- Took anchor high, took anchor low, touched anchor midpoint.
- Closed above, below, or inside the anchor range.
- Outside continuation up/down.
- Swept both sides.
- First-touch timing for high, low, and midpoint.
- Same-direction or opposite-direction close.

## Leakage Notes

ITR is designed as a completed-interval feature. Do not use the `label.*` / `oc.*` outcome columns as model features. The safe model path is the snapshot matrix, where `asof.feature_cutoff_ts` is `ed.interval_end_utc`.

Current audit: `docs/ML_SNAPSHOT_AUDIT_ITR_XCTX.md`.

## How To Refresh

Typical sequence:

```powershell
python -m app.cli.scan_research_events --detector interval_true_range --mode daily_itr --symbols NQ.c.0 ES.c.0 YM.c.0 --start 2015-01-01 --end 2026-05-08
python scripts/backfill_interval_true_range_outcomes.py
python scripts/ml/build_feature_matrix.py
python scripts/ml/build_generic_anchor_snapshots.py --anchors itr
python scripts/ml/build_cross_concept_context.py --matrix C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots.parquet --schema C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots.schema.json --output C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots_xctx.parquet --schema-output C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots_xctx.schema.json --context-output C:\Users\benbr\BacktestStation\data\ml\context\itr_cross_concept_context.parquet --exclude-anchor-short itr
python scripts/ml/audit_snapshot_matrix.py --matrix C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots_xctx.parquet --schema C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots_xctx.schema.json --doc C:\Users\benbr\BacktestStation\docs\ML_SNAPSHOT_AUDIT_ITR_XCTX.md
```
