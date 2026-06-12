"""Level instances with per-instance validity (PLAN rules A1/A2/A8) — tier 1 + round numbers.

Every level instance carries (level_id, family, price, valid_from, valid_to, source span).
The touch detector asserts touch_onset >= valid_from; instances whose source span crosses
a roll-poison day are dropped here. Level CONSTRUCTION uses 1m bars (session-aware);
touch PRICING happens on MBP-1 in touches.py (PLAN rule that bars never price touches).

valid_from per family (PLAN Phase 0 table):
  prior-day (pdh/pdl/pdc/pd_mid), prior-week (pwh/pwl/pwc), round numbers -> Globex open
  overnight (onh/onl), premarket (pmh/pml), london (loh/lol)             -> 09:30 ET
  asia (ash/asl)                                                          -> 02:00 ET
  rth_open + gap_pdc (gap-qualified prior close)                          -> 09:31 ET
  opening range (orh/orl)                                                 -> 09:45 ET

Importable; no CLI. Tier 2 dynamic/computed families (VWAP bands, VP nodes, FVG,
equal H/L) and tier 3 (gamma walls, MBO clusters) land in later increments.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from spec import EPS_TICKS, REPO, ROUND_GRID_PTS, TICK  # noqa: F401

import sys  # noqa: E402

sys.path.insert(0, str(REPO / "backend"))
from app.data.reader import read_bars  # noqa: E402
from app.research.sessions import globex_day_for_trading_date  # noqa: E402

ET = ZoneInfo("America/New_York")


def _naive_utc(ts) -> pd.Timestamp:
    return pd.Timestamp(ts).tz_convert("UTC").tz_localize(None)


def _et(d: dt.date, hh: int, mm: int) -> pd.Timestamp:
    return _naive_utc(pd.Timestamp(dt.datetime(d.year, d.month, d.day, hh, mm), tz=ET))


def load_bars_et(sym: str, start: str, end: str) -> pd.DataFrame:
    """1m bars indexed by ET ts with trading-date labels (evening bars -> next session)."""
    b = read_bars(symbol=sym, timeframe="1m", start=start, end=end)
    ts = pd.to_datetime(b["ts_event"], utc=True).dt.tz_convert(ET)
    df = pd.DataFrame(
        {
            "o": np.asarray(b["open"].to_numpy(), dtype=float),
            "h": np.asarray(b["high"].to_numpy(), dtype=float),
            "l": np.asarray(b["low"].to_numpy(), dtype=float),
            "c": np.asarray(b["close"].to_numpy(), dtype=float),
        },
        index=ts,
    ).sort_index()
    df["tod"] = df.index.hour * 60 + df.index.minute
    date = df.index.normalize()
    td = pd.Series(date, index=df.index) + pd.to_timedelta(
        (df["tod"] >= 1080).to_numpy() * 1, unit="D"
    )
    wd = td.dt.weekday
    td = td + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    df["td"] = td.dt.date
    return df


def day_table(bars: pd.DataFrame) -> pd.DataFrame:
    """Per-trading-day session aggregates (all sessions defined WITHIN trading day td)."""
    tod = bars["tod"]
    segs = {
        "rth": (tod >= 570) & (tod < 960),
        "orr": (tod >= 570) & (tod < 585),
        "on": (tod >= 1080) | (tod < 570),
        "pm": (tod >= 240) & (tod < 570),
        "as": (tod >= 1080) | (tod < 120),
        "lo": (tod >= 120) & (tod < 570),
    }
    out = None
    for name, mask in segs.items():
        seg = bars[mask]
        agg = seg.groupby("td").agg(
            h=("h", "max"), l=("l", "min"), o=("o", "first"), c=("c", "last")
        )
        agg.columns = [f"{name}_{c}" for c in agg.columns]
        out = agg if out is None else out.join(agg, how="outer")
    out = out.sort_index()
    iso = pd.Series(pd.to_datetime(out.index), index=out.index).dt.isocalendar()
    out["yw"] = iso["year"].astype(str) + "-" + iso["week"].astype(str).str.zfill(2)
    return out


def _prior_week_map(days: pd.DataFrame) -> dict[str, dict]:
    wk = days.groupby("yw").agg(
        pwh=("rth_h", "max"),
        pwl=("rth_l", "min"),
        pwc=("rth_c", "last"),
        w_start=("yw", lambda s: s.index.min()),
        w_end=("yw", lambda s: s.index.max()),
    )
    keys = list(wk.index)
    return {keys[i]: wk.iloc[i - 1].to_dict() for i in range(1, len(keys))}


def _round_levels(pdh: float, pdl: float, step: float) -> list[float]:
    rng = max(pdh - pdl, step)
    lo, hi = pdl - 0.5 * rng, pdh + 0.5 * rng
    k0, k1 = int(np.ceil(lo / step)), int(np.floor(hi / step))
    return [k * step for k in range(k0, k1 + 1)]


def _poisoned(poison: set[dt.date], a: dt.date, b: dt.date) -> bool:
    return any(a <= p <= b for p in poison)


def build_instances(
    sym: str, start: str, end: str, poison: set[dt.date]
) -> pd.DataFrame:
    """All level instances for [start, end] trading days. Drops roll-crossing instances."""
    lookback = (dt.date.fromisoformat(start) - dt.timedelta(days=15)).isoformat()
    days = day_table(load_bars_et(sym, lookback, end))
    pw = _prior_week_map(days)
    tick = TICK[sym]
    rows: list[dict] = []
    tds = [d for d in days.index if start <= d.isoformat() <= end]
    for td in tds:
        loc = days.index.get_loc(td)
        if loc == 0:
            continue
        prev_td = days.index[loc - 1]
        r, p = days.loc[td], days.loc[prev_td]
        g_open = _naive_utc(globex_day_for_trading_date(td).start_utc)
        v930, v931, v945, v200 = (
            _et(td, 9, 30),
            _et(td, 9, 31),
            _et(td, 9, 45),
            _et(td, 2, 0),
        )
        v_to = _naive_utc(globex_day_for_trading_date(td).end_utc)

        def add(
            family: str,
            price: float,
            vf: pd.Timestamp,
            s0: dt.date,
            s1: dt.date,
            **meta,
        ) -> None:
            if not np.isfinite(price) or _poisoned(poison, s0, td):
                return
            # level_key = persistent identity across days (level-block bootstrap unit):
            # round numbers persist by price; prior-week by defining week; dailies by day.
            key = (
                f"{sym}|round|{price:.2f}"
                if family == "round"
                else (
                    f"{sym}|{family}|{s0}"
                    if family in ("pwh", "pwl", "pwc")
                    else f"{sym}|{family}|{td}"
                )
            )
            rows.append(
                {
                    "symbol": sym,
                    "trading_day": td,
                    "family": family,
                    "level_id": f"{sym}|{family}|{td}|{price:.2f}",
                    "level_key": key,
                    "price": float(price),
                    "valid_from": vf,
                    "valid_to": v_to,
                    "source_start": s0,
                    "source_end": s1,
                    **meta,
                }
            )

        # prior-day family (valid from Globex open)
        add("pdh", p["rth_h"], g_open, prev_td, prev_td)
        add("pdl", p["rth_l"], g_open, prev_td, prev_td)
        add("pdc", p["rth_c"], g_open, prev_td, prev_td)
        add("pd_mid", (p["rth_h"] + p["rth_l"]) / 2.0, g_open, prev_td, prev_td)
        # prior week
        w = pw.get(r["yw"])
        if w is not None:
            add("pwh", w["pwh"], g_open, w["w_start"], w["w_end"])
            add("pwl", w["pwl"], g_open, w["w_start"], w["w_end"])
            add("pwc", w["pwc"], g_open, w["w_start"], w["w_end"])
        # session extremes (valid at/after the defining session END — PLAN rule A2)
        add("onh", r["on_h"], v930, prev_td, td)
        add("onl", r["on_l"], v930, prev_td, td)
        add("pmh", r["pm_h"], v930, td, td)
        add("pml", r["pm_l"], v930, td, td)
        add("ash", r["as_h"], v200, prev_td, td)
        add("asl", r["as_l"], v200, prev_td, td)
        add("loh", r["lo_h"], v930, td, td)
        add("lol", r["lo_l"], v930, td, td)
        add("orh", r["orr_h"], v945, td, td)
        add("orl", r["orr_l"], v945, td, td)
        # open + gap-qualified prior close (needs the open to know a gap exists)
        add("rth_open", r["rth_o"], v931, td, td)
        gap_ticks = (r["rth_o"] - p["rth_c"]) / tick
        if np.isfinite(gap_ticks) and abs(gap_ticks) >= 2 * EPS_TICKS:
            add("gap_pdc", p["rth_c"], v931, prev_td, td, gap_ticks=float(gap_ticks))
        # round numbers (grid bounded by prior-day info only)
        if np.isfinite(p["rth_h"]) and np.isfinite(p["rth_l"]):
            for px in _round_levels(p["rth_h"], p["rth_l"], ROUND_GRID_PTS[sym]):
                add("round", px, g_open, prev_td, prev_td)
    return pd.DataFrame(rows)
