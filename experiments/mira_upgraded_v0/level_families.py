"""Upgraded-Mira: NEW level families (gaps, gamma walls) that plug into Mira's proven pipeline.

SEPARATE research module. Imports Mira's LevelSpec framework READ-ONLY -- does NOT touch the live engine.
Each generator returns list[LevelSpec] (Mira's exact schema), so Mira's downstream sweep -> MBO-bookproxy
confirmation -> honest-R pipeline consumes them unchanged. This is the "more levels" half of upgraded Mira;
the combo sweep (level x confirmation) wires these into Mira's event builder next.

Run (smoke): backend/.venv/Scripts/python.exe experiments/mira_upgraded_v0/level_families.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RT = Path(__file__).resolve().parents[2]
for _p in ["live_engine/vendor/bs_mira/mira_v1", "live_engine/vendor/bs_mira/mira_v0"]:
    sys.path.insert(0, str(RT / _p))
import build_pdh_pdl_mbo_events as v0  # noqa: E402  (Mira v0 helpers: ET_TZ, RTH_START, _to_utc_timestamp)
from build_level_events import LevelSpec, _et_ts  # noqa: E402  (Mira v1 schema + helper, read-only)

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

ET, SYM = "America/New_York", "ES.c.0"
GAMMA = RT / "experiments/options_signals_v0/out/gamma_walls_2025.parquet"


def _spec(family, ltype, price, side, anchor, *, known, search, hi, lo) -> LevelSpec:
    return LevelSpec(level_family=family, level_type=ltype, level_side=side, smt_anchor_side=anchor,
                     level_price=float(price), level_known_ts_utc=known, source_start_ts_utc=known,
                     source_end_ts_utc=known, search_start_ts_utc=search, source_high=float(hi),
                     source_low=float(lo), source_range_pts=float(abs(hi - lo)))


def gap_levels(session_date: dt.date, prior_rth: pd.DataFrame, current_rth: pd.DataFrame) -> list[LevelSpec]:
    """Daily-gap fill level = prior RTH close (the magnet price reverses to). Side set by gap direction."""
    if prior_rth.empty or current_rth.empty:
        return []
    pclose = float(pd.to_numeric(prior_rth["close"]).iloc[-1])
    topen = float(pd.to_numeric(current_rth["open"]).iloc[0])
    if not (np.isfinite(pclose) and np.isfinite(topen)) or abs(topen - pclose) < 1e-9:
        return []
    side, anchor = ("support", "low") if topen > pclose else ("resistance", "high")  # gap-fill target side
    known = v0._to_utc_timestamp(_et_ts(session_date, v0.RTH_START))
    search = v0._to_utc_timestamp(pd.Timestamp(current_rth["ts_event"].min()))
    return [_spec("daily_gap", "gap_fill", pclose, side, anchor, known=known, search=search, hi=pclose, lo=topen)]


def gamma_wall_levels(session_date: dt.date, wall: float, current_rth: pd.DataFrame) -> list[LevelSpec]:
    """Dealer gamma wall (SPX GEX magnet) as a level. Side set by where price opens vs the wall."""
    if not np.isfinite(wall) or current_rth.empty:
        return []
    topen = float(pd.to_numeric(current_rth["open"]).iloc[0])
    side, anchor = ("resistance", "high") if wall >= topen else ("support", "low")
    known = v0._to_utc_timestamp(_et_ts(session_date, v0.RTH_START))
    search = v0._to_utc_timestamp(pd.Timestamp(current_rth["ts_event"].min()))
    return [_spec("gamma_wall", "gex_wall", wall, side, anchor, known=known, search=search, hi=wall, lo=wall)]


def fvg_levels(session_date: dt.date, bars: pd.DataFrame, tf: str = "15min",
               lookback_h: int = 18, max_n: int = 6) -> list[LevelSpec]:
    """3-candle FVG (imbalance) zones as reversal levels: level = FAR edge (full-fill point), known when the
    3rd candle closes. Only FVGs formed in the lookback before today's RTH open. Price sweeps in to fill -> reclaim."""
    if bars is None or bars.empty:
        return []
    b = bars.copy()
    b["ts"] = pd.to_datetime(b["ts_event"], utc=True)
    open_et = _et_ts(session_date, v0.RTH_START)
    win = b[(b["ts"] >= open_et - pd.Timedelta(hours=lookback_h)) & (b["ts"] < open_et)]
    if len(win) < 5:
        return []
    c = win.set_index("ts").resample(tf).agg(h=("high", "max"), l=("low", "min")).dropna()
    if len(c) < 3:
        return []
    hh, ll, ts = c["h"].to_numpy(float), c["l"].to_numpy(float), c.index
    search = v0._to_utc_timestamp(open_et)
    specs: list[LevelSpec] = []
    for i in range(1, len(c) - 1):
        if ll[i + 1] > hh[i - 1]:                      # bullish FVG -> demand void below; far edge = bottom
            far, near, side, anchor = hh[i - 1], ll[i + 1], "support", "low"
        elif hh[i + 1] < ll[i - 1]:                    # bearish FVG -> supply void above; far edge = top
            far, near, side, anchor = ll[i - 1], hh[i + 1], "resistance", "high"
        else:
            continue
        specs.append(_spec("fvg", "fvg_fill", far, side, anchor, known=v0._to_utc_timestamp(ts[i + 1]),
                           search=search, hi=max(near, far), lo=min(near, far)))
    return specs[-max_n:]


