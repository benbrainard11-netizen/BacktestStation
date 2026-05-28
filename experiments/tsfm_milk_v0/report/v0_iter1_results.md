# tsfm_milk_v0 — Iteration 1 Results

Generated: 2026-05-28T02:03:40.946215+00:00

Cells: 1,680
Models: ['lightgbm', 'lightgbm_best_per_cell', 'lightgbm_ensemble', 'lightgbm_tuned', 'naive', 'transformer', 'ttm']

## Pooled metrics (test phase, across folds)

| model | horizon | n_cells | acc | macro_f1 | auc | ece | ic |
|---|---|---|---|---|---|---|---|
| lightgbm | h_15m | 24 | 0.435 | 0.355 | 0.608 | 0.031 | -0.001 |
| lightgbm | h_240m | 24 | 0.432 | 0.264 | 0.571 | 0.037 | 0.018 |
| lightgbm | h_30m | 24 | 0.428 | 0.344 | 0.598 | 0.030 | 0.003 |
| lightgbm | h_60m | 24 | 0.421 | 0.316 | 0.586 | 0.031 | 0.000 |
| lightgbm | h_90m | 24 | 0.419 | 0.294 | 0.576 | 0.033 | 0.012 |
| lightgbm_best_per_cell | h_15m | 24 | 0.435 | 0.356 | 0.608 | 0.030 | -0.001 |
| lightgbm_best_per_cell | h_240m | 24 | 0.431 | 0.277 | 0.565 | 0.035 | 0.009 |
| lightgbm_best_per_cell | h_30m | 24 | 0.428 | 0.343 | 0.599 | 0.032 | 0.002 |
| lightgbm_best_per_cell | h_60m | 24 | 0.422 | 0.319 | 0.587 | 0.029 | 0.001 |
| lightgbm_best_per_cell | h_90m | 24 | 0.419 | 0.298 | 0.574 | 0.032 | 0.010 |
| lightgbm_ensemble | h_15m | 24 | 0.435 | 0.355 | 0.609 | 0.030 | -0.001 |
| lightgbm_ensemble | h_240m | 24 | 0.431 | 0.261 | 0.563 | 0.040 | 0.012 |
| lightgbm_ensemble | h_30m | 24 | 0.430 | 0.346 | 0.601 | 0.031 | -0.002 |
| lightgbm_ensemble | h_60m | 24 | 0.423 | 0.320 | 0.590 | 0.029 | 0.001 |
| lightgbm_ensemble | h_90m | 24 | 0.419 | 0.297 | 0.575 | 0.031 | 0.000 |
| lightgbm_tuned | h_15m | 24 | 0.435 | 0.355 | 0.608 | 0.031 | -0.000 |
| lightgbm_tuned | h_240m | 24 | 0.428 | 0.280 | 0.551 | 0.036 | 0.007 |
| lightgbm_tuned | h_30m | 24 | 0.429 | 0.346 | 0.600 | 0.030 | -0.001 |
| lightgbm_tuned | h_60m | 24 | 0.422 | 0.318 | 0.588 | 0.029 | -0.001 |
| lightgbm_tuned | h_90m | 24 | 0.418 | 0.303 | 0.569 | 0.031 | 0.004 |
| naive | h_15m | 24 | 0.397 | 0.189 | 0.500 | 0.029 | nan |
| naive | h_240m | 24 | 0.422 | 0.197 | 0.499 | 0.039 | nan |
| naive | h_30m | 24 | 0.392 | 0.187 | 0.500 | 0.031 | nan |
| naive | h_60m | 24 | 0.394 | 0.188 | 0.500 | 0.040 | nan |
| naive | h_90m | 24 | 0.400 | 0.190 | 0.500 | 0.041 | nan |
| transformer | h_15m | 24 | 0.423 | 0.325 | 0.594 | 0.030 | 0.011 |
| transformer | h_240m | 24 | 0.430 | 0.272 | 0.568 | 0.045 | 0.002 |
| transformer | h_30m | 24 | 0.420 | 0.316 | 0.585 | 0.030 | 0.012 |
| transformer | h_60m | 24 | 0.417 | 0.317 | 0.577 | 0.028 | 0.012 |
| transformer | h_90m | 24 | 0.422 | 0.313 | 0.572 | 0.031 | 0.023 |
| ttm | h_15m | 24 | 0.415 | 0.254 | 0.598 | 0.085 | 0.014 |
| ttm | h_240m | 24 | 0.429 | 0.228 | 0.573 | 0.062 | -0.024 |
| ttm | h_30m | 24 | 0.410 | 0.248 | 0.591 | 0.082 | 0.017 |
| ttm | h_60m | 24 | 0.411 | 0.250 | 0.582 | 0.070 | 0.013 |
| ttm | h_90m | 24 | 0.414 | 0.242 | 0.576 | 0.070 | 0.003 |

