# TSFM Milk v0 — Locked Plan

**Status:** scaffolded, no model trained yet
**Version:** 0
**Branch:** `experiments/tsfm-milk-v0`
**Created:** 2026-05-27

Calibrated multivariate cross-asset directional forecaster for ES/NQ/YM/RTY built on a time-series foundation model. End-use case is multi-account copy-traded prop-firm milking — high win rate, highest R:R that preserves the win rate. This document is the locked v0 spec. Anything outside this scope is v0.5+ work.

---

## Decision

**Forecaster:** multivariate TSFM, fine-tuned on 8 years of 1-minute OHLCV bars.
**Output:** per-(symbol × horizon) probability vector over 3 classes (up / down / flat).
**Horizons:** 15min, 30min, 1h, 90min, 4h — all 5 emitted in one forward pass.
**Sizing/risk layer:** out of v0 scope. Lives in v1 (separate plan).

### Why TSFM over GBDT

Modern TSFMs (TTM, Moirai) are designed for **multivariate cross-asset learning** in a single forward pass. Asset synchronization (ES leads NQ, RTY decouples around earnings, etc.) becomes learnable structure rather than hand-engineered features. A tuned LightGBM is our baseline to beat.

### Why not the existing Type A/B framework

The Type B framework relied on labels (OB break / FVG zone_reaction / swing pivot break) that are widely-taught retail concepts. Any edge is likely commodified and / or regime-degraded. We're building a forecaster from raw bars — no detector pre-filter, no retail-concept dependency.

---

## Path

| Stage | Model | Time | Purpose |
|---|---|---|---|
| **v0**   | IBM Granite TTM (TinyTimeMixer, 1–5M params) | ~2 weeks | Baseline pipeline. Fast iteration. |
| **v0.5** | Salesforce Moirai-base (~14M params) | ~3 days | Same data + pipeline, swap model. Compare. |
| **v0.7** | Moirai-large or fine-tuned Chronos-Bolt | conditional | Only if v0.5 shows model-bound lift. |
| **v1**   | Sizing + risk layer | separate plan | Convert probabilities → contracts per account. |
| **v2**   | Live shadow + paper trade | separate plan | 2 weeks shadow before any real account. |

Pipeline is built model-agnostic. Stages 1–4 and 6–7 don't know which model is in stage 5 — defined by `forecaster.Forecaster` ABC.

---

## §1. Inputs (multivariate tensor)

### Data source

Primary: **1-minute OHLCV bars** at `D:/data/processed/bars/timeframe=1m/symbol=<X>/date=<Y>/*.parquet`.

Date range: **2018-05-01 → 2026-05-21** (~8 years). RTY goes back to 2018-05; ES/NQ/YM similar.

**NOT used in v0:** MBO (53 trading days, regime-narrow), MBP-1 (1 year, fine but not needed yet). They re-enter as auxiliary streams in v0.3+ once the bar-only baseline is solid.

### Channel schema (32 channels per timestamp)

Each minute, we build a tensor row containing all 4 symbols and a few derived cross-asset channels.

**Per-symbol channels (7 per symbol × 4 symbols = 28):**
- `{sym}_log_return_1m` = log(close_t / close_t-1)
- `{sym}_high_minus_low_pct` = (high - low) / close
- `{sym}_close_minus_open_pct` = (close - open) / open
- `{sym}_log_volume` = log(1 + volume)
- `{sym}_log_trade_count` = log(1 + trade_count)
- `{sym}_close_vs_vwap_pct` = (close - vwap) / vwap
- `{sym}_realized_vol_60` = stddev(log_return_1m, 60 bars)

**Cross-asset derived channels (4):**
- `nq_over_es_log_ratio` = log(NQ_close / ES_close), z-scored on rolling 60 bars
- `rty_over_es_log_ratio` = log(RTY_close / ES_close), z-scored on 60 bars
- `equity_basket_mean_return_1m` = mean of 4 symbols' log_return_1m
- `equity_basket_dispersion` = std of 4 symbols' log_return_1m

### Lookback window

Default **240 minutes (4 hours)** of history at each prediction timestamp. Configurable per fold in `feature_schema.yaml`.

### RTH filter

Predict only at 1-minute boundaries inside **13:30–20:00 UTC** (09:30–16:00 ET RTH). Globex overnight rows still feed the lookback window (helpful context), but we don't sample decision points there.

---

## §2. Labels — 3-way classification at 5 horizons

Per PLAN §2.2 (user-locked): adaptive threshold `k × σ` where σ is rolling realized vol.

For each anchor row at timestamp t, for each symbol s, for each horizon h ∈ {15m, 30m, 1h, 90m, 4h}:

```
future_return = log(close_{t+h, s} / close_{t, s})
sigma_t       = stddev of close-to-close log_returns over last 60 minutes (per symbol)
k             = 0.5 (locked for v0)

label = up    if future_return > +k * sigma_t
       down   if future_return < -k * sigma_t
       flat   otherwise
```

Expected class distribution: roughly 30/30/40 (up/down/flat) at 15m; closer to 35/35/30 at 4h.

