"""Gamma walls as a LEGAL level family through the honest reclaim engine (NOT the frozen gate).

Ben's headline Q: "does mira give good reactions off gamma walls?" Answer it the disciplined way:
inject dealer call_wall (resistance) / put_wall (support) as a `gamma_wall` family into
legal_reclaim_bars (conservative fills, stop-wins-ties, no lookahead), and read honest reaction-R
against the other families' floor. NO frozen gate, NO MBO -- pure structure reaction first.

LEGALITY: wall for session D = the most recent GEX row with date < D (prior trading day; that
row is built from day-D-1 EOD greeks/OI, so knowable at D's open). Index->futures price via the
prior day's basis: futures 16:00-ET close minus (index spot * scale). DJX is quoted at 1/100 of
the Dow, so scale=100 maps DJX walls to YM points; SPX/NDX/RUT scale=1.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/gamma_wall_legal.py
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
import legal_reclaim_bars as LB  # noqa: E402
import app.data.reader as R  # noqa: E402

GEXDIR = ROOT / "experiments" / "options_signals_v0" / "out"
# future -> (index gex file, price scale to map index points -> futures points)
WALL_INDEX = {"ES.c.0": ("spx", 1.0), "NQ.c.0": ("ndx", 1.0),
              "YM.c.0": ("djx", 100.0), "RTY.c.0": ("rut", 1.0)}
# per-symbol futures-bar floor: RTY 1m bars begin 2018-05; ES/NQ/YM from 2015 (legal engine).
FUT_FLOOR = {"ES.c.0": "2015-01-02", "NQ.c.0": "2015-01-02",
             "YM.c.0": "2015-01-02", "RTY.c.0": "2018-05-01"}
# NDX has no vendor greeks pre-2026-05 -> exclude NQ from a deep run: GW_EXCLUDE=NQ.c.0
EXCLUDE = {s for s in os.environ.get("GW_EXCLUDE", "").split(",") if s}
ET16 = dt.time(16, 0)
PARTS = LB.RUNS / "gw_legal_parts"


def _gex_window(sym: str) -> tuple[str, str]:
    """Auto-derive the test window from the gex file's date EXTENT, clamped to the futures floor.
    Turnkey for a deep recompute: extend gex_levels_{idx}.parquet and the window follows — no edit."""
    idx, _ = WALL_INDEX[sym]
    g = pd.read_parquet(GEXDIR / f"gex_levels_{idx}.parquet")
    d = pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d").dt.date
    start = max(d.min(), dt.date.fromisoformat(FUT_FLOOR[sym]))
    return (start.isoformat(), d.max().isoformat())


WINDOWS = {s: _gex_window(s) for s in WALL_INDEX
           if s not in EXCLUDE and (GEXDIR / f"gex_levels_{WALL_INDEX[s][0]}.parquet").exists()}


def build_walls(sym: str) -> dict:
    """{session_date: (call_wall_fut, put_wall_fut)} in futures prices, prior-day data only."""
    idx, scale = WALL_INDEX[sym]
    tick = LB.TICK[sym]
    g = pd.read_parquet(GEXDIR / f"gex_levels_{idx}.parquet").sort_values("date")
    g["d"] = pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d").dt.date
    w0 = (pd.Timestamp(g["d"].min()) - pd.Timedelta(days=10)).date().isoformat()
    w1 = (pd.Timestamp(g["d"].max()) + pd.Timedelta(days=3)).date().isoformat()
    bars = R.read_bars(symbol=sym, timeframe="1m", start=w0, end=w1,
                       columns=["ts_event", "close"])
    bi = pd.DatetimeIndex(pd.to_datetime(bars["ts_event"], utc=True))
    bc = bars["close"].to_numpy(float)

    basis: dict = {}
    for _, row in g.iterrows():
        ts = pd.Timestamp(dt.datetime.combine(row["d"], ET16), tz=LB.ET).tz_convert("UTC")
        pos = bi.searchsorted(ts, side="right") - 1
        if pos < 0 or (ts - bi[pos]) > pd.Timedelta(minutes=30):
            continue
        basis[row["d"]] = float(bc[pos]) - float(row["spot"]) * scale

    gex_dates = [d for d in g["d"] if d in basis]
    by_date = g.set_index("d")
    sd, ed = (dt.date.fromisoformat(WINDOWS[sym][0]), dt.date.fromisoformat(WINDOWS[sym][1]))
    out: dict = {}
    d = sd
    while d <= ed:
        prior = [x for x in gex_dates if x < d]
        if prior and (d - prior[-1]).days <= 7:
            src = prior[-1]
            b = basis[src]
            cw = float(by_date.loc[src, "call_wall"]) * scale + b
            pw = float(by_date.loc[src, "put_wall"]) * scale + b
            out[d] = (round(cw / tick) * tick, round(pw / tick) * tick)
        d += dt.timedelta(days=1)
    bvals = list(basis.values())
    print(f"  {sym}({idx}x{scale:g}): {len(out)} sessions w/ walls; basis mean={np.mean(bvals):+.1f} "
          f"std={np.std(bvals):.1f}", flush=True)
    return out


WALLS = {sym: build_walls(sym) for sym in WINDOWS}
_CUR = {"sym": None}
_ORIG_DAY_LEVELS = LB.day_levels


def patched_day_levels(b, daily, day, tick):
    out = _ORIG_DAY_LEVELS(b, daily, day, tick)
    dw = WALLS.get(_CUR["sym"], {}).get(day)
    if dw:
        rth_ns = LB.et_ns(day, LB.RTH_START)
        cw, pw = dw
        if np.isfinite(cw):
            out.append(dict(level_family="gamma_wall", level_type="gwc", side="high",
                            level_price=float(cw), known_ns=rth_ns, search_ns=rth_ns))
        if np.isfinite(pw):
            out.append(dict(level_family="gamma_wall", level_type="gwp", side="low",
                            level_price=float(pw), known_ns=rth_ns, search_ns=rth_ns))
    return out


LB.day_levels = patched_day_levels


def main() -> int:
    PARTS.mkdir(parents=True, exist_ok=True)
    parts = []
    for sym in WINDOWS:
        if not WALLS[sym]:
            continue
        _CUR["sym"] = sym
        sd, ed = (dt.date.fromisoformat(WINDOWS[sym][0]), dt.date.fromisoformat(WINDOWS[sym][1]))
        for year in range(sd.year, ed.year + 1):
            y0, y1 = max(sd, dt.date(year, 1, 1)), min(ed, dt.date(year, 12, 31))
            if y0 > y1:
                continue
            part = PARTS / f"gw__{sym}__{year}.parquet"
            if part.exists():
                res = pd.read_parquet(part)
                print(f"  {sym} {year}: {len(res)} attempts (CHECKPOINT)", flush=True)
            else:
                res = LB.run_symbol_year(sym, y0, y1)
                if len(res):
                    res.to_parquet(part, index=False)
                ng = int((res["level_family"] == "gamma_wall").sum()) if len(res) else 0
                print(f"  {sym} {year}: {len(res)} attempts ({ng} gamma_wall)", flush=True)
            if len(res):
                parts.append(res)
    df = pd.concat(parts, ignore_index=True)
    out = LB.RUNS / "legal_bars_gw.parquet"
    df.to_parquet(out, index=False)

    ent = df[df["status"] == "entered"].copy()
    gw = ent[ent["level_family"] == "gamma_wall"]
    print(f"\n=== GAMMA WALLS through the HONEST engine ({len(df)} attempts, {len(ent)} entered, "
          f"{len(gw)} gamma_wall entered) ===")
    pol = "trail_2R"
    print(f"\n[{pol}]  gamma_wall vs the floor:")
    print(f"  ALL families pooled   {LB.stats(ent[pol])}")
    print(f"  gamma_wall (all)      {LB.stats(gw[pol])}")
    print(f"  gamma_wall CALL (gwc) {LB.stats(gw[gw['level_type'] == 'gwc'][pol])}")
    print(f"  gamma_wall PUT  (gwp) {LB.stats(gw[gw['level_type'] == 'gwp'][pol])}")
    print(f"\n  gamma_wall by symbol:")
    for s, sub in gw.groupby("symbol"):
        print(f"    {s:9s} {LB.stats(sub[pol])}")
    print(f"\n  for reference, other families (same pol, same windows):")
    for fam, sub in ent[ent["level_family"] != "gamma_wall"].groupby("level_family"):
        print(f"    {fam:15s} {LB.stats(sub[pol])}")
    # depth/wait splits on gamma_wall (the legal combo that helped generic levels)
    if len(gw) > 30:
        print(f"\n  gamma_wall depth/wait splits:")
        print(f"    depth>8tk        {LB.stats(gw[gw['depth_tk'] > 8][pol])}")
        print(f"    wait>=5m         {LB.stats(gw[gw['wait_s'] >= 300][pol])}")
        print(f"    depth>8 & wait>=5m {LB.stats(gw[(gw['depth_tk'] > 8) & (gw['wait_s'] >= 300)][pol])}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
