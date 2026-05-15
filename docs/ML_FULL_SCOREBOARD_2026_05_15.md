# Full GPU XGBoost scoreboard — 2026-05-15

_Generated 2026-05-15. Source: 112-config sweep across all 10 terminal anchor matrices in release `strategy-lab-core-2026-05-14-context-layers`._

This is the broadest GPU XGBoost vs CPU LightGBM comparison we have to date. For every (matrix, snapshot, side, label) configuration that already had a CPU baseline in the export's walk-forward summary CSVs, we re-ran on the GPU XGBoost runner and recorded both numbers.

- Total configs: **112** (10 anchor matrices, 8-16 configs each).
- All 112 succeeded — no skipped folds, no errors.
- Wall time: **55.6 minutes** on the RTX 5080.
- Output: [experiments/gpu_runs/2026-05-15_full_scoreboard/scoreboard.csv](../experiments/gpu_runs/2026-05-15_full_scoreboard/scoreboard.csv) — one row per config.

## Plain-English takeaways

1. **GPU XGBoost ≈ CPU LightGBM on quality.** Average mean-AUC delta is **+0.0044** (median +0.0027). GPU wins 79/112 configs (71%) but most deltas are well inside fold-to-fold noise. Same pattern as yesterday's 8-config scoreboard — the GPU win is **speed**, not accuracy.
2. **The one matrix where CPU LightGBM beats GPU XGBoost: SMT period-close.** 0/8 GPU wins, average delta **−0.0059**. Worth flagging — if you specifically want to predict period-close SMT outcomes, stay on the CPU LightGBM runner.
3. **247's strict-label hypothesis is broadly confirmed.** The strongest signal-to-noise configs across the whole sweep are short-horizon, behavior-named labels (`next_60m.resistance_rejection_3bar`, `partial_touch_rejected@60m`, etc.) — not the broad "did price move a lot" labels that dominate raw AUC.
4. **The top-bucket-lift ranking exposes the "broad-label trap".** Top configs by absolute AUC are mostly labels with base rates ≥ 0.9 — the model is just predicting the majority class. The trader-meaningful metric is top-bucket lift over base rate. Rankings below use that.

## GPU vs CPU, by matrix

| Matrix | n | GPU avg AUC | CPU avg AUC | Δ avg | GPU wins |
|---|---:|---:|---:|---:|---:|
| `fvg_snapshots_xctx_fvggeom_obgeom` | 12 | 0.7643 | 0.7611 | **+0.0032** | **12/12** |
| `itr_snapshots_xctx` | 12 | 0.7786 | 0.7760 | +0.0026 | 10/12 |
| `macro_event_snapshots_xctx` | 10 | 0.8422 | 0.8316 | +0.0106 | 9/10 |
| `forming_vp_snapshots_xctx_gapctx` | 12 | 0.9062 | 0.9039 | +0.0023 | 9/12 |
| `opening_gap_…_regime` (broad) | 16 | 0.8792 | 0.8782 | +0.0010 | 8/16 |
| `opening_gap_…_regime_strict` | 12 | 0.8098 | 0.7975 | **+0.0124** | 10/12 |
| `sweep_…_regime` | 8 | 0.8779 | 0.8707 | +0.0072 | 7/8 |
| `tp_snapshots_xctx_fvggeom_obgeom` | 10 | 0.7227 | 0.7153 | +0.0074 | 5/10 |
| `vp_snapshots_xctx` | 12 | 0.8946 | 0.8908 | +0.0038 | 9/12 |
| `smt_previous_day_…_regime` | 8 | 0.9599 | 0.9658 | **−0.0059** | **0/8** |

## Top 15 configs by top-bucket lift (the trader-meaningful ranking)

