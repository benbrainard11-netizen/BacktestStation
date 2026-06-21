"""Extend the gamma-wall level family across the FULL 6 months (ES only until NDX/RUT/DJX
backfill lands). Jan probe passed: existing trades reproduced the +0.456/138 anchor exactly
(injection is clean) and the 5 Jan wall trades went +1.781 (5/5) — n too small, hence this.

Builds train_wall (2026-02-06..05-20) + holdout_wall (2026-05-21..06-05) with walls injected,
scores the frozen gate, computes realized-R for the gamma_wall trades ONLY (existing trades'
R is already established in train/oos_holdout; Jan additivity was verified by the probe).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/gamma_wall_extend.py
"""
from __future__ import annotations

import datetime as dt
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
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import smt_bench as SB  # noqa: E402
import harness as H  # noqa: E402
import realized_r as RR  # noqa: E402
import gate as G  # noqa: E402

BLE = H.D._ble
V0 = H.D._v0
GEXDIR = Path(r"C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out")
# 4-symbol wall map (2026-06-10). SCALE converts index strike -> futures points BEFORE the basis:
# DJX quotes 1/100th of the Dow. NDX has no greeks history before 2026-05-08 at our Theta tier
# (probed both NDX/NDXP roots: 472 no-data) -> NQ walls exist May 8+ only; builder skips gaps.
WALL_INDEX = {"ES.c.0": "spx", "NQ.c.0": "ndx", "RTY.c.0": "rut", "YM.c.0": "djx"}
SCALE = {"ES.c.0": 1.0, "NQ.c.0": 1.0, "RTY.c.0": 1.0, "YM.c.0": 100.0}
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "RTY.c.0": 0.10, "YM.c.0": 1.0}
WINDOWS = [("jan_wall", "2026-01-02", "2026-02-04"),
           ("train_wall", "2026-02-06", "2026-05-20"),
           ("holdout_wall", "2026-05-21", "2026-06-05")]
SPAN_START, SPAN_END = "2026-01-02", "2026-06-05"
ET16 = dt.time(16, 0)


def build_walls(start: str, end: str) -> dict:
    walls: dict = {}
    bars_lo = (pd.Timestamp(start) - pd.Timedelta(days=30)).date().isoformat()
    bars_hi = (pd.Timestamp(end) + pd.Timedelta(days=5)).date().isoformat()
    for sym, idx in WALL_INDEX.items():
        g = pd.read_parquet(GEXDIR / f"gex_levels_{idx}.parquet").sort_values("date")
        g["d"] = pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d").dt.date
        bars = SB.load_1m(sym, bars_lo, bars_hi)
        tick = TICK[sym]
        scale = SCALE[sym]
        basis: dict = {}
        for _, row in g.iterrows():
            ts = pd.Timestamp(dt.datetime.combine(row["d"], ET16), tz=V0.ET_TZ).tz_convert("UTC")
            pos = bars.index.searchsorted(ts, side="right") - 1
            if pos < 0 or (ts - bars.index[pos]) > pd.Timedelta(minutes=30):
                continue
            basis[row["d"]] = float(bars["close"].iloc[pos]) - float(row["spot"]) * scale
        gex_dates = [d for d in g["d"] if d in basis]
        by_date = g.set_index("d")
        out: dict = {}
        d = pd.Timestamp(start).date()
        while d <= pd.Timestamp(end).date():
            prior = [x for x in gex_dates if x < d]
            if prior and (d - prior[-1]).days <= 7:
                src = prior[-1]
                b = basis[src]
                cw = float(by_date.loc[src, "call_wall"]) * scale + b
                pw = float(by_date.loc[src, "put_wall"]) * scale + b
                out[d] = (round(cw / tick) * tick, round(pw / tick) * tick)
            d += pd.Timedelta(days=1)
        walls[sym] = out
        bv = list(basis.values())
        print(f"  {sym}: {len(out)} sessions with walls; basis mean={np.mean(bv):+.1f} std={np.std(bv):.1f}"
              if bv else f"  {sym}: 0 sessions", flush=True)
    return walls


