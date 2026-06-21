"""Phase model v0 -- STEP ZERO: are consolidation/expansion phases actually forecastable? (before any TSFM).

The lesson from this session: never build a forecaster for a target that turns out random. So first prove the
phases have a there-there, on CLEAN daily data (daily closes aren't wick-contaminated like the 5m bars were).

Phase axis = Kaufman EFFICIENCY RATIO (the textbook expansion-vs-consolidation measure: |net move| / total path
over a window; ~1 = clean trend/expansion, ~0 = choppy/consolidation) + realized vol. Tests:
  1. FORECASTABILITY (the key one): does PAST trendiness/vol predict FORWARD (non-overlapping) trendiness/vol?
     corr(past_er, fwd_er) and corr(past_vol, fwd_vol). Non-overlapping windows so it's not autocorrelation.
  2. STICKINESS: P(same phase tomorrow).
  3. MEANINGFUL: do expansion phases actually have bigger forward moves than consolidation phases?
If past predicts forward -> phases are forecastable -> a phase model is worth building. If not -> we can only
nowcast the current phase, not forecast the next (still useful for gating, but no TSFM needed).

Run: backend/.venv/Scripts/python.exe experiments/phase_model_v0/characterize_phases.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PANEL = Path(__file__).resolve().parents[1] / "sync_regime_v0" / "out" / "daily_returns.parquet"
W = 20   # phase window (trading days ~ 1 month)


def fwd_sum(x: pd.Series, n: int) -> pd.Series:
    """Sum over the FORWARD window (t+1 .. t+n)."""
    return x[::-1].rolling(n, min_periods=n).sum()[::-1].shift(-1)


def main() -> int:
    R = pd.read_parquet(PANEL)
    R.index = pd.to_datetime(R.index)
    logP = R.cumsum()                                   # affine log-price proxy (fine for efficiency ratio)
    absR = R.abs()
    print(f"panel {R.shape[0]} days x {R.shape[1]} assets  {R.index.min().date()}..{R.index.max().date()}  W={W}d\n")

    rows = {}
    for s in R.columns:
        p = logP[s]
        past_net = (p - p.shift(W)).abs()
        past_path = absR[s].rolling(W).sum()
        past_er = (past_net / past_path).replace([np.inf, -np.inf], np.nan)
        past_vol = R[s].rolling(W).std()
        fwd_net = (p.shift(-W) - p).abs()
        fwd_path = fwd_sum(absR[s], W)
        fwd_er = (fwd_net / fwd_path).replace([np.inf, -np.inf], np.nan)
        fwd_vol = fwd_sum(R[s] ** 2, W) ** 0.5

        d = pd.DataFrame({"per": past_er, "fer": fwd_er, "pv": past_vol, "fv": fwd_vol}).dropna()
        # phase by past trendiness terciles
        q1, q2 = d["per"].quantile([0.33, 0.67])
        exp = d[d["per"] >= q2]      # expansion (trendy)
        con = d[d["per"] <= q1]      # consolidation (choppy)
        rows[s] = {
            "er_fcast": d["per"].corr(d["fer"]),          # does past trendiness predict forward trendiness?
            "vol_fcast": d["pv"].corr(d["fv"]),           # vol clustering (sanity: should be high)
            "exp_fwd_er": exp["fer"].mean(),              # expansion -> forward trendiness
            "con_fwd_er": con["fer"].mean(),              # consolidation -> forward trendiness
            "exp_fwd_vol": exp["fv"].mean(),
            "con_fwd_vol": con["fv"].mean(),
        }
    T = pd.DataFrame(rows).T
    pd.set_option("display.width", 200)
    print(T.round(3).to_string())
    print("\n---- AGGREGATE (mean across assets) ----")
    print(f"  trendiness forecastability  corr(past_ER, fwd_ER) = {T['er_fcast'].mean():+.3f}  "
          f"(>0.15 = expansion/consolidation persists)")
    print(f"  vol forecastability         corr(past_vol, fwd_vol) = {T['vol_fcast'].mean():+.3f}  (sanity, expect high)")
    print(f"  expansion phase -> fwd ER {T['exp_fwd_er'].mean():.3f} vs consolidation -> fwd ER {T['con_fwd_er'].mean():.3f}  "
          f"(gap {T['exp_fwd_er'].mean()-T['con_fwd_er'].mean():+.3f} = does the phase carry forward?)")
    print(f"  expansion -> fwd vol {T['exp_fwd_vol'].mean():.4f} vs consolidation -> fwd vol {T['con_fwd_vol'].mean():.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
