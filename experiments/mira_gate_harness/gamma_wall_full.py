"""PHASE 1 of the wall+LTF-zone test: build the FULL-HISTORY wall-reclaim universe.

Inject the already-built full-history dealer walls (walls_v2/ndx/rut/djx, 2017/2018-2026, all 4
indices) as a `gamma_wall` level family through the honest reclaim engine (conservative fills,
stop-wins-ties, prior-day-legal walls). Unlike gamma_wall_legal (gex_levels, 275 days) this uses the
full wall files via wall_beyond_full.build_walls, and returns ONLY wall levels (no session families)
so the engine run is fast. Output: runs/legal_bars_wall_full.parquet -> Phase 2 detects LTF zones on it.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/gamma_wall_full.py [--smoke SYM YEAR]
"""
from __future__ import annotations

import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "backend"))
import legal_reclaim_bars as LB  # noqa: E402
import wall_beyond_full as WB  # noqa: E402  (build_walls, WALL_FILES, futures-mapped prior-day-legal)

# futures 1m-bar floor per symbol (engine can't reclaim before bars exist)
FUT_FLOOR = {"ES.c.0": "2017-01-03", "NQ.c.0": "2018-01-19",
             "YM.c.0": "2018-01-29", "RTY.c.0": "2018-05-01"}
PARTS = LB.RUNS / "gw_full_parts"
OUT = LB.RUNS / "legal_bars_wall_full.parquet"

print("=== building full-history walls (futures-mapped, prior-day-legal) ===", flush=True)
WALLS = {sym: WB.build_walls(sym) for sym in WB.WALL_FILES}
_CUR = {"sym": None}


def wall_only_day_levels(b, daily, day, tick):
    """Return ONLY the gamma walls for the day (call=resistance/short, put=support/long).
    Replaces LB.day_levels so the engine attempts wall reclaims only -> fast."""
    out = []
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


LB.day_levels = wall_only_day_levels


def run(symbols=None, years=None) -> pd.DataFrame:
    PARTS.mkdir(parents=True, exist_ok=True)
    parts = []
    for sym in (symbols or list(WB.WALL_FILES)):
        if not WALLS.get(sym):
            continue
        _CUR["sym"] = sym
        dates = sorted(WALLS[sym].keys())
        sd = max(dates[0], dt.date.fromisoformat(FUT_FLOOR[sym]))
        ed = dates[-1]
        for year in range(sd.year, ed.year + 1):
            if years and year not in years:
                continue
            y0, y1 = max(sd, dt.date(year, 1, 1)), min(ed, dt.date(year, 12, 31))
            if y0 > y1:
                continue
            part = PARTS / f"gwf__{sym}__{year}.parquet"
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
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main() -> int:
    if len(sys.argv) >= 4 and sys.argv[1] == "--smoke":
        sym, yr = sys.argv[2], int(sys.argv[3])
        df = run([sym], [yr])
        ent = df[df["status"] == "entered"] if len(df) else df
        gw = ent[ent["level_family"] == "gamma_wall"] if len(ent) else ent
        print(f"\n[smoke] {sym} {yr}: {len(df)} attempts, {len(ent)} entered, {len(gw)} gamma_wall")
        if len(gw):
            print(f"  gamma_wall trail_2R: {LB.stats(gw['trail_2R'])}")
            print(f"  by type: gwc {LB.stats(gw[gw['level_type']=='gwc']['trail_2R'])} | "
                  f"gwp {LB.stats(gw[gw['level_type']=='gwp']['trail_2R'])}")
        return 0
    df = run()
    df.to_parquet(OUT, index=False)
    ent = df[df["status"] == "entered"]
    gw = ent[ent["level_family"] == "gamma_wall"]
    yr = pd.to_datetime(gw["session_date"]).dt.year
    print(f"\n=== FULL-HISTORY wall-reclaim universe: {len(df)} attempts, {len(ent)} entered, "
          f"{len(gw)} gamma_wall entered, years {sorted(yr.unique())} ===")
    print(f"  gamma_wall trail_2R: {LB.stats(gw['trail_2R'])}")
    print(f"  gwc (call/short) {LB.stats(gw[gw['level_type']=='gwc']['trail_2R'])} | "
          f"gwp (put/long) {LB.stats(gw[gw['level_type']=='gwp']['trail_2R'])}")
    for s, sub in gw.groupby("symbol"):
        print(f"    {s:9s} {LB.stats(sub['trail_2R'])}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
