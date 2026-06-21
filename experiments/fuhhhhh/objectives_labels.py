"""Objective engine + triple-barrier race labels (geo_ block, y, realized R).

Objectives: nearest meaningful level above AND below price at t, drawn from all
families (options levels mapped to ES via prior-day basis, session levels, VWAP).
Levels can be on either side of spot regardless of name (LEDGER P0.2). Registered
params live in common.py (OBJ_MIN_PTS, OBJ_CAP_ATR_FRAC).

Label: y=1 up-objective touched first, y=0 down first, y=2 neither within the time
barrier (or 16:00 ET), y=-1 ambiguous (both in one 1m bar — excluded, counted; rule 6
conservative-ambiguity; tick-level verification is the phase-3 job).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

import common as C

FAMILIES = ("gamma", "pdhl", "on", "or", "vwap")


def _tick(x: float) -> float:
    return round(x / C.TICK) * C.TICK


def candidate_levels(
    gex_row: pd.Series | None, levels: dict[str, float], vwap: float, basis: float
) -> list[tuple[float, str]]:
    """All (es_price, family) candidates valid at t. Caller built `levels` causally."""
    out: list[tuple[float, str]] = []
    if gex_row is not None:
        for col in ("call_wall", "put_wall", "zero_gamma", "pin"):
            v = float(gex_row[col])
            if math.isfinite(v):
                out.append((_tick(v + basis), "gamma"))
    for k, fam in (("pdh", "pdhl"), ("pdl", "pdhl"), ("onh", "on"), ("onl", "on"), ("orh", "or"), ("orl", "or")):
        if k in levels:
            out.append((_tick(levels[k]), fam))
    if math.isfinite(vwap):
        out.append((_tick(vwap), "vwap"))
    return out


def pick_objectives(
    cands: list[tuple[float, str]], price: float, atr: float,
    min_pts: float | None = None, cap_atr: float | None = None,
) -> tuple[tuple[float, str], tuple[float, str]] | None:
    """Nearest valid level above and below within [min_pts, cap_atr*ATR]. None = no
    setup. Defaults = the registered v1 params; v2 datasets pass economic floors
    (e.g. min_pts = COST_PTS / cost_to_objective_cap)."""
    floor = C.OBJ_MIN_PTS if min_pts is None else min_pts
    cap = (C.OBJ_CAP_ATR_FRAC if cap_atr is None else cap_atr) * atr
    ups = [(lv, f) for lv, f in cands if floor <= lv - price <= cap]
    dns = [(lv, f) for lv, f in cands if floor <= price - lv <= cap]
    if not ups or not dns:
        return None
    return min(ups, key=lambda x: x[0]), max(dns, key=lambda x: x[0])


def geo_features(price: float, up: float, dn: float, fam_up: str, fam_dn: str, atr: float) -> dict[str, float]:
    du, dd = up - price, price - dn
    f = {
        "geo_dist_up": du / atr,
        "geo_dist_dn": dd / atr,
        "geo_log_ratio": float(np.log(du / dd)),
    }
    for fam in FAMILIES:
        f[f"geo_up_{fam}"] = 1.0 if fam_up == fam else 0.0
        f[f"geo_dn_{fam}"] = 1.0 if fam_dn == fam else 0.0
    return f


def race_label(fwd: pd.DataFrame, up: float, dn: float) -> tuple[int | None, float | None, float]:
    """First-touch race on forward 1m bars (already sliced to the barrier window).

    Returns (y, close_end, mins_to_resolve). close_end only meaningful for y=2;
    mins_to_resolve = bar offset of the resolving bar (NaN for timeout). y=None means
    no forward bars exist (early close) — caller skips the row. y=-1 = both barriers
    inside one bar: order unknowable at bar grain, scored CONSERVATIVELY as a stop
    (rule 6).
    """
    if fwd.empty:
        return None, None, float("nan")
    hi = fwd["high"].to_numpy(float)
    lo = fwd["low"].to_numpy(float)
    hit_up = hi >= up
    hit_dn = lo <= dn
    iu = int(np.argmax(hit_up)) if hit_up.any() else None
    idn = int(np.argmax(hit_dn)) if hit_dn.any() else None
    if iu is not None and idn is not None:
        if iu == idn:
            return -1, None, float(iu)  # both barriers inside one bar: order unknowable
        return (1, None, float(iu)) if iu < idn else (0, None, float(idn))
    if iu is not None:
        return 1, None, float(iu)
    if idn is not None:
        return 0, None, float(idn)
    return 2, float(fwd["close"].iloc[-1]), float("nan")


def realized_r(
    y: int, entry: float, up: float, dn: float, close_end: float | None,
    cost_pts: float | None = None,
) -> tuple[float, float]:
    """(r_long_net, r_short_net) in R units, costs included. Long: target=up stop=dn.

    cost_pts = per-trade round-trip cost in the instrument's POINTS (rule 6, per-symbol
    honest). Defaults to ES (C.COST_PTS); the NASDAQ port passes C.COST_PTS_NQ.

    y=-1 (ambiguous bar) scores as a STOP on both sides — conservative, never excluded
    from evaluation (CLAUDE.md rule 8 / review finding F1).
    """
    cost = C.COST_PTS if cost_pts is None else cost_pts
    du, dd = up - entry, entry - dn
    if y == 1:
        rl, rs = du / dd, -1.0
    elif y == 0:
        rl, rs = -1.0, dd / du
    elif y == -1:
        rl, rs = -1.0, -1.0
    elif y == 2 and close_end is not None:
        rl, rs = (close_end - entry) / dd, (entry - close_end) / du
    else:
        return np.nan, np.nan
    return rl - cost / dd, rs - cost / du
