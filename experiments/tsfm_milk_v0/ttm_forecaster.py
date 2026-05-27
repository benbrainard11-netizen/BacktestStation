"""TTMForecaster — IBM Granite TinyTimeMixer (TTM), v0 primary.

Reference: https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2

Why TTM:
  - 1-5M params, fits easily on RTX 5080 16GB
  - Multivariate-by-design (any-variate forecasting)
  - Fast fine-tuning, fast inference
  - Designed for custom-domain fine-tuning, not just zero-shot

v0 setup (subject to confirmation during implementation):
  - Pretrained checkpoint: granite-timeseries-ttm-r2 (or successor)
  - Lookback: 240 minutes (PLAN.md §1)
  - Forecast horizons: 15, 30, 60, 90, 240 minutes
  - Output head: 3-way classification per (symbol, horizon) — replace the
    default forecasting head with a small classification MLP per output
  - Loss: cross-entropy per horizon, mean across horizons
  - Calibration: temperature scaling on val fold

NOT YET IMPLEMENTED. Phase: dataset must be built first (build_dataset.py).
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "ttm_forecaster.py is a stub. "
        "Implement after build_dataset.py + baseline_naive.py + "
        "baseline_lightgbm.py are working."
    )


if __name__ == "__main__":
    raise SystemExit(main())
