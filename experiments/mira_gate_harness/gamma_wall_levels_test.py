"""Gamma-wall LEVELS as a NEW level family, through the FROZEN gate, with realized-R.

Funnel stage 1 (levels = WHERE/frequency): options dealer-gamma walls (call_wall resistance,
put_wall support; SPX->ES, NDX->NQ) injected as level family "gamma_wall" alongside the 7
existing families, Jan window first. NOTE this is DIFFERENT from the (killed) gamma-SIGN
regime filter: walls are price levels that may host sweep+reclaim setups, not a regime split.

NO LOOKAHEAD: walls for session D come from the prior gex row (date < D; that file's rows are
built from day-D EOD greeks/OI, so same-day rows are not knowable intraday). Index->futures
mapping uses the prior day's basis: futures 1m close at 16:00 ET minus index spot, tick-snapped.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/gamma_wall_levels_test.py
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
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import smt_bench as SB  # noqa: E402  (load_1m)
import harness as H  # noqa: E402
import realized_r as RR  # noqa: E402
import gate as G  # noqa: E402

BLE = H.D._ble
V0 = H.D._v0
GEXDIR = Path(r"C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out")
WALL_INDEX = {"ES.c.0": "spx", "NQ.c.0": "ndx"}  # YM/RTY: no DJX/RUT gex levels pulled
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25}
NAME, START, END = "jan_wall", "2026-01-02", "2026-02-04"
ET16 = __import__("datetime").time(16, 0)


def build_walls() -> dict:
    """{symbol: {session_date: (call_wall_px, put_wall_px)}} in FUTURES prices, prior-day data only."""
    import datetime as dt

    walls: dict = {}
    for sym, idx in WALL_INDEX.items():
        g = pd.read_parquet(GEXDIR / f"gex_levels_{idx}.parquet").sort_values("date")
        g["d"] = pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d").dt.date
        bars = SB.load_1m(sym, "2025-12-15", "2026-02-10")
        tick = TICK[sym]

        basis: dict = {}
        for _, row in g.iterrows():
            ts = pd.Timestamp(dt.datetime.combine(row["d"], ET16), tz=V0.ET_TZ).tz_convert("UTC")
            pos = bars.index.searchsorted(ts, side="right") - 1
            if pos < 0 or (ts - bars.index[pos]) > pd.Timedelta(minutes=30):
                continue
            basis[row["d"]] = float(bars["close"].iloc[pos]) - float(row["spot"])

        gex_dates = [d for d in g["d"] if d in basis]
        by_date = g.set_index("d")
        out: dict = {}
        d = pd.Timestamp(START).date()
        while d <= pd.Timestamp(END).date():
            prior = [x for x in gex_dates if x < d]
            if prior and (d - prior[-1]).days <= 7:
                src = prior[-1]
                b = basis[src]
                cw = float(by_date.loc[src, "call_wall"]) + b
                pw = float(by_date.loc[src, "put_wall"]) + b
                out[d] = (round(cw / tick) * tick, round(pw / tick) * tick)
            d += pd.Timedelta(days=1)
        walls[sym] = out
        bvals = list(basis.values())
        print(f"  {sym}: {len(out)} sessions with walls; basis mean={np.mean(bvals):+.1f} "
              f"std={np.std(bvals):.1f} pts", flush=True)
    return walls


WALLS = build_walls()
_CUR = {"sym": None}
_ORIG_BSE = BLE._build_symbol_events
_ORIG_BLS = BLE._build_level_specs


def _patched_bse(*, symbol, **kw):
    _CUR["sym"] = str(symbol)
    return _ORIG_BSE(symbol=symbol, **kw)


def _patched_bls(*, bars, rth, session_date, prior_date, level_families, opening_range_minutes):
    specs = _ORIG_BLS(bars=bars, rth=rth, session_date=session_date, prior_date=prior_date,
                      level_families=level_families, opening_range_minutes=opening_range_minutes)
    sym = _CUR["sym"]
    day_walls = WALLS.get(sym, {}).get(session_date)
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
    p = H.DATA / f"{NAME}.parquet"
    for f in (p, H.DATA / f"{NAME}.manifest.json"):
        if f.exists():
            os.remove(f)
    ds = H.build_dataset(NAME, START, END)
    n_wall_cand = int(ds["level_family"].astype(str).eq("gamma_wall").sum())
    print(f"built {NAME}: {len(ds)} candidates ({n_wall_cand} gamma_wall)", flush=True)

    gate = G.Gate()
    ds["p"] = gate.score(ds)
    gt = (ds[ds.p >= gate.threshold]
          .sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(H.OPP, sort=False).head(1).copy())
    print(f"gated/deduped: {len(gt)} ({int(gt['level_family'].astype(str).eq('gamma_wall').sum())} gamma_wall)",
          flush=True)
    print("computing realized-R on the gated set...", flush=True)
    computed = RR.compute(gt.drop(columns=["p"], errors="ignore"))
    gt["realized_r"] = computed["realized_r"].to_numpy()
    gt["r_reason"] = computed["r_reason"].to_numpy()
    ds.loc[gt.index, "realized_r"] = gt["realized_r"]
    ds.to_parquet(p, index=False)

    gt["grp"] = np.where(gt["level_family"].astype(str).eq("gamma_wall"), "gamma_wall", "existing")
    print(f"\n=== Jan + gamma-wall levels through frozen gate (baseline jan_oos = +0.456R/139) ===")
    print(f"  ALL gated       {st(gt['realized_r'])}")
    for grp, sub in gt.groupby("grp"):
        print(f"  {grp:14s}  {st(sub['realized_r'])}")
    gw = gt[gt["grp"] == "gamma_wall"]
    if len(gw):
        print("\n  gamma_wall by symbol/type:")
        for (s, lt), sub in gw.groupby([gw["symbol"].astype(str), gw["level_type"].astype(str)]):
            print(f"    {s:8s} {lt:4s} {st(sub['realized_r'])}")
    print("\n  interpretation: 'existing' should land near +0.456 (cluster context shifts it slightly);")
    print("  gamma_wall = NEW trades. meanR >= ~+0.3 -> adds frequency at edge; << base -> dilution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
