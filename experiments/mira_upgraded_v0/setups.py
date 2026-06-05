"""Setup registry -- the GENERALIZED setup stage. Each setup is a (mask, r_fn): which events it applies to,
and its own honest per-event R (its own entry/direction/geometry). The SMT/TF-sync gate + walk-forward ruler +
stop rule are setup-AGNOSTIC and run downstream unchanged. Sweep-reclaim is now just setup #1.

  sweep_reclaim  -- REVERSE: swept the level, reclaimed back, fade the sweep (entry on reclaim). Fill-verified.
  sweep_continue -- TREND:  swept and kept going, trade WITH the break (entry at the break, stop back to level).

Both resolved honestly (target-before-opposite via post_extreme 15/60/120m buckets, stop wins ties, per-symbol cost).
Add gap_fill / smt_fill / double_tap / rejection here -- each with its OWN entry.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from reclaim_entry import DEF, HORIZONS, SPEC, seq_r  # noqa: F401  (seq_r = sweep_reclaim reverse R)


def _per_symbol(df: pd.DataFrame):
    sym = df["symbol"].to_numpy()
    ptv = np.array([SPEC.get(s, DEF)[0] for s in sym])
    cost = np.array([SPEC.get(s, DEF)[1] for s in sym])
    tick = np.array([SPEC.get(s, DEF)[2] for s in sym])
    return ptv, cost, tick


def seq_r_continue(df: pd.DataFrame, target_r: float) -> np.ndarray:
    """TREND R: enter at the break (~level), trade WITH the sweep. Stop = reversal back to the level (risk=depth);
    target = continuation target_r*depth past the extreme. Win = continuation bucket strictly before the stop bucket."""
    ptv, cost, tick = _per_symbol(df)
    depth = np.maximum(df["sweep.5m.max_through_pts"].to_numpy(float), 8 * tick)   # level -> extreme
    tgt = target_r * depth                                                          # continuation past extreme
    cost_r = cost / (depth * ptv)
    n, INF = len(df), 9
    first_cont, first_stop = np.full(n, INF), np.full(n, INF)
    for i, h in enumerate(HORIZONS):
        cont = df[f"post_extreme.5m.{h}.max_rebreak_extreme_pts"].to_numpy(float) >= tgt     # continued past extreme
        stop = df[f"post_extreme.5m.{h}.max_away_from_extreme_pts"].to_numpy(float) >= depth  # reversed back to level
        first_cont = np.where((first_cont == INF) & cont, i, first_cont)
        first_stop = np.where((first_stop == INF) & stop, i, first_stop)
    win = (first_cont < INF) & (first_cont < first_stop)
    return np.where(win, target_r, -1.0) - cost_r


def _double_manip_opp(df: pd.DataFrame, window_min: int = 120) -> np.ndarray:
    """TWO-SIDED PURGE: a reclaim preceded by an OPPOSITE-side sweep in the same session within window_min
    (highs grabbed, then lows -> reverse). The classic both-sides liquidity raid before the real move."""
    recl = _reclaimed(df)
    t = pd.to_datetime(df["touch_ts_utc"]).to_numpy()
    sd = df["session_date"].astype(str).to_numpy()
    side = df["smt_anchor_side"].to_numpy()
    out = np.zeros(len(df), bool)
    for s in np.unique(sd):
        sel = np.where(sd == s)[0]
        order = np.argsort(t[sel])
        so, to, sido = sel[order], t[sel][order], side[sel][order]
        for k in range(1, len(so)):
            dt = (to[k] - to[:k]) / np.timedelta64(1, "m")
            if ((sido[:k] != sido[k]) & (dt > 0) & (dt <= window_min)).any():   # prior OPPOSITE-side sweep
                out[so[k]] = True
    return out & recl


def _reclaimed(df: pd.DataFrame) -> np.ndarray:
    return df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0


def _all(df: pd.DataFrame) -> np.ndarray:
    return np.ones(len(df), bool)


def _fam(name: str):
    return lambda df: df["level_family"].to_numpy() == name


def _double_manip(df: pd.DataFrame, window_min: int = 90) -> np.ndarray:
    """DOUBLE-MANIPULATION: a reclaim preceded by a SAME-SIDE sweep in the same session within window_min, where
    THIS sweep runs DEEPER (a 2nd, deeper grab of the same liquidity) -> then reverse. The genuine 2-stage pattern."""
    recl = _reclaimed(df)
    t = pd.to_datetime(df["touch_ts_utc"]).to_numpy()
    sd = df["session_date"].astype(str).to_numpy()
    side = df["smt_anchor_side"].to_numpy()
    ext = df["sweep.5m.sweep_extreme_price"].to_numpy(float)
    out = np.zeros(len(df), bool)
    for s in np.unique(sd):
        sel = np.where(sd == s)[0]
        order = np.argsort(t[sel])
        so, to, sido, exo = sel[order], t[sel][order], side[sel][order], ext[sel][order]
        for k in range(1, len(so)):
            dt = (to[k] - to[:k]) / np.timedelta64(1, "m")
            prior = (sido[:k] == sido[k]) & (dt > 0) & (dt <= window_min)     # same-side prior sweep in window
            if not prior.any():
                continue
            pe = exo[:k][prior]
            deeper = (exo[k] < np.nanmin(pe)) if sido[k] == "low" else (exo[k] > np.nanmax(pe))
            if deeper:                                                        # this grab ran past the 1st
                out[so[k]] = True
    return out & recl


# registry: name -> (which-events mask, per-event R function). Each setup = its own entry/direction/geometry.
SETUPS = {
    "sweep_reclaim": (_reclaimed, seq_r),            # REVERSE: reclaim entry (fill-verified)
    "sweep_continue": (_all, seq_r_continue),         # TREND: break entry
    "gap_fill": (_fam("daily_gap"), seq_r),           # TAG entry on gap levels (all touches: fill -> reverse)
    "smt_fill": (_fam("fvg"), seq_r),                 # TAG entry on FVG fills (all touches; SMT gate = the divergence)
    "double_manip": (_double_manip, seq_r),           # REVERSE after a same-side DEEPER 2nd grab
    "double_opp": (_double_manip_opp, seq_r),          # REVERSE after a two-sided purge (opp side grabbed first)
}
