# tsfm_milk_v0 — Iteration 1 Results

Generated: 2026-05-27T21:45:03.211740+00:00

Cells: 480
Models: ['lightgbm', 'naive']

## Pooled metrics (test phase, across folds)

| model | horizon | n_cells | acc | macro_f1 | auc | ece | ic |
|---|---|---|---|---|---|---|---|
| lightgbm | h_15m | 24 | 0.435 | 0.355 | 0.608 | 0.031 | -0.001 |
| lightgbm | h_240m | 24 | 0.432 | 0.264 | 0.571 | 0.037 | 0.018 |
| lightgbm | h_30m | 24 | 0.428 | 0.344 | 0.598 | 0.030 | 0.003 |
| lightgbm | h_60m | 24 | 0.421 | 0.316 | 0.586 | 0.031 | 0.000 |
| lightgbm | h_90m | 24 | 0.419 | 0.294 | 0.576 | 0.033 | 0.012 |
| naive | h_15m | 24 | 0.397 | 0.189 | 0.500 | 0.029 | nan |
| naive | h_240m | 24 | 0.422 | 0.197 | 0.499 | 0.039 | nan |
| naive | h_30m | 24 | 0.392 | 0.187 | 0.500 | 0.031 | nan |
| naive | h_60m | 24 | 0.394 | 0.188 | 0.500 | 0.040 | nan |
| naive | h_90m | 24 | 0.400 | 0.190 | 0.500 | 0.041 | nan |

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
| naive | h_15m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| naive | h_240m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| naive | h_30m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| naive | h_60m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |
| naive | h_90m | 24 | 0.55 | 0 | nan | nan | 0.0 | 0.0 |

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
| naive | h_15m | 0.0 | 0.0 | n/a | nan | nan |
| naive | h_240m | 0.0 | 0.0 | n/a | nan | nan |
| naive | h_30m | 0.0 | 0.0 | n/a | nan | nan |
| naive | h_60m | 0.0 | 0.0 | n/a | nan | nan |
| naive | h_90m | 0.0 | 0.0 | n/a | nan | nan |

**Read:** the HONEST row is what you'd actually realize trading this model walk-forward.
Big positive bias means the in-sample version was cheating heavily.

## Kill criteria (PLAN §5)

- **ship:** ECE ≤ 0.08 at all horizons, accuracy > naive + 2pp at ≥ 3 horizons, IC > 0 in ≥ 4 folds, net R > 0
- **kill:** ECE > 0.15 anywhere, OR net R ≤ 0 at every threshold and horizon