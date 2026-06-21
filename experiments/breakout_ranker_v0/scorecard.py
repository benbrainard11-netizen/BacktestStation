"""The advice's 0-100 breakout-candidate scorecard, computed from the causal setup features.
Each component is a cross-sectional percentile of the relevant feature(s) so the score is
well-defined and rank-stable. Catalyst (0-10 in the advice) needs news we don't pull here,
so it is omitted (documented) — it does not change the ranking of what we can score.

  market regime   0-20   regime_up + trailing SPY strength
  sector strength 0-20   top-quartile-sector percentile
  rel strength    0-20   rs_6m / ret_6m / ret_12_1
  compression     0-15   tight base + vol contraction + proximity to 52wk high
  accumulation    0-15   close-location-value + up/down volume
  - extendedness  0-10   penalty for already-extended above ma50
  - liquidity     0-10   penalty for thin dollar-volume
"""
from __future__ import annotations

import pandas as pd


def _pct(s: pd.Series) -> pd.Series:
    return s.rank(pct=True)


def score(df: pd.DataFrame) -> pd.Series:
    regime = 20 * (0.5 * df["regime_up"] + 0.5 * _pct(df["spy_ret60"]))
    sector = 20 * df["sector_pct"].fillna(0.5)
    rs = 20 * (_pct(df["rs_6m"]) + _pct(df["ret_6m"]) + _pct(df["ret_12_1"])) / 3
    compression = 15 * ((1 - _pct(df["base_width"])) + (1 - _pct(df["vol_contract"])) + _pct(df["high52_prox"])) / 3
    accumulation = 15 * (_pct(df["clv20"]) + _pct(df["updnvol"].fillna(df["updnvol"].median()))) / 2
    extend_pen = 10 * _pct(df["dist_ma50"])          # more extended => bigger penalty
    liq_pen = 10 * (1 - _pct(df["log_dvol"]))         # thinner => bigger penalty
    return (regime + sector + rs + compression + accumulation - extend_pen - liq_pen).rename("score")