**Reject rules:**
- Drop labels where `future_return` requires a bar outside RTH (e.g., 4h horizon late in session)
- Drop labels where `sigma_t` is null or zero
- Drop labels where any input channel in the lookback window has > 5% missing data

### Tensor shape

For N anchor rows, the output is:

```
inputs : (N, 240, 32)     # lookback × channels
labels : {
    "h_15m":  (N, 4)      # 4 symbols, one class label per symbol
    "h_30m":  (N, 4)
    "h_60m":  (N, 4)
    "h_90m":  (N, 4)
    "h_240m": (N, 4)
}
```

5 horizons × 4 symbols × 3 classes = 60 output dimensions per anchor row.

---

## §3. Walk-forward splits

6-fold expanding window with explicit purge + 1-hour embargo. Final holdout untouched until model + hyperparameter selection is complete.

```
Universe: 2018-05-01 → 2026-05-21
Final holdout: 2026-03-01 → 2026-05-21 (NEVER touched until v0 is locked)

Fold 1: train 2018-05-01 → 2020-12-31, val 2021-01-04 → 2021-01-31, test 2021-02-01 → 2021-04-30
Fold 2: train 2018-05-01 → 2021-04-30, val 2021-05-03 → 2021-05-31, test 2021-06-01 → 2021-08-31
Fold 3: train 2018-05-01 → 2021-08-31, val 2021-09-01 → 2021-09-30, test 2021-10-01 → 2022-04-30
Fold 4: train 2018-05-01 → 2022-04-30, val 2022-05-02 → 2022-05-31, test 2022-06-01 → 2023-04-30
Fold 5: train 2018-05-01 → 2023-04-30, val 2023-05-01 → 2023-05-31, test 2023-06-01 → 2024-12-31
Fold 6: train 2018-05-01 → 2024-12-31, val 2025-01-02 → 2025-01-31, test 2025-02-03 → 2026-02-27
```

Each fold spans different regime mixes:
- Fold 1: post-COVID rally / meme-stock era
- Fold 2: Fed tightening prep
- Fold 3-4: 2022 bear / vol spikes / rate shocks
- Fold 5: 2023-2024 recovery + chop
- Fold 6: 2025 — recent regime, full year

**Embargo:** 1 hour between train/val and val/test windows (longer than 4h max horizon ÷ 4 to avoid leakage from in-flight labels).

**Purge:** drop training rows whose `[ts, ts + 4h]` label window crosses into the val/test windows.

---

## §4. Model interface (the swap point)

All model implementations subclass `forecaster.Forecaster`:

```python
class Forecaster(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def fit(self, *, train_inputs, train_labels, val_inputs, val_labels, **kwargs) -> None: ...

    @abstractmethod
    def predict_proba(self, inputs, ts) -> ForecastBatch: ...

    @abstractmethod
    def save(self, path: Path) -> None: ...

    @classmethod
    @abstractmethod
    def load(cls, path: Path) -> "Forecaster": ...
```

`ForecastBatch.proba` is a dict mapping `"h_15m"`, `"h_30m"`, ..., `"h_240m"` → array shape `(N, 4_symbols, 3_classes)`.

v0 implementations:
- `ttm_forecaster.TTMForecaster` — IBM Granite TTM, the v0 primary
- `baseline_lightgbm.LightGBMBaselineForecaster` — flat-features baseline (handcrafted feature vector → LightGBM per (symbol, horizon))
- `baseline_naive.NaiveBaseline` — predict marginal class frequency from training data (sanity baseline)

v0.5+ implementations:
- `moirai_forecaster.MoiraiForecaster` — Salesforce Uni2TS

---

## §5. Evaluation — calibration is a kill criterion

### Statistical metrics (per fold, per horizon, per symbol)

| Metric | Why |
|---|---|
| **Accuracy** | Sanity — must beat 1/3 floor |
| **Macro-F1** | Class-balanced view |
| **Per-class precision** | If "up" precision = 60% at p > 0.65, that's actionable |
| **ROC-AUC (one-vs-rest)** | Discrimination quality |
| **Brier score** | Calibration + discrimination together |
| **Expected Calibration Error (ECE)** | Are probabilities honest? **Hard kill criterion.** |
| **Reliability diagram** | Visual ECE — saved as PNG per fold |
| **Information Coefficient (IC)** | Rank correlation between predicted P(up) − P(down) and realized return |

### Economic overlay metrics

Convert probabilities to a toy trading sim — does the model lift after costs?

```
Per anchor row, per symbol, per horizon:
  predicted_dir = argmax(p_up, p_down, p_flat)
  if predicted_dir == flat: no trade
  else:
      enter at next bar's open
      exit at +h bars later
      apply slippage: 1 tick for ES, 1 tick for NQ, 1 tick for YM, 1 tick for RTY
      apply commission: $1.50 / contract round-trip
```

Report:
- net_R, mean_R_per_trade, win rate, max DD, MAR ratio
- **Multi-account proxy:** win rate × R:R map at varying probability thresholds (e.g., only trade when max class prob > 0.55 / 0.60 / 0.65). Picks the threshold maximizing win rate × R:R for the v1 sizing layer.

