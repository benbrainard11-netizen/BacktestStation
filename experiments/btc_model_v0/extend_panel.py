"""Extend the validated cross-asset daily-returns panel from lake 1m bars.

The validated artifact (sync_regime_v0/out/daily_returns.parquet) ends 2026-04-23.
This builds the missing tail for the 6 peer symbols the BTC model uses, with the
SAME construction (18:00 ET trading-day roll on 1m bars — never the buggy 1d
resample), and writes a module-local extension. The validated artifact is never
modified.

Run: backend/.venv/Scripts/python.exe experiments/btc_model_v0/extend_panel.py
Artifact: data/panel_ext.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(REPO / "backend"))
from app.data.reader import read_bars  # noqa: E402

ET = ZoneInfo("America/New_York")
PEERS = ["NQ.c.0", "ES.c.0", "GC.c.0", "CL.c.0", "6E.c.0", "ZN.c.0"]
START, END = "2026-04-15", "2026-06-10"  # overlap a week for a continuity check

sys.stdout.reconfigure(encoding="utf-8")


def daily_closes(sym: str) -> pd.Series:
    b = read_bars(symbol=sym, timeframe="1m", start=START, end=END)
    ts = pd.to_datetime(b["ts_event"], utc=True).dt.tz_convert(ET)
    c = pd.Series(np.asarray(b["close"].to_numpy(), dtype=float), index=ts).sort_index()
    tod = c.index.hour * 60 + c.index.minute
    td = c.index.normalize() + pd.to_timedelta((tod >= 1080).astype(int), unit="D")
    wd = td.weekday
    td = pd.DatetimeIndex(td + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D"))
    out = c.groupby(td.tz_localize(None).normalize()).last()
    return out


def main() -> int:
    val = pd.read_parquet(REPO / "experiments" / "sync_regime_v0" / "out" / "daily_returns.parquet")
    val.index = pd.DatetimeIndex(val.index).tz_localize(None).normalize()
    ext = {}
    for p in PEERS:
        ret = daily_closes(p).pct_change()
        # continuity check on the overlap week vs the validated panel
        ov = ret.index.intersection(val.index)
        if len(ov) >= 3:
            diff = (ret.loc[ov] - val.loc[ov, p]).abs().max()
            flag = "OK" if diff < 5e-3 else f"MISMATCH {diff:.4f}"
        else:
            flag = "no overlap"
        ext[p] = ret[ret.index > val.index.max()]
        print(f"{p}: +{len(ext[p])} days (overlap check: {flag})")
    e = pd.DataFrame(ext)
    if e.empty:
        raise RuntimeError("0-row extension — refusing to write")
    e.to_parquet(MODULE / "data" / "panel_ext.parquet")
    print(f"extension: {e.index.min().date()} -> {e.index.max().date()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