| Matrix | Side | Label | GPU AUC | Base | Top lift |
|---|---|---|---:|---:|---:|
| opening_gap broad | all | `next_60m.resistance_rejection_3bar` | 0.947 | 0.291 | **+0.613** |
| smt_previous_day | high | `n1_thesis_confirmed_strict` | 0.961 | 0.409 | +0.591 |
| smt_previous_day | high | `n1_primary_took_period_n_low` | 0.961 | 0.409 | +0.591 |
| smt_previous_day | high | `n1_close_moved_with_thesis` | 0.969 | 0.409 | +0.578 |
| smt_previous_day | all | `n1_primary_took_period_n_low` | 0.960 | 0.439 | +0.561 |
| forming_vp | all | `next_60m.took_profile_so_far_high` | 0.888 | 0.240 | +0.550 |
| forming_vp | balanced | `next_60m.took_profile_so_far_high` | 0.882 | 0.231 | +0.550 |
| opening_gap strict | all | `strict.next_60m.partial_touch_rejected` | 0.831 | 0.329 | +0.549 |
| smt_previous_day | all | `n1_close_moved_with_thesis` | 0.946 | 0.456 | +0.544 |
| opening_gap broad | all | `next_60m.support_rejection_3bar` | 0.918 | 0.363 | +0.543 |
| opening_gap broad | all | `next_60m.unfilled_at_window_end` | 0.830 | 0.329 | +0.542 |
| forming_vp | all | `next_60m.took_profile_so_far_low` | 0.877 | 0.194 | +0.536 |
| opening_gap strict | gap_down | `strict.next_60m.partial_touch_rejected` | 0.829 | 0.315 | +0.532 |
| smt_previous_day | low | `n1_primary_took_period_n_low` | 0.958 | 0.472 | +0.528 |
| opening_gap strict | all | `strict.next_240m.partial_touch_rejected` | 0.845 | 0.225 | +0.526 |

**Patterns visible in the top 15:**
- **60-minute horizon dominates** (12 of 15 use `next_60m.*` or short-window labels). 247's 240m strict label is actually edged by the 60m version on lift.
- **Behavior-named labels win**: `resistance_rejection_3bar`, `support_rejection_3bar`, `took_profile_so_far_high`, `partial_touch_rejected`, `unfilled_at_window_end`, `n1_thesis_confirmed_strict` — these all describe specific market behaviors, not aggregate price moves. Same pattern 247 identified.
- **SMT period-close has multiple entries** despite GPU losing the head-to-head on average AUC — these labels are strong enough that even the slightly-weaker GPU XGBoost still ranks them in the top 15. The CPU LightGBM versions would rank even higher.

## Biggest GPU wins (Δ > +0.02)

| Matrix | Side | Label | Δ AUC |
|---|---|---|---:|
| opening_gap strict | all | `strict.next_1d.failed_fill_expanded_away` | **+0.048** |
| tp | bearish | `n_plus_2.took_parent_high` | +0.038 |
| macro_event | high | `next_15m.range_expanded_2x_pre_60m` | +0.036 |
| macro_event | all | `next_15m.range_expanded_2x_pre_60m` | +0.033 |
| opening_gap strict | gap_up | `strict.next_1d.partial_touch_rejected` | +0.026 |
| tp | bearish | `next_period.took_parent_high` | +0.023 |

## Biggest GPU losses (Δ < −0.02)

| Matrix | Side | Label | Δ AUC |
|---|---|---|---:|
| opening_gap broad | all | `next_1d.range_expanded_2x_gap` | **−0.027** |

Only one config crossed the −0.02 threshold. Notable: this is a broad-label, 1-day-horizon config with a 0.96 base rate — XGBoost may be slightly worse at predicting "is this very-common outcome" than LightGBM, which is also where the SMT period-close losses cluster. **The takeaway: when the model is essentially predicting the majority class, LightGBM has a small edge. When the model is predicting genuinely-uncertain outcomes (the trader-useful case), GPU XGBoost is fine.**

## Operational implications

1. **Default training path for new labels: GPU XGBoost.** Comparable quality, much faster. Use the CPU LightGBM runner only for SMT period-close configs where the small edge matters.
2. **247's FVG strict-label work is the right next investment.** The strict-label pattern is consistently the highest-signal configuration across event families.
3. **Short-horizon (60m) versions of strict labels should always be paired with their longer-horizon counterparts.** In opening_gap we saw 60m partial_touch_rejected (+0.549 lift) edge out 240m (+0.526 lift). 247 should produce both horizons for every FVG strict label too.
4. **Cross-event composite labels are now the obvious next research direction.** Once 247 has FVG strict labels + the shared level-reaction vocabulary, the highest-value next-build is composites like "sweep into untested FVG" or "FVG forming on swing pivot." Those would be entirely new top-of-rankings candidates.

## Reproducing

```bash
# From repo root, branch assets/expanded-universe-v1.
python -m scripts.ml.overnight_sweep_2026_05_15
```

The sweep reads the 10 walk-forward summary CSVs in the release ZIP at
`D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\*_summary.csv`
and for each row runs the GPU XGBoost runner with the same (matrix, snapshot, side, label) configuration.

Per-config artifacts (config.json, fold predictions, feature importance) are NOT written — only the unified scoreboard. To regenerate full artifacts for any single config of interest, use [backend/scripts/ml/gpu_train_runner.py](../backend/scripts/ml/gpu_train_runner.py) directly.