def wick_levels(session_date: dt.date, bars: pd.DataFrame, tfs=("30min", "60min"),
                min_wick_atr: float = 0.6, max_n: int = 3) -> list[LevelSpec]:
    """Rejection blocks / HTF wicks: a candle with a large REJECTING wick -> its body edge is a reversal level.
    Upper wick -> resistance at body-top; lower wick -> support at body-bottom. Known at candle close."""
    if bars is None or bars.empty:
        return []
    b = bars.copy()
    b["ts"] = pd.to_datetime(b["ts_event"], utc=True)
    open_et = _et_ts(session_date, v0.RTH_START)
    win = b[(b["ts"] >= open_et - pd.Timedelta(hours=24)) & (b["ts"] < open_et)]
    if len(win) < 5:
        return []
    search = v0._to_utc_timestamp(open_et)
    specs: list[LevelSpec] = []
    for tf in tfs:
        c = win.set_index("ts").resample(tf).agg(
            o=("open", "first"), h=("high", "max"), l=("low", "min"), cl=("close", "last")).dropna()
        if len(c) < 3 or not ((c["h"] - c["l"]).median() > 0):
            continue
        atr = float((c["h"] - c["l"]).median())
        for ts_i, r in c.iterrows():
            bhi, blo, body = max(r.o, r.cl), min(r.o, r.cl), abs(r.cl - r.o)
            known = v0._to_utc_timestamp(ts_i + pd.Timedelta(tf))
            if (r.h - bhi) >= min_wick_atr * atr and (r.h - bhi) > body:        # bearish rejection (upper wick)
                specs.append(_spec("wick", "rejection", bhi, "resistance", "high",
                                   known=known, search=search, hi=r.h, lo=bhi))
            if (blo - r.l) >= min_wick_atr * atr and (blo - r.l) > body:        # bullish rejection (lower wick)
                specs.append(_spec("wick", "rejection", blo, "support", "low",
                                   known=known, search=search, hi=blo, lo=r.l))
    return specs[-max_n:]


def _rth_by_day() -> dict:
    b = read_bars(symbol=SYM, timeframe="1m", start="2025-04-01", end="2026-06-01")
    b = b.assign(ts_event=pd.to_datetime(b["ts_event"], utc=True))
    et = b["ts_event"].dt.tz_convert(ET)
    b = b.assign(session_date=et.dt.date, tod=et.dt.hour * 60 + et.dt.minute)
    rth = b[(b["tod"] >= 570) & (b["tod"] < 960)]
    return {d: g.sort_values("ts_event") for d, g in rth.groupby("session_date")}


def main() -> int:
    days = _rth_by_day()
    gw = pd.read_parquet(GAMMA)
    gw.index = pd.to_datetime(gw.index).date
    walls = gw["wall"].to_dict()
    keys = sorted(days)
    specs = []
    for i in range(1, len(keys)):
        d, pd_ = keys[i], keys[i - 1]
        specs += gap_levels(d, days[pd_], days[d])
        if d in walls:
            specs += gamma_wall_levels(d, float(walls[d]), days[d])
    df = pd.DataFrame([{"date": s.search_start_ts_utc.date(), "family": s.level_family, "type": s.level_type,
                        "price": round(s.level_price, 2), "side": s.level_side} for s in specs])
    print(f"generated {len(specs)} LevelSpecs across {len(keys)} RTH days (gap + gamma_wall families)")
    print(f"  by family: {df['family'].value_counts().to_dict()}")
    print("\nsample (last 8) -- these are valid Mira LevelSpecs, ready for the sweep->bookproxy->R pipeline:")
    print(df.tail(8).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