## Economic overlay — HONEST (val-picked threshold applied to test)

For each (model, fold, horizon, symbol):
  1. On VAL: compute economic at thresholds {0.45, 0.50, 0.55, 0.60, 0.65}
  2. Pick the val threshold maximizing `win_rate × mean_R`
  3. Apply that exact threshold to TEST (no peeking)

Slippage: 1 tick/side per round trip. Commission: $1.50/round trip.
R = ticks moved per trade (per-symbol unit — not directly comparable across symbols).

| model | horizon | cells | mean thr | total trades | mean win% | mean R/trade | sum net R | mean DD (R) |
|---|---|---|---|---|---|---|---|---|
| lightgbm | h_15m | 24 | 0.50 | 1,447 | 52.8% | 17.95 | 11611.2 | 707.8 |
| lightgbm | h_240m | 24 | 0.52 | 1,481 | 57.7% | -31.53 | -138534.7 | 7591.0 |
| lightgbm | h_30m | 24 | 0.52 | 1,200 | 46.7% | -3.59 | 2103.8 | 913.8 |
| lightgbm | h_60m | 24 | 0.51 | 1,275 | 46.6% | 43.93 | 39517.4 | 2351.7 |
| lightgbm | h_90m | 24 | 0.52 | 677 | 58.6% | 31.81 | 39375.9 | 1131.4 |
| lightgbm_best_per_cell | h_15m | 24 | 0.50 | 1,375 | 55.2% | 26.04 | 32379.9 | 941.5 |
| lightgbm_best_per_cell | h_240m | 24 | 0.51 | 3,072 | 48.5% | -27.59 | -121127.7 | 9256.9 |
| lightgbm_best_per_cell | h_30m | 24 | 0.50 | 1,554 | 45.7% | -27.27 | -2309.1 | 1368.6 |
| lightgbm_best_per_cell | h_60m | 24 | 0.50 | 1,566 | 50.2% | 61.55 | 26199.8 | 3054.5 |
| lightgbm_best_per_cell | h_90m | 24 | 0.52 | 1,295 | 57.3% | 18.14 | 20149.0 | 2529.1 |
| lightgbm_ensemble | h_15m | 24 | 0.50 | 1,915 | 55.8% | 20.36 | 19054.0 | 541.1 |
| lightgbm_ensemble | h_240m | 24 | 0.51 | 1,536 | 41.1% | -81.01 | -148916.2 | 8145.7 |
| lightgbm_ensemble | h_30m | 24 | 0.52 | 1,018 | 54.2% | -0.44 | 8136.5 | 641.2 |
| lightgbm_ensemble | h_60m | 24 | 0.52 | 780 | 54.4% | 109.56 | 28597.6 | 1177.0 |
| lightgbm_ensemble | h_90m | 24 | 0.53 | 1,588 | 55.1% | 66.73 | 42230.9 | 2779.6 |
| lightgbm_tuned | h_15m | 24 | 0.51 | 1,287 | 58.3% | 32.59 | 26316.2 | 763.8 |
| lightgbm_tuned | h_240m | 24 | 0.52 | 4,174 | 55.9% | 16.71 | -102176.6 | 8300.8 |
| lightgbm_tuned | h_30m | 24 | 0.52 | 1,079 | 57.1% | 44.00 | 2408.6 | 973.6 |
| lightgbm_tuned | h_60m | 24 | 0.50 | 1,194 | 50.8% | 35.28 | 39300.0 | 2291.2 |
| lightgbm_tuned | h_90m | 24 | 0.51 | 2,122 | 61.7% | 53.00 | 23894.5 | 3641.5 |
| naive | h_15m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| naive | h_240m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| naive | h_30m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| naive | h_60m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| naive | h_90m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| transformer | h_15m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| transformer | h_240m | 24 | 0.54 | 566 | 41.4% | 5.79 | -57390.0 | 2502.3 |
| transformer | h_30m | 24 | 0.55 | 48 | 68.8% | 17.76 | 852.6 | 37.3 |
| transformer | h_60m | 24 | 0.54 | 262 | 53.1% | 9.97 | 1288.3 | 155.0 |
| transformer | h_90m | 24 | 0.53 | 425 | 30.0% | -1.78 | 1442.3 | 350.3 |
| ttm | h_15m | 24 | 0.54 | 112 | 46.6% | -15.76 | -2774.5 | 344.6 |
| ttm | h_240m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| ttm | h_30m | 24 | 0.54 | 500 | 52.4% | -6.77 | -7777.0 | 980.0 |
| ttm | h_60m | 24 | 0.54 | 783 | 55.4% | -7.30 | -5758.0 | 1851.4 |
| ttm | h_90m | 24 | 0.55 | 340 | 54.4% | -19.04 | -6474.5 | 1305.6 |

