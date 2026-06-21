"""Data access for the fuhhhhh dataset build: ES 1m bars, options panels, basis, ATR.

All loaders are causal by construction; callers still pass everything through the
build-time asserts in build_dataset.py (SPEC rule 1).
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date as Date, datetime, time as Time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

import common as C

ET = ZoneInfo(C.ET)
UTC = ZoneInfo("UTC")
MS_1600 = 16 * 3600 * 1000

_bar_cache: OrderedDict[str, pd.DataFrame | None] = OrderedDict()


def load_bars_sym(root, day: Date) -> pd.DataFrame | None:
    """One UTC-date partition of a symbol's 1m bars, ET-stamped, cached (LRU 16)."""
    key = f"{root.name}|{day.isoformat()}"
    if key in _bar_cache:
        _bar_cache.move_to_end(key)
        return _bar_cache[key]
    p = root / f"date={day.isoformat()}" / "part-000.parquet"
    df = None
    if p.exists():
        df = pd.read_parquet(p, columns=["ts_event", "open", "high", "low", "close", "volume", "vwap"])
        df["et"] = df["ts_event"].dt.tz_convert(ET)
        df = df.sort_values("ts_event").reset_index(drop=True)
    _bar_cache[key] = df
    while len(_bar_cache) > 16:
        _bar_cache.popitem(last=False)
    return df


def load_bars(day: Date) -> pd.DataFrame | None:
    """ES 1m bars for one UTC date (back-compat wrapper)."""
    return load_bars_sym(C.BARS_1M, day)


def et_ts(day: Date, ms_of_day: int) -> pd.Timestamp:
    h, rem = divmod(ms_of_day // 1000, 3600)
    return pd.Timestamp(datetime.combine(day, Time(h, rem // 60, rem % 60), tzinfo=ET))


def rth_bars(day: Date) -> pd.DataFrame | None:
    """Bars in [09:30, 16:00) ET of `day` (single UTC partition covers all of RTH)."""
    df = load_bars(day)
    if df is None:
        return None
    lo, hi = et_ts(day, 9 * 3600_000 + 30 * 60_000), et_ts(day, MS_1600)
    out = df[(df["et"] >= lo) & (df["et"] < hi)]
    return out if len(out) else None


def overnight_bars(prev_day: Date, day: Date, root=None) -> pd.DataFrame | None:
    """Bars in [18:00 ET prev_day, 09:30 ET day) — the Globex overnight session.

    Loads every UTC partition in [prev_day, day]: Sunday/holiday evenings live in
    partitions between a Friday prev_day and a Monday session (review F2). `root`
    selects the symbol's bar dir (default ES); pass C.BARS_1M_NQ for a symmetric NQ
    overnight (SMT alignment fix).
    """
    root = root or C.BARS_1M
    span = [prev_day + timedelta(days=n) for n in range((day - prev_day).days + 1)]
    parts = [b for b in (load_bars_sym(root, d) for d in span) if b is not None]
    if not parts:
        return None
    df = pd.concat(parts, ignore_index=True)
    lo = et_ts(prev_day, 18 * 3600_000)
    hi = et_ts(day, 9 * 3600_000 + 30 * 60_000)
    out = df[(df["et"] >= lo) & (df["et"] < hi)]
    return out if len(out) else None


def load_panels() -> dict[str, pd.DataFrame]:
    """All options panels, date-normalized to python date objects, sorted."""
    out = {}
    for name, path in (
        ("gex", C.INTRADAY_GEX),
        ("dte0", C.DTE0_FLOW),
        ("iv", C.IV_INTRADAY),
        ("eod", C.GEX_LEVELS_DAILY),
    ):
        df = pd.read_parquet(path)
        df["d"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d").dt.date
        sort = ["d", "ms_of_day"] if "ms_of_day" in df.columns else ["d"]
        out[name] = df.sort_values(sort).reset_index(drop=True)
    return out


def basis_for(day: Date, prev_day: Date, spot_panel_day: pd.DataFrame) -> float | None:
    """SPX->ES additive basis from PRIOR day ~16:00 ET (the proven no-lookahead mapping).

    spot_panel_day = intraday gex/spot rows for prev_day. Returns ES − SPX in points.
    """
    rows = spot_panel_day[spot_panel_day["ms_of_day"] <= MS_1600]
    if rows.empty:
        return None
    r = rows.iloc[-1]
    bars = load_bars(prev_day)
    if bars is None:
        return None
    t = et_ts(prev_day, int(r["ms_of_day"]))
    prior = bars[bars["et"] <= t - pd.Timedelta(minutes=1)]  # bar fully closed by t (F4)
    if prior.empty:
        return None
    return float(prior.iloc[-1]["close"]) - float(r["spot"])


class AtrTracker:
    """Daily ATR(14) from RTH true ranges; day D sees only days < D (push after use)."""

    def __init__(self) -> None:
        self.trs: list[float] = []
        self.prev_close: float | None = None

    def atr(self) -> float | None:
        if len(self.trs) < 5:
            return None
        return float(pd.Series(self.trs[-C.ATR_LEN :]).mean())

    def push_day(self, rth: pd.DataFrame) -> None:
        hi, lo, cl = rth["high"].max(), rth["low"].min(), float(rth["close"].iloc[-1])
        tr = hi - lo
        if self.prev_close is not None:
            tr = max(tr, abs(hi - self.prev_close), abs(lo - self.prev_close))
        self.trs.append(float(tr))
        self.prev_close = cl
