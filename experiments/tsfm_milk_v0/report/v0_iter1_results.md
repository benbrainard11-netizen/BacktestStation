# tsfm_milk_v0 — Iteration 1 Results

Generated: 2026-05-27T21:31:46.856035+00:00

Cells: 40
Models: ['naive']

## Pooled metrics (test phase, across folds)

| model | horizon | n_cells | acc | macro_f1 | auc | ece | ic |
|---|---|---|---|---|---|---|---|
| naive | h_15m | 4 | 0.424 | 0.198 | 0.498 | 0.010 | nan |
| naive | h_240m | 4 | 0.435 | 0.202 | 0.495 | 0.015 | nan |
| naive | h_30m | 4 | 0.416 | 0.196 | 0.498 | 0.008 | nan |
| naive | h_60m | 4 | 0.422 | 0.198 | 0.497 | 0.020 | nan |
| naive | h_90m | 4 | 0.429 | 0.200 | 0.497 | 0.022 | nan |

Kill rule (PLAN §5):
- ship: ECE ≤ 0.08 at all horizons, accuracy > naive +2% at ≥ 3 horizons, IC > 0 in ≥ 4 folds
- kill: ECE > 0.15 anywhere, or net_R ≤ 0 everywhere