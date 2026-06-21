"""State buckets: vol_regime x implied_move_rank (9 primary buckets).

The expensiveness rank is a rolling PRIOR-252-observation percentile -- it may use only
observations strictly before t (enforced by tests/test_no_lookahead_implied_move_rank.py). Ranking
the tradable straddle (not raw IV) is deliberate: IV-cheap but ask-expensive still loses.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RANK_WINDOW = 252
VOL_LOOKBACK = 10
VOL_RANK_WINDOW = 504


def rolling_prior_percentile(values: pd.Series, window: int = RANK_WINDOW) -> pd.Series:
    """Percentile of value_i within the STRICTLY-PRIOR `window` observations (no lookahead).

    rank_i = mean(prior_window < value_i). NaN until `window` prior obs exist.
    """
    v = values.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        lo = i - window
        if lo < 0 or np.isnan(v[i]):
            continue
        prior = v[lo:i]
        prior = prior[~np.isnan(prior)]
        if len(prior) >= window:
            out[i] = float(np.mean(prior < v[i]))
    return pd.Series(out, index=values.index)


def bucket_3(rank: pd.Series, lo: float = 1 / 3, hi: float = 2 / 3) -> pd.Series:
    """cheap (bottom third) / mid / rich (top third); NaN ranks -> NaN bucket."""
    def lab(r):
        if not np.isfinite(r):
            return np.nan
        return "cheap" if r < lo else ("rich" if r >= hi else "mid")
    return rank.map(lab)


def realized_vol_percentile_regime(returns: pd.Series) -> pd.Series:
    """UNVALIDATED fallback regime: simple rolling-std percentile -> CALM/NORMAL/VOLATILE.

    NOT the validated vol-regime model. The PRIMARY audit must use
    validation/vol_regime_adapter.vol_regime_series (canonical MAD method, OOS rho +0.35). This
    plain-std version exists only for self-contained tests / a no-panel fallback, and is labelled
    as such so it can never be mistaken for the validated model (per GPT review).
    """
    rv = returns.rolling(VOL_LOOKBACK).std()
    pct = rolling_prior_percentile(rv, VOL_RANK_WINDOW)
    return bucket_3(pct).map({"cheap": "CALM", "mid": "NORMAL", "rich": "VOLATILE"})


def assign_buckets(entries: pd.DataFrame) -> pd.DataFrame:
    """entries needs columns 'vol_regime' and 'implied_move_rank' (the bucket() label)."""
    out = entries.copy()
    out["bucket"] = out["vol_regime"].astype(str) + " x " + out["implied_move_rank"].astype(str)
    return out
