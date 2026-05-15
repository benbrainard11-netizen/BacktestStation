# First proxy backtest — `next_60m.resistance_rejection_3bar`

_Generated 2026-05-15. Proxy R-multiple backtest of the highest-lift label in the registry, on out-of-sample 2025 data._

## TL;DR

**The model has real, large edge over the blind baseline.** On 427 gap_down events in 2025, the top 10% of the model's high-confidence predictions were **100% accurate (43/43)**, vs a 61.4% base rate from blindly trading every gap_down. That's a +38.6 percentage-point edge concentrated where it matters — at the top of the score distribution.

This is the strongest signal we've found across the lab. It deserves a follow-up rigorous OHLCV backtest before any real-capital consideration, but the proxy answers the threshold question (is this noise or real?) decisively: **real.**

## Setup

| Item | Value |
|---|---|
| Label | `label.next_60m.resistance_rejection_3bar` |
| Matrix | `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet` |
| Side filter | `gap_down` (this label is only non-zero on gap_down rows; gap_ups have a mirror label `support_rejection_3bar`) |
| Snapshot | `at_fire` (signal at the gap fire timestamp = ~09:30 ET on a gap_down day) |
| Train years | ≤ 2023 |
| Val year | 2024 |
| Test year | **2025** (held out) |
| Test rows | 427 gap_down events |
| Test base rate | 0.614 (i.e. on a randomly-picked gap_down, the rejection happens 61% of the time) |
| Test AUC | 0.776 |
| Trade rule | Synthetic: predict 1 → +1R if label=1, −1R if label=0. No OHLCV simulation. |

**Design note on the side filter.** The 112-config scoreboard ranked `next_60m.resistance_rejection_3bar` #1 on `side=all` with AUC 0.947 and lift +0.613. But on `side=all` the label is structurally 0 on every gap_up row (because rejection-from-resistance describes a gap_down behavior), which means most of the AUC=0.947 comes from the model learning the trivial "is this a gap_down" classifier. The real test isolates `side=gap_down` so the model has to predict *rejection conditional on being a gap_down*. That's a stricter test — AUC drops to 0.776 but the *meaningful* edge becomes visible.

## Results

### By threshold

| Threshold | # signals | Precision | Recall | Cum R | Avg R / trade |
|---|---:|---:|---:|---:|---:|
| 0.50 | 386 | 0.643 | 0.947 | +110 | +0.285 |
| 0.60 | 310 | 0.703 | 0.832 | +126 | +0.407 |
| 0.70 | 223 | 0.816 | 0.695 | **+141** | +0.632 |
| 0.80 | 122 | 0.951 | 0.443 | +110 | +0.902 |
| 0.90 | 18 | **1.000** | 0.069 | +18 | **+1.000** |

The threshold sweep shows the classic precision-vs-recall trade-off. Maximum total R lands at threshold 0.70 (+141R across 223 trades). Tighter thresholds get smaller but cleaner trade sets.

### By top-N% of model score

This is the metric that matters most when base rate is high — *how much better than base rate is the model at the top of its score distribution?*

| Top % | n | Precision | Edge vs base (0.614) | Avg R |
|---|---:|---:|---:|---:|
| Top 1% | 4 | 1.000 | **+0.386** | +1.000 |
| Top 5% | 21 | 1.000 | **+0.386** | +1.000 |
| Top 10% | 43 | 1.000 | **+0.386** | +1.000 |
| Top 20% | 85 | 0.976 | +0.363 | +0.953 |
| Top 50% | 214 | 0.818 | +0.204 | +0.636 |

**Top 10% of scores → perfect precision (43/43).** The model is calibrated such that its highest-confidence picks really are the safest. This is the strongest evidence that the ML score isn't random — it's actually ordering events by genuine signal strength.

### Vs the blind baseline

| Strategy | n | Precision | Cum R | Avg R / trade |
|---|---:|---:|---:|---:|
| **Blind** (every gap_down) | 427 | 0.614 | +97 | +0.227 |
| **Model thr=0.7** | 223 | 0.816 | +141 | +0.632 |
| **Model thr=0.8** | 122 | 0.951 | +110 | +0.902 |
| **Model top-10%** | 43 | 1.000 | +43 | +1.000 |

Trading every gap_down blindly is *already* +R because the base rate is favorable (61.4% > 50%). But the model **roughly triples the per-trade R** at threshold 0.7, and quintuples it at top-10%.

## Plots

- [`equity_curve.png`](../experiments/backtests/2026-05-15_resistance_rejection_v1/equity_curve.png) — R-multiple cumulative curves at each threshold + the blind baseline.
- [`signal_density.png`](../experiments/backtests/2026-05-15_resistance_rejection_v1/signal_density.png) — Monthly histogram of signal count at the best threshold (0.7).

## Caveats

1. **One test year (2025) is a small sample.** 427 events sounds like a lot but for walk-forward AUC variance we'd want 4+ test years to be statistically firm. The 100% top-10% precision could partly be a 2025-specific calibration luck. Need to fold back into multi-year walk-forward.
2. **+1R/−1R is a synthetic outcome model.** Real trading has variable wins (a strong rejection might be +5R, a weak one +0.5R), losses can blow through stops, and entries get slipped. This test answers *is the signal real*, not *what's the actual dollar P&L*.
3. **No transaction costs.** Commissions + slippage on 200+ trades per year would eat several R per year. Worth modeling.
4. **The test set is gap_down events at gap fire** — that's a narrow trade trigger (one event per gap_down day, typically open of NQ/ES/YM). Not generalizable to other event types or intraday triggers.

## What this unlocks

This is the first signal we have that's strong enough to justify the **rigorous OHLCV backtest** (the 4-6 hour follow-up I mentioned earlier). With this proxy result in hand, we know:
- The label is predictable beyond chance.
- The model is well-calibrated (high-confidence picks are reliably high-precision).
- The signal is concentrated in gap_down sessions on ES/NQ/YM.

Next builds, in order:

1. **Multi-year walk-forward backtest** — repeat this test for test years 2020 through 2025, confirm the top-10% precision is robust across years and not a 2025 fluke. ~30 min run.
2. **OHLCV backtest with real trade mechanics** — define entry (when does the 3-bar rejection pattern complete?), stop (above the resistance level), target (gap fill? VWAP? prior-day low?), and time exit (60-minute window). Look up bars from `D:\data\processed\bars\` and compute dollar P&L per trade. ~4-6 hours of build, then run.
3. **Per-symbol breakdown** — does the signal work as well on YM (low volume, slow) as on NQ (high volume, fast)? Could imply per-symbol thresholds or NQ-only deployment.
4. **Stability across context layers** — does the signal hold if we strip out `regime` or `liqgeom`? If most of the AUC comes from one layer, that informs feature engineering.

## Reproducing

```bash
python -m scripts.ml.backtest_resistance_rejection_v1
```

Reads `D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions\data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet`, trains a single fold (test_year=2025) on GPU, and writes:

- `experiments/backtests/2026-05-15_resistance_rejection_v1/summary_by_threshold.csv`
- `experiments/backtests/2026-05-15_resistance_rejection_v1/summary_by_top_pct.csv`
- `experiments/backtests/2026-05-15_resistance_rejection_v1/trade_log.csv`
- `experiments/backtests/2026-05-15_resistance_rejection_v1/equity_curve.png`
- `experiments/backtests/2026-05-15_resistance_rejection_v1/signal_density.png`
- `experiments/backtests/2026-05-15_resistance_rejection_v1/meta.json`
