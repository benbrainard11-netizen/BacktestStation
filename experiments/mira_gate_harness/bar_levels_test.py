"""THREE new bar-only level families through the frozen gate (Jan probe, walls pattern):
  daily_gap : unfilled RTH gap edge (prior RTH close) when |today open - prior close| >= 4 ticks
  prev_mid  : prior RTH midpoint (equilibrium) — emitted as BOTH support and resistance
  month_hl  : prior calendar-month H/L (mnh/mnl)
No options data needed. Injection via _build_level_specs (additivity proven by the wall probe:
existing trades reproduce the anchor exactly). Realized-R on NEW-family gated trades only.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/bar_levels_test.py
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ["BACKTESTSTATION_BACKEND"] = str(ROOT / "live_engine" / "vendor")
os.environ.pop("BS_MIRA_ROOT", None)
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import harness as H  # noqa: E402
import realized_r as RR  # noqa: E402
import gate as G  # noqa: E402

BLE = H.D._ble
V0 = H.D._v0
NAME, START, END = "jan_bars", "2026-01-02", "2026-02-04"
NEW_FAMS = ("daily_gap", "prev_mid", "month_hl")
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}
GAP_MIN_TICKS = 4

_CUR = {"sym": None}
_ORIG_BSE = BLE._build_symbol_events
_ORIG_BLS = BLE._build_level_specs


def _patched_bse(*, symbol, **kw):
    _CUR["sym"] = str(symbol)
    return _ORIG_BSE(symbol=symbol, **kw)


def _spec(fam, ltype, side, anchor, px, known_ts, search_start):
    return BLE.LevelSpec(level_family=fam, level_type=ltype, level_side=side, smt_anchor_side=anchor,
                         level_price=float(px), level_known_ts_utc=known_ts,
                         source_start_ts_utc=known_ts, source_end_ts_utc=known_ts,
                         search_start_ts_utc=search_start,
                         source_high=float(px), source_low=float(px), source_range_pts=0.0)


def _patched_bls(*, bars, rth, session_date, prior_date, level_families, opening_range_minutes):
    specs = _ORIG_BLS(bars=bars, rth=rth, session_date=session_date, prior_date=prior_date,
                      level_families=level_families, opening_range_minutes=opening_range_minutes)
    sym = _CUR["sym"]
    cur = rth[rth["session_date"].eq(session_date)]
    if cur.empty or prior_date is None:
        return specs
    pri = rth[rth["session_date"].eq(prior_date)]
    if pri.empty:
        return specs
    known = V0._to_utc_timestamp(BLE._et_ts(session_date, V0.RTH_START))
    sstart = V0._to_utc_timestamp(pd.Timestamp(cur["ts_event"].min()))
    tick = TICK[sym]
    p_close = float(pri["close"].iloc[-1]); p_hi = float(pri["high"].max()); p_lo = float(pri["low"].min())
    t_open = float(cur["open"].iloc[0])
    # daily_gap: prior close is the gap edge; gap-up -> support below, gap-down -> resistance above
    if abs(t_open - p_close) >= GAP_MIN_TICKS * tick:
        if t_open > p_close:
            specs.append(_spec("daily_gap", "gpl", "support", "low", p_close, known, sstart))
        else:
            specs.append(_spec("daily_gap", "gph", "resistance", "high", p_close, known, sstart))
    # prev_mid: equilibrium, both sides
    mid = round((p_hi + p_lo) / 2 / tick) * tick
    specs.append(_spec("prev_mid", "pmdh", "resistance", "high", mid, known, sstart))
    specs.append(_spec("prev_mid", "pmdl", "support", "low", mid, known, sstart))
    # month_hl: prior calendar-month H/L from all rth bars in that month
    mstart = (pd.Timestamp(session_date).replace(day=1) - pd.offsets.MonthBegin(1)).date()
    mend = pd.Timestamp(session_date).replace(day=1).date()
    mbars = rth[(rth["session_date"] >= mstart) & (rth["session_date"] < mend)]
    if len(mbars):
        specs.append(_spec("month_hl", "mnh", "resistance", "high", float(mbars["high"].max()), known, sstart))
        specs.append(_spec("month_hl", "mnl", "support", "low", float(mbars["low"].min()), known, sstart))
    return specs


BLE._build_symbol_events = _patched_bse
BLE._build_level_specs = _patched_bls


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}% sumR={x.sum():+6.1f}" if len(x) else "n=  0"


def main() -> int:
    p = H.DATA / f"{NAME}.parquet"
    ds = H.build_dataset(NAME, START, END)  # cache-hits if already built with these families
    fam = ds["level_family"].astype(str)
    print(f"built {NAME}: {len(ds)} candidates; new-family: "
          f"{ {f: int(fam.eq(f).sum()) for f in NEW_FAMS} }", flush=True)
    gate = G.Gate()
    ds["p"] = gate.score(ds)
    gt = (ds[ds.p >= gate.threshold].sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(H.OPP, sort=False).head(1).copy())
    new = gt[gt["level_family"].astype(str).isin(NEW_FAMS)].copy()
    print(f"gated/deduped: {len(gt)} ({len(new)} new-family)", flush=True)
    if "realized_r" not in ds.columns:
        ds["realized_r"] = float("nan")
    if len(new):
        comp = RR.compute(new.drop(columns=["p"], errors="ignore"))
        new["realized_r"] = comp["realized_r"].to_numpy()
        ds.loc[new.index, "realized_r"] = new["realized_r"]
    ds.to_parquet(p, index=False)
    print(f"\n=== Jan + bar-only families through frozen gate (existing baseline = +0.456/138) ===")
    for f in NEW_FAMS:
        print(f"  {f:14s}  {st(new[new['level_family'].astype(str) == f]['realized_r'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