WALLS = build_walls(SPAN_START, SPAN_END)
_CUR = {"sym": None}
_ORIG_BSE = BLE._build_symbol_events
_ORIG_BLS = BLE._build_level_specs


def _patched_bse(*, symbol, **kw):
    _CUR["sym"] = str(symbol)
    return _ORIG_BSE(symbol=symbol, **kw)


def _patched_bls(*, bars, rth, session_date, prior_date, level_families, opening_range_minutes):
    specs = _ORIG_BLS(bars=bars, rth=rth, session_date=session_date, prior_date=prior_date,
                      level_families=level_families, opening_range_minutes=opening_range_minutes)
    day_walls = WALLS.get(_CUR["sym"], {}).get(session_date)
    if day_walls is None:
        return specs
    current_rth = rth[rth["session_date"].eq(session_date)]
    if current_rth.empty:
        return specs
    known_ts = V0._to_utc_timestamp(BLE._et_ts(session_date, V0.RTH_START))
    search_start = V0._to_utc_timestamp(pd.Timestamp(current_rth["ts_event"].min()))
    cw, pw = day_walls
    for px, ltype, side, anchor in ((cw, "gwc", "resistance", "high"), (pw, "gwp", "support", "low")):
        if not np.isfinite(px):
            continue
        specs.append(BLE.LevelSpec(
            level_family="gamma_wall", level_type=ltype, level_side=side, smt_anchor_side=anchor,
            level_price=float(px), level_known_ts_utc=known_ts,
            source_start_ts_utc=known_ts, source_end_ts_utc=known_ts,
            search_start_ts_utc=search_start,
            source_high=float(px), source_low=float(px), source_range_pts=0.0))
    return specs


BLE._build_symbol_events = _patched_bse
BLE._build_level_specs = _patched_bls


def st(x) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=  0"
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}% sumR={x.sum():+7.1f}"


def main() -> int:
    gate = G.Gate()
    all_wall_trades = []
    for name, start, end in WINDOWS:
        # No pre-delete: harness cache-hits clean builds and self-heals smt_db-poisoned ones.
        # (Delete the parquet manually if the WALL INJECTION itself changes.)
        p = H.DATA / f"{name}.parquet"
        ds = H.build_dataset(name, start, end)
        ds["p"] = gate.score(ds)
        gt = (ds[ds.p >= gate.threshold]
              .sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
              .groupby(H.OPP, sort=False).head(1).copy())
        gw = gt[gt["level_family"].astype(str).eq("gamma_wall")].copy()
        print(f"[{name}] candidates={len(ds)} ({int(ds['level_family'].astype(str).eq('gamma_wall').sum())} wall) "
              f"gated={len(gt)} ({len(gw)} wall)", flush=True)
        if len(gw):
            computed = RR.compute(gw.drop(columns=["p"], errors="ignore"))
            gw["realized_r"] = computed["realized_r"].to_numpy()
            gw["r_reason"] = computed["r_reason"].to_numpy()
            ds.loc[gw.index, "realized_r"] = gw["realized_r"]
            all_wall_trades.append(gw)
        ds.to_parquet(p, index=False)

    aw = pd.concat(all_wall_trades, ignore_index=True)
    aw["rr"] = pd.to_numeric(aw["realized_r"], errors="coerce")
    aw["_mo"] = aw["trigger_ts_utc"].dt.strftime("%Y-%m")
    print(f"\n=== GAMMA-WALL trades, Jan-Jun, 4-SYMBOL (frozen gate; baseline all-family = +0.576) ===")
    print(f"  ALL walls   {st(aw['rr'])}")
    for lt, sub in aw.groupby(aw["level_type"].astype(str)):
        print(f"  {lt:4s}        {st(sub['rr'])}")
    print("  by symbol:")
    for sym, sub in aw.groupby(aw["symbol"].astype(str)):
        print(f"    {sym:8s} {st(sub['rr'])}")
    print("  by month:")
    for mo, sub in aw.groupby("_mo"):
        print(f"    {mo}    {st(sub['rr'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
