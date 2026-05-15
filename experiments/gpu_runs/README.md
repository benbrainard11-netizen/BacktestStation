# GPU training run outputs

Each subfolder is one `(matrix, label, side, snapshot)` experiment from
`backend/scripts/ml/gpu_train_runner.py`. The convention is
`<date>_<topic>/<side>_<snapshot>/`, e.g.
`2026-05-15_sweep_context_layers/low_at_fire/`.

## What's committed

- `config.json` — full reproducibility payload (matrix sha256, git SHA,
  device info, hyperparameters, seed)
- `metrics_summary.csv` — one row per fold
- `feature_importance.csv` — gain per `(fold, feature)`
- `README.md` — comparison table vs the CPU LightGBM baseline from
  `docs/ML_CONTEXT_LAYER_RESULTS.md`

## What's gitignored

- `predictions.parquet` — per-row test predictions (multi-GB at scale)
- `folds.parquet` — same content as `metrics_summary.csv`, parquet form

Regenerate either locally by re-running the runner with the same
`config.json` arguments.

## Running

```bash
python -m scripts.ml.gpu_train_runner \
  --matrix <export_root>/data/ml/anchors/sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet \
  --schema <export_root>/data/ml/anchors/sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json \
  --label  label.manipulation_range_reaction.range_expanded_2x_manipulation \
  --side   low --snapshot at_fire \
  --output-dir experiments/gpu_runs/2026-05-15_sweep_context_layers/low_at_fire \
  --quick   # smoke test on one fold; drop for the full 6-year walk-forward
```

See `backend/scripts/ml/gpu_train_runner.py` for the full CLI surface.
