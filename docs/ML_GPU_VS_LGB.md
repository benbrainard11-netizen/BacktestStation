# GPU XGBoost vs CPU LightGBM — Sweep at_fire scoreboard

_Generated 2026-05-15. Source runs: `experiments/gpu_runs/2026-05-15_sweep_context_layers/` (8 dirs). Baseline numbers from [ML_CONTEXT_LAYER_RESULTS.md](ML_CONTEXT_LAYER_RESULTS.md)._

## Plain-English takeaway

GPU XGBoost beats CPU LightGBM on 7 of 8 sweep `at_fire` configurations but the average win is only **+0.007 mean AUC** — within the noise band you'd expect from seed and split variance. The real edge is **speed**: 26-60 s per full 6-fold walk-forward on the RTX 5080, versus the hours the CPU sweep needed. Use GPU XGBoost when you want to **explore** (label sweeps, side combos), not because it'll squeeze meaningful AUC out of any single config.

## Scoreboard

Matrix: `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`. Both runners use the same encoding (`pd.get_dummies(dummy_na=True)`) and walk-forward split (`train ≤ test_year−2 / val = test_year−1 / test = test_year`), so the delta isolates device + library.

| Side | Label | CPU LGB mean | GPU XGB mean | Δ mean | CPU min | GPU min | Δ min |
|------|-------|-------------:|-------------:|------:|-------:|-------:|------:|
| low  | range_expanded_2x_manipulation | 0.907 | **0.914** | +0.007 | 0.861 | **0.866** | +0.005 |
| all  | range_expanded_2x_manipulation | 0.903 | **0.913** | +0.010 | 0.830 | **0.866** | +0.036 |
| all  | ob_confirmation.did_confirm    | **0.896** | 0.895 | −0.001 | **0.856** | 0.854 | −0.002 |
| high | ob_confirmation.did_confirm    | 0.894 | **0.901** | +0.007 | 0.873 | **0.879** | +0.006 |
| high | range_expanded_2x_manipulation | 0.887 | **0.900** | +0.013 | 0.800 | **0.823** | +0.023 |
| low  | ob_confirmation.did_confirm    | 0.863 | **0.880** | +0.017 | 0.782 | **0.838** | +0.056 |
| high | swept_reference_reaction.first_bar_down_then_final_up | 0.823 | **0.826** | +0.003 | **0.803** | 0.802 | −0.001 |
| high | swept_level_recovery.level_recovered | 0.792 | **0.794** | +0.002 | **0.747** | 0.743 | −0.004 |

**Aggregate**

| Metric | GPU win rate | Avg delta | Range |
|--------|-------------:|----------:|------:|
| Mean AUC across folds | 7 / 8 | +0.007 | −0.001 … +0.017 |
| Min-fold AUC          | 5 / 8 | +0.015 | −0.004 … +0.056 |

The GPU edge is largest on the weakest CPU configurations (`low/ob_confirmation` +0.017 mean, +0.056 min) and smallest on the strongest. That's mild evidence that XGBoost on GPU is slightly more robust on harder-to-fit configs, but the sample size is tiny.

## Speed

| Runner | Hardware | Per-config 6-fold walk-forward |
|--------|----------|--------------------------------|
| GPU XGBoost (this branch) | RTX 5080, 16 GB | 26 - 60 s |
| CPU LightGBM (baseline)   | benpc CPU       | "hours" for the full sweep (per `snapshot_walk_forward.py` cadence) |

GPU SM utilization tops out at ~50% during fit — the workload (~2.9k features × 8-19k rows per fold) is small relative to the 5080's bandwidth. Larger matrices would likely scale further before hitting GPU bottlenecks.

## Caveats

- 8 configs is not a population. A 7/8 win rate has binomial p ≈ 0.035 against a no-edge null — suggestive but not definitive.
- Per-config fold AUC variance is ~0.05+; a +0.007 mean delta is within that band.
- This compares **runners as built**, not pure XGBoost-on-GPU vs pure LightGBM-on-CPU. Hyperparameter shape is matched but not identical.
- Period-close labels (`at_period_close`) are not tested here — the GPU runner supports them via `--snapshot at_period_close` but the comparison would need matching CPU runs.

## Decision

- Treat GPU XGBoost as the **default training path for label/side/snapshot sweeps** going forward. The speed unlock is real.
- Don't expect quality improvements when re-running a single config that the CPU baseline already scored. The deltas are too small to matter for production decisions.
- Next useful build: **a Fractal-AMD-specific label** (entry-fires → did it hit target before stop?), then re-use this runner against it. That converts the speed advantage into research on a question that actually feeds the live bot, rather than another diagnostic-label sweep.

## Reproducing

```bash
python -m scripts.ml.gpu_train_runner \
  --matrix D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet \
  --schema D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json \
  --label  <label> --side <low|high|all> --snapshot at_fire \
  --output-dir experiments/gpu_runs/2026-05-15_sweep_context_layers/<side>_at_fire_<slug>
```

Each run dir's `config.json` captures the full CLI + matrix sha256 + git SHA for byte-deterministic reruns.
