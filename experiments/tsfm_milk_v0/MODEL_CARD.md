# Model Card — tsfm_milk_v0

**Version:** 0
**Status:** Not yet trained (planning phase)
**Owner:** Ben Brainard

## Intended use

Produce calibrated directional probability vectors (up / down / flat) for ES/NQ/YM/RTY at 5 forward horizons (15m, 30m, 1h, 90m, 4h). Outputs feed a separate v1 sizing/risk layer that runs a single strategy across multiple copy-traded prop-firm accounts.

## Out-of-scope (v0)

- Sizing decisions / contract count
- Order placement
- Engine integration (Strategy.on_bar consumption)
- Live trading
- Account-level risk management

## Inputs

- 8 years of 1-minute OHLCV bars (`D:/data/processed/bars/timeframe=1m/`)
- 4 symbols: ES.c.0, NQ.c.0, YM.c.0, RTY.c.0 — continuous, unadjusted
- 32 multivariate channels per timestamp:
  - 28 per-symbol (7 fields × 4 symbols): log_return, hl_range_pct, co_pct, log_volume, log_trade_count, vwap_dev_pct, realized_vol_60
  - 4 cross-asset derived: NQ/ES log-ratio z, RTY/ES log-ratio z, basket mean return, basket dispersion
- Lookback: 240 minutes (4h) per anchor row
- RTH-only anchor sampling: 13:30–20:00 UTC

## Outputs

For each anchor row (symbol-agnostic input, per-symbol per-horizon output):

```
proba["h_15m"]:  (N, 4_symbols, 3_classes)
proba["h_30m"]:  ...
proba["h_60m"]:  ...
proba["h_90m"]:  ...
proba["h_240m"]: ...
```

3 classes: `up` / `down` / `flat`, where threshold is ±0.5σ of rolling 60-min realized vol per symbol.

## Models (v0 ladder)

| Model | Role | Params | Fine-tuning |
|---|---|---|---|
| NaiveBaseline | sanity floor | — | none — marginal class freq |
| LightGBMBaselineForecaster | strong baseline | — | per (symbol, horizon) head |
| **TTMForecaster** (v0 primary) | TSFM | 1–5M | fine-tune on train fold |
| MoiraiForecaster (v0.5) | TSFM challenger | ~14M | fine-tune on train fold |

All implement the `forecaster.Forecaster` ABC.

## Training data

- Universe: 2018-05-01 → 2026-02-27 (selection)
- Final untouched holdout: 2026-03-01 → 2026-05-21
- 6-fold walk-forward expanding window
- 1-hour embargo between train/val and val/test
- Purge: drop rows whose label window crosses into val/test

## Performance metrics

Not yet trained. Kill / ship thresholds in [`PLAN.md`](PLAN.md) §5.

## Hard kill criteria

- ECE > 0.15 at any horizon (calibration broken)
- Net R ≤ 0 at every probability threshold and every horizon (no economic edge)
- Accuracy beats baseline only on 1 of 6 folds (regime-fragile)

## Limitations / known risks

- **Continuous-contract roll artifacts.** `.c.0` symbols are unadjusted; roll boundaries can create fake returns. Mitigation: exclude roll days from label windows (handled in build_dataset.py).
- **Regime narrowness in recent data.** Last 1-2 years may not include a real vol spike comparable to 2020/2022. Mitigation: report fold-by-fold lift, not just aggregate.
- **TSFMs vs LightGBM on financial data.** Published evidence does NOT show TSFM dominance on intraday futures. Expectation calibration: v0 may not beat LightGBM, and that's a real result, not failure.
- **Calibration drift.** Probability calibration can degrade as the regime shifts. Mitigation: report ECE per fold, monitor for trend.
- **Asset synchronization is learned, not enforced.** If the model never picks up the lead-lag relationships, that's a model-capacity issue. Mitigation: explicit cross-asset derived channels in input (NQ/ES log-ratio, basket dispersion).

## Update / retrain cadence

Not yet defined. Initial proposal: monthly retrain on rolling 8-year window once v0 ships.

## Restrictions / safety

- v0 outputs are **probabilities only.** Must never trigger orders directly.
- v0 does NOT include cost-aware sizing. Live deployment without a v1 sizing/risk layer is prohibited.
- Calibration must be re-verified before any live shadow deployment.
