# ML Data Location Guide

_Generated 2026-05-12._

This repo has three main ML data layers.

## 1. Raw Feature Tables

Path:

`data/ml/features/`

These are per-concept event tables. They are closest to the detector output.

Examples:

- `data/ml/features/fvg.parquet`
- `data/ml/features/sweep.parquet`
- `data/ml/features/tp.parquet`
- `data/ml/features/vp.parquet`
- `data/ml/features/ob.parquet`

Use these when improving the database or rebuilding anchors.

Do not start strategy work here unless you know the timing rules, because these files include raw event/outcome fields before the safer snapshot packaging.

## 2. Audited Anchor Matrices

Path:

`data/ml/anchors/`

These are the main files the other PC should use.

An anchor matrix means:

- one row per event/snapshot
- features are what the model is allowed to know at that time
- labels are future outcomes
- schema JSON explains feature columns and label columns
- audit docs check basic zero-lookahead invariants

Best current strategy-lab candidates:

- `data/ml/anchors/fvg_snapshots_xctx_fvggeom.parquet`
- `data/ml/anchors/sweep_snapshots_xctx_fvggeom.parquet`
- `data/ml/anchors/tp_snapshots_xctx_fvggeom.parquet`
- `data/ml/anchors/smt_previous_day_snapshots_xctx_fvggeom.parquet`

Each should travel with its matching schema:

- `*.schema.json`

Examples:

- `data/ml/anchors/fvg_snapshots_xctx_fvggeom.schema.json`
- `data/ml/anchors/sweep_snapshots_xctx_fvggeom.schema.json`

## 3. Context Tables

Path:

`data/ml/context/`

These are intermediate context layers that were merged into anchor matrices.

Examples:

- `data/ml/context/fvg_fvg_geometry_context.parquet`
- `data/ml/context/sweep_fvg_geometry_context.parquet`
- `data/ml/context/tp_fvg_geometry_context.parquet`
- `data/ml/context/smt_previous_day_fvg_geometry_context.parquet`

Usually the other PC does not need these directly, because the useful columns are already merged into the anchor matrices.

## Result Files

Path:

`data/ml/anchors/`

Leaderboard files show one train/validation/test split:

- `*_leaderboard*.csv`
- `*_leaderboard*.parquet`

Walk-forward files show year-by-year validation:

- `*_walk_forward*_summary.csv`
- `*_walk_forward*_folds.csv`

For strategy research, prefer walk-forward summaries over leaderboard-only results.

## Docs To Read First

Start here:

- `docs/ML_DATASET_CATALOG.md`
- `docs/ML_DATA_LOCATION_GUIDE.md`
- `docs/ML_FVG_GEOMETRY_CONTEXT.md`
- `docs/ML_VP_V2_LABELS.md`

Then concept/model reports:

- `docs/ML_SNAPSHOT_LEADERBOARD_FVG_FVGGEOM.md`
- `docs/ML_SNAPSHOT_WALK_FORWARD_FVG_FVGGEOM.md`
- `docs/ML_SNAPSHOT_WALK_FORWARD_SWEEP_FVGGEOM.md`
- `docs/ML_SNAPSHOT_WALK_FORWARD_TP_FVGGEOM.md`
- `docs/ML_SNAPSHOT_WALK_FORWARD_SMT_FVGGEOM.md`

## Simple Rule For The Other PC

Use these first:

1. `data/ml/anchors/fvg_snapshots_xctx_fvggeom.parquet`
2. `data/ml/anchors/sweep_snapshots_xctx_fvggeom.parquet`
3. `data/ml/anchors/tp_snapshots_xctx_fvggeom.parquet`
4. `data/ml/anchors/smt_previous_day_snapshots_xctx_fvggeom.parquet`

Do not use labels as features. Labels start with:

`label.`

Do not use metadata as model features unless the schema says so. The schema's `feature_columns` list is the safe source of truth.

## Plain English

If the other PC wants to train/test strategies, it should load an anchor parquet and its schema JSON.

The parquet has the rows.

The schema tells it:

- which columns are features
- which columns are labels
- what anchor/concept the rows came from
- what snapshot timing rules were used

The docs explain what the results mean.
