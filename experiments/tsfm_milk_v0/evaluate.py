"""Evaluate predictions against kill criteria (PLAN §5).

Reads:
  out/predictions/{model}/fold_*_{val,test}.parquet
  walk_forward.yaml
  labels_and_horizons.yaml

Reports SEPARATELY for:
  - each model
  - each fold
  - each horizon
  - each symbol
  - pooled (across-fold per-model)

Statistical metrics:
  - Accuracy
  - Macro-F1
  - Per-class precision
  - ROC-AUC (one-vs-rest)
  - Brier score
  - Expected Calibration Error (ECE)
  - Reliability diagram (saved as PNG per (fold, horizon, symbol))
  - Information Coefficient: Spearman rank corr between
      predicted_directional_score = p_up - p_down
      and realized forward return

Economic overlay:
  For each (symbol, horizon, probability_threshold):
    predicted_dir = argmax(p_up, p_down, p_flat)
    if predicted_dir == flat or max(p_up, p_down) < threshold:
        no trade
    else:
        trade direction = predicted_dir
        entry = next bar's open
        exit  = entry_ts + horizon
        slippage = 1 tick (ES/NQ/YM) or 1 tick (RTY)  ← confirm per-symbol
        commission = $1.50 round-trip per contract

  Report: net_R, mean_R_per_trade, win_rate, max_dd_R, mar_ratio
  AND the threshold maximizing win_rate × R:R per (symbol, horizon).
  That's the input the v1 sizing layer needs.

Kill criteria (median across 6 folds):
  ship → ECE ≤ 0.08 at all horizons + accuracy beats naive by ≥ 2% at ≥ 3 horizons
         + IC > 0 in ≥ 4 folds and ≥ 3 horizons + net_R > 0 at best threshold
  kill → ECE > 0.15 anywhere OR net_R ≤ 0 at every threshold AND horizon

Output:
  report/v0_iter1_results.md
  out/metrics_by_model.parquet

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("evaluate.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
