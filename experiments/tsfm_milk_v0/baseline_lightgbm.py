"""LightGBMBaselineForecaster — per (symbol, horizon) classifier.

The "real" baseline. Handcrafted feature vector from the lookback window
(returns, vol, range, vwap-dev, basket spreads, etc.) → LightGBM 3-way
classifier. One model per (symbol, horizon) pair = 4 × 5 = 20 models per fold.

If TTM (v0) can't beat this, TSFM isn't the right tool for this dataset and
we ship LightGBM.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("baseline_lightgbm.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
