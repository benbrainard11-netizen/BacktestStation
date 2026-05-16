# OB strict release — GPU walk-forward verification

_Generated 2026-05-16. Verifies 247's `strategy-lab-core-2026-05-16-strict-order-block` release on GPU XGBoost._

## TL;DR

**247's strict order-block release reproduces cleanly on GPU XGBoost.** All 8 configs in the CPU summary CSV verified on GPU within ±0.006 AUC. Mean delta ≈ 0. Release is good to consume.

## Setup

- Matrix: `ob_snapshots_xctx_strict.parquet` (46,331 rows × 898 cols, 3-symbol release matrix)
- Snapshot: `at_fire` (only one in this release)
- Test years: 2020-2025 (6-fold walk-forward, train/val/test offset = 2/1)
- Device: CUDA (RTX 5080), xgboost 3.2.0
- Total runtime: 1.5 min for 8 configs

## Results

| # | Side | Label | GPU AUC | CPU AUC | Δ | top_lift_GPU | base_rate |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | all | `next_60m.ob_broken_through_continuation` | **0.797** | 0.797 | −0.000 | 0.372 | 0.187 |
| 2 | bearish | `next_60m.ob_broken_through_continuation` | 0.793 | 0.794 | −0.001 | 0.367 | 0.193 |
| 3 | all | `next_60m.ob_swept_and_recovered` | **0.798** | 0.793 | +0.005 | 0.139 | 0.054 |
| 4 | bullish | `next_60m.ob_broken_through_continuation` | 0.784 | 0.785 | −0.001 | 0.351 | 0.180 |
| 5 | bullish | `next_60m.ob_swept_and_recovered` | 0.787 | 0.781 | +0.006 | 0.142 | 0.056 |
| 6 | all | `next_240m.ob_broken_through_continuation` | 0.772 | 0.770 | +0.002 | 0.392 | 0.380 |
| 7 | all | `next_60m.ob_failed_immediately` | 0.766 | 0.767 | −0.001 | 0.322 | 0.306 |
| 8 | bearish | `next_240m.ob_broken_through_continuation` | 0.767 | 0.766 | +0.001 | 0.371 | 0.394 |

**All 8 ok, mean |Δ| = 0.002.** GPU and CPU LightGBM are scoring the same patterns.

## What stands out

**`label.strict.next_60m.ob_broken_through_continuation`** is the standout — AUC 0.797 with a healthy 19% base rate and +0.37 top-bucket lift. That's a "directional follow-through" signal: when an order block confirms strictly and then the next 60m extends through it, the model nails it. This is the natural candidate to plug into the v8a portfolio as a **continuation** family alongside the existing rejection labels.

**`ob_swept_and_recovered`** has 0.054 base rate — very rare event. AUC 0.798 means the model identifies it well, but with that base rate the top-bucket precision lift translates to maybe 14% precision absolute. Tradeable in principle but needs the high-precision direction rule.

**`ob_failed_immediately`** at 0.766 AUC, 31% base rate, +0.32 lift — this is the **rejection** version (OB invalidates within 60m). Mirrors the existing OGAP rejection family, just on an OB anchor.

## Implications for v8a portfolio

The current v8a portfolio is 3 OGAP signals on NQ+ES with vol-floored stops and 5×ATR target. Natural extensions:

1. **Add `ob_broken_through_continuation` as a continuation family.** Direction rule: side=bullish → long, side=bearish → short. Same v8a trade-rule shape (vol-floored stops, 5×ATR target, 240 min window).
2. **Add `ob_failed_immediately` as a rejection family** alongside the OGAP rejections. Direction rule: side=bullish → short, side=bearish → long.

But — these are both on the **same OB matrix at two horizons** (`next_60m.ob_broken_through_continuation` and `next_240m.ob_broken_through_continuation`). The consensus filter has the known bug here: multi-horizon labels on the same matrix shouldn't count as independent. So we'd treat OB as **one family** with internal horizon picking, not two independent signals.

## What this doesn't tell us

- **No P&L test yet.** AUC parity confirms the model + features are good, not that the labels translate to tradeable P&L. Need a v9 backtest with OB plugged into v8a's trade-rule shape.
- **Index-only matrix.** This is the 3-symbol release matrix. We don't know if OB strict labels generalize to FX (where the cross-asset edge actually lives — see [ML_CROSS_ASSET_SCREENING_2026_05_16.md](ML_CROSS_ASSET_SCREENING_2026_05_16.md)).
- **Only top 8 configs verified.** 247's summary CSV had 8 entries (some labels overlap by side/horizon). If we want all 10 (5 behaviors × 2 horizons) × multiple sides, that's another sweep.

## Suggested next moves

1. **v9 portfolio test**: add `ob_broken_through_continuation` (continuation family) + `ob_failed_immediately` (rejection family) to the v8a portfolio. Family-level consensus (not label-level — multi-horizon bug). ~15 min compute on benpc.
2. **247 next task**: tick-aware strict-label refactor → unlock FX strict labels. See `docs/BEN_247_PROMPT_2026_05_16_STRICT_FX_AND_VOCAB.md`.
3. **Defer**: extending the strict-label families further on indices. The marginal AUC lift is small (~0.02 per family). The big leverage is cross-asset, not more index families.

## Reproducing

```bash
python -m scripts.ml.ob_strict_walkforward
```

Outputs in `experiments/backtests/2026-05-16_ob_strict_walkforward/`:
- `scoreboard.csv` — GPU vs CPU AUC per config
- `sweep.log` — full run log