### Comparison: honest (val-picked) vs in-sample (test-picked) threshold

Same pooling, but threshold picked on TEST data (the in-sample, biased version).
Difference = the bias from picking threshold with future-leaking information.

| model | horizon | honest sum_net_R | in-sample sum_net_R | bias pct | honest win% | in-sample win% |
|---|---|---|---|---|---|---|
| lightgbm | h_15m | 11611.2 | 11485.2 | -1% | 52.8% | 55.4% |
| lightgbm | h_240m | -138534.7 | -29151.3 | +79% | 57.7% | 52.0% |
| lightgbm | h_30m | 2103.8 | 14773.4 | +602% | 46.7% | 53.7% |
| lightgbm | h_60m | 39517.4 | 36728.0 | -7% | 46.6% | 55.4% |
| lightgbm | h_90m | 39375.9 | 59378.5 | +51% | 58.6% | 73.7% |
| lightgbm_best_per_cell | h_15m | 32379.9 | 9987.7 | -69% | 55.2% | 58.3% |
| lightgbm_best_per_cell | h_240m | -121127.7 | 20043.9 | +117% | 48.5% | 46.2% |
| lightgbm_best_per_cell | h_30m | -2309.1 | 8109.2 | +451% | 45.7% | 54.5% |
| lightgbm_best_per_cell | h_60m | 26199.8 | 38607.6 | +47% | 50.2% | 58.7% |
| lightgbm_best_per_cell | h_90m | 20149.0 | 39597.6 | +97% | 57.3% | 64.4% |
| lightgbm_ensemble | h_15m | 19054.0 | 20271.9 | +6% | 55.8% | 49.6% |
| lightgbm_ensemble | h_240m | -148916.2 | -40792.4 | +73% | 41.1% | 50.8% |
| lightgbm_ensemble | h_30m | 8136.5 | 5602.5 | -31% | 54.2% | 55.9% |
| lightgbm_ensemble | h_60m | 28597.6 | 18773.4 | -34% | 54.4% | 56.9% |
| lightgbm_ensemble | h_90m | 42230.9 | 64100.4 | +52% | 55.1% | 59.6% |
| lightgbm_tuned | h_15m | 26316.2 | 10304.8 | -61% | 58.3% | 58.0% |
| lightgbm_tuned | h_240m | -102176.6 | -51323.5 | +50% | 55.9% | 44.0% |
| lightgbm_tuned | h_30m | 2408.6 | 10835.1 | +350% | 57.1% | 59.0% |
| lightgbm_tuned | h_60m | 39300.0 | 22098.4 | -44% | 50.8% | 55.1% |
| lightgbm_tuned | h_90m | 23894.5 | 41099.2 | +72% | 61.7% | 62.0% |
| naive | h_15m | 0.0 | 0.0 | n/a | nan | nan |
| naive | h_240m | 0.0 | 0.0 | n/a | nan | nan |
| naive | h_30m | 0.0 | 0.0 | n/a | nan | nan |
| naive | h_60m | 0.0 | 0.0 | n/a | nan | nan |
| naive | h_90m | 0.0 | 0.0 | n/a | nan | nan |
| transformer | h_15m | 0.0 | 460.8 | n/a | nan | 75.3% |
| transformer | h_240m | -57390.0 | 3950.8 | +107% | 41.4% | 42.3% |
| transformer | h_30m | 852.6 | 2043.5 | +140% | 68.8% | 76.4% |
| transformer | h_60m | 1288.3 | 880.7 | -32% | 53.1% | 43.8% |
| transformer | h_90m | 1442.3 | 4788.1 | +232% | 30.0% | 45.9% |
| ttm | h_15m | -2774.5 | -3961.8 | -43% | 46.6% | 39.0% |
| ttm | h_240m | 0.0 | 531.4 | n/a | nan | 100.0% |
| ttm | h_30m | -7777.0 | -356.8 | +95% | 52.4% | 63.6% |
| ttm | h_60m | -5758.0 | 1629.3 | +128% | 55.4% | 51.0% |
| ttm | h_90m | -6474.5 | 4111.3 | +164% | 54.4% | 79.3% |

**Read:** the HONEST row is what you'd actually realize trading this model walk-forward.
Big positive bias means the in-sample version was cheating heavily.

## Kill criteria (PLAN §5)

- **ship:** ECE ≤ 0.08 at all horizons, accuracy > naive + 2pp at ≥ 3 horizons, IC > 0 in ≥ 4 folds, net R > 0
- **kill:** ECE > 0.15 anywhere, OR net R ≤ 0 at every threshold and horizon