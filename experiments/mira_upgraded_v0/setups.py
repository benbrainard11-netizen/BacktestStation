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


def _reclaimed(df: pd.DataFrame) -> np.ndarray:
    return df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0


def _all(df: pd.DataFrame) -> np.ndarray:
    return np.ones(len(df), bool)


def _fam(name: str):
    return lambda df: df["level_family"].to_numpy() == name


# registry: name -> (which-events mask, per-event R function). Each setup = its own entry/direction/geometry.
SETUPS = {
    "sweep_reclaim": (_reclaimed, seq_r),            # REVERSE: reclaim entry (fill-verified)
    "sweep_continue": (_all, seq_r_continue),         # TREND: break entry
    "gap_fill": (_fam("daily_gap"), seq_r),           # TAG entry on gap levels (all touches: fill -> reverse)
    "smt_fill": (_fam("fvg"), seq_r),                 # TAG entry on FVG fills (all touches; SMT gate = the divergence)
}