### Kill criteria (v0)

Model ships to v0.5 if (median across 6 folds):
- Accuracy beats naive baseline by ≥ 2% at ≥ 3 horizons
- ECE ≤ 0.08 at all 5 horizons
- IC > 0 at ≥ 4 of 6 folds, ≥ 3 of 5 horizons
- Economic overlay: net_R > 0 after costs at the **best** probability threshold per horizon

Model dies if:
- ECE > 0.15 anywhere (calibration is broken)
- Net_R ≤ 0 after costs at every threshold across all horizons
- Model only outperforms baseline on one fold

---

## §6. Integration (v0)

v0 writes predictions to parquet at `out/predictions/`. No engine integration in v0. The downstream sizing/risk layer (v1) will consume these predictions.

### Prediction schema

```
ts_decision        (timestamp UTC, anchor row)
symbol             (string: ES.c.0 / NQ.c.0 / YM.c.0 / RTY.c.0)
model_name         (string: e.g., "ttm_v0_2026-05-28")
fold_id            (int)
h_15m_p_up
h_15m_p_down
h_15m_p_flat
... (same for h_30m, h_60m, h_90m, h_240m)
prediction_created_at
```

---

## §7. Sample-count viability

| Component | Sample count | Notes |
|---|---|---|
| Total minutes 2018-05 → 2026-02 (selection) | ~2.8M × 4 symbols | After RTH filter: ~600k per symbol |
| At 4 anchor rows / minute → all 5 horizons | ~2.4M anchor rows | Plenty |
| Class balance after 0.5σ thresholding | ~30 / 30 / 40 per horizon | Mild imbalance, manageable |
| Per fold test window | 100k–600k rows | More than enough for stable AUC/ECE |

---

## §8. Sub-experiments queued for after v0

- **MBO + MBP-1 feature streams** — add as auxiliary channels once available (v0.3)
- **Atlas predictions as input feature** — feed atlas regime probs as channels
- **Larger TSFM** (Moirai-large, fine-tuned Chronos-Bolt) — only if v0.5 lift is model-bound
- **Per-symbol heads** — same backbone, different output head per symbol — if cross-asset attention is sub-optimal
- **Volatility-aware loss** — weight loss by realized vol to focus on tradeable moves

---

## §9. Five ambiguities — RESOLVE BEFORE CODING

These are the audits to run before any model training. Output goes in `report/v0_iter0_dataset_audit.md`.

1. **Bar coverage gaps** — for each symbol, count days with < 200 RTH 1m bars. Verify roll boundaries don't break anchor continuity.
2. **Tick size + slippage assumptions** — confirm ES=0.25, NQ=0.25, YM=1, RTY=0.10 against actual `price - vwap` distributions. Confirm $1.50 round-trip commission is realistic for prop firms.
3. **Cross-symbol time alignment** — at minute t, do all 4 symbols have a bar? If not, how often, when, and how to handle (forward-fill vs drop row)?
4. **Class balance at each horizon** — at k=0.5σ, what's the actual up/down/flat distribution at 15m, 30m, 60m, 90m, 240m? If 4h is heavily flat-dominated (low signal), we may raise k for that horizon.
5. **Vol regime distribution across folds** — are some folds dominated by low-vol or high-vol regimes? Affects how we read fold-to-fold consistency.

---

## §10. Codex instruction block

Send the following to Codex (Claude Code) when ambiguities §9 are resolved:

```
Build tsfm_milk_v0 per experiments/tsfm_milk_v0/PLAN.md.

Hard constraints:
- Multivariate cross-asset input (32 channels, 4 symbols + 4 derived).
- 5 horizons (15m, 30m, 1h, 90m, 4h) emitted in one forward pass.
- 3-way classification (up/down/flat) with k=0.5σ thresholding.
- Walk-forward 6 folds + final holdout 2026-03 → 2026-05.
- No model code knows another stage's internals — Forecaster ABC contract.
- Calibration (ECE ≤ 0.08) is a hard kill criterion.
- No look-ahead, no random splits, no leakage in cross-symbol alignment.

Tasks (in order):
 1. Implement qa.py --audit (run §9 ambiguities, output report/v0_iter0_dataset_audit.md).
 2. Implement build_dataset.py: load bars, build 32-channel multivariate tensor,
    sample at RTH minute boundaries, emit (inputs, labels, ts, symbols) per fold.
 3. Implement Forecaster ABC + NaiveBaseline + LightGBMBaselineForecaster.
 4. Implement TTMForecaster (the v0 primary).
 5. Implement train_walkforward.py running all 3 implementations across 6 folds.
 6. Implement evaluate.py: per-fold per-horizon per-symbol metrics + economic overlay.
 7. Write report/v0_iter1_results.md summarizing kill criteria pass/fail.

After v0 ships:
 8. Implement MoiraiForecaster, re-run walk-forward, compare. Write v0_iter2.

Reports: use real numbers, no placeholders. If a fold breaks, log + skip + report.
```

---

**Updated:** 2026-05-27
**Owner:** Ben Brainard
**Reviewers:** GPT Pro (research design), Codex / Claude Code (implementation)
