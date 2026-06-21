"""Canonical validated vol-regime, as a per-date series for the audit.

market_state/state_monitor.py::vol_regime is the VALIDATED daily vol-regime (OOS rho +0.35, 6/6
clean symbols) but it emits only the LATEST date. This adapter replicates its exact methodology --
MAD-based realized vol (VOL_WIN=20), ranked against a ~2yr trailing window (RANK_WIN=504), cut at
33/66 -> CALM/NORMAL/VOLATILE -- across ALL dates, no-lookahead (prior-window percentile only).

Same constants and robust estimator as the source; not a fresh stand-in. For SPX we use ES.c.0
(SPX->ES map). The run persists the labels to a small artifact for the payoff audit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from validation.state_buckets import rolling_prior_percentile

# constants copied from market_state/state_monitor.py
VOL_WIN = 20
RANK_WIN = 504
LOW, HIGH = 0.33, 0.66

REPO_ROOT = Path(__file__).resolve().parents[3]
RETURNS_PANEL = REPO_ROOT / "experiments" / "sync_regime_v0" / "out" / "daily_returns.parquet"


def mad_realized_vol(returns: pd.Series) -> pd.Series:
    """Per-date MAD realized vol (the canonical 'now' reading), annualized."""
    med = returns.rolling(VOL_WIN).median()
    return 1.4826 * (returns - med).abs().rolling(VOL_WIN).median() * np.sqrt(252)


def vol_regime_series(returns: pd.Series) -> pd.Series:
    """Date -> CALM/NORMAL/VOLATILE using the canonical method, causal (prior-RANK_WIN percentile)."""
    rv = mad_realized_vol(returns)
    pct = rolling_prior_percentile(rv, RANK_WIN)

    def lab(p):
        if not np.isfinite(p):
            return np.nan
        return "CALM" if p < LOW else ("VOLATILE" if p >= HIGH else "NORMAL")

    return pct.map(lab)


def load_es_returns() -> pd.Series:  # pragma: no cover - reads the panel
    df = pd.read_parquet(RETURNS_PANEL).sort_index()
    if df.index.tz is not None:  # panel is tz-aware UTC; chain dates are naive -> strip tz to align
        df.index = df.index.tz_localize(None)
    col = "ES.c.0" if "ES.c.0" in df.columns else "ES"
    return df[col].dropna()


def build_vol_regime(out_path: str) -> pd.Series:  # pragma: no cover - run step
    """Persist date -> vol_regime (validated methodology) for the audit to consume."""
    reg = vol_regime_series(load_es_returns())
    reg.rename("vol_regime").to_frame().to_parquet(out_path)
    return reg
