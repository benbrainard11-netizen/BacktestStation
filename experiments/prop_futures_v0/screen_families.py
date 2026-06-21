"""screen_families — design-window bake-off of the pre-registered day-flat families.

Design window only (2016-01-01 .. 2025-06-09); holdout (2025-06-10+) stays sealed. Writes
out/screen_<SYM>.csv. The survivor rule is STRICTER than the ORB sweep: it adds an OUTLIER-ROBUST
term (net_R must stay > 0 after removing the top 2% of trades) — the exact guard the ORB holdout
showed was missing (its +0.086 design edge was a few trend-day outliers that vanished OOS).

Survivor (all must hold): n>=150, net_R>0, both chrono halves>0, ex-2020>0, worst_year>-0.20,
AND net_R_ex_top2pct > 0.

  python screen_families.py --symbol ES.c.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from families import run_family  # noqa: E402
from orb_engine import build_dataset, get_spec  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
START = "2016-01-01"
DESIGN_END = "2025-06-09"

GRID = {
    "gap_fade":        [dict(g=g, s=s) for g in (0.3, 0.5) for s in (0.75, 1.25)],
    "gap_cont":        [dict(g=g, s=1.0, t=t) for g in (0.3, 0.5) for t in (1.5, 2.5)],
    # k is a fraction of the daily-range ATR (the vol unit here is the daily range, so intraday
    # VWAP deviations are well below 1.0 ATR) — smoke test showed k>=1.5 never triggers.
    "vwap_revert":     [dict(k=k, s=s) for k in (0.3, 0.5) for s in (0.75, 1.25)],
    "afternoon_trend": [dict(hour_m=840, m=mm, s=s) for mm in (0.0, 0.5) for s in (1.0, 1.5)],
    "pre_rth_break":   [dict(buf_atr=b, target_R=tr) for b in (0.0, 0.05) for tr in (0.0, 2.0)],
    "accum_poc_break": [dict(ib_min=60, n_bins=30, buf_atr=b, stop_buf_atr=0.1, target_R=tr)
                        for b in (0.05, 0.1) for tr in (0.0, 2.0)],
    "accum_detect_break": [dict(win=w, c_range=0.4, c_vol=cv, buf_atr=0.05, target_R=tr)
                           for w in (20, 30) for cv in (1.0, 1.5) for tr in (0.0, 2.0)],
}


def summarize(t: pd.DataFrame) -> dict:
    if t is None or len(t) == 0:
        return {"n": 0}
    t = t.sort_values("date").reset_index(drop=True)
    r = t["net_R"].to_numpy()
    half = len(r) // 2
    by_year = t.groupby("year")["net_R"].mean()
    k = max(1, int(np.ceil(0.02 * len(r))))           # top 2% of trades
    ex_top = np.sort(r)[: len(r) - k]                  # drop the k largest
    return {
        "n": int(len(r)), "net_R": float(r.mean()), "median_R": float(np.median(r)),
        "win": float((r > 0).mean()),
        "net_R_h1": float(r[:half].mean()) if half else float("nan"),
        "net_R_h2": float(r[half:].mean()) if half else float("nan"),
        "net_R_ex2020": float(t[t["year"] != 2020]["net_R"].mean()),
        "worst_year": float(by_year.min()),
        "net_R_ex_top2pct": float(ex_top.mean()),
        "trades_per_year": float(len(r) / max(1, t["year"].nunique())),
    }


def is_survivor(r: dict) -> bool:
    return (r.get("n", 0) >= 150 and r["net_R"] > 0 and r["net_R_h1"] > 0 and r["net_R_h2"] > 0
            and r["net_R_ex2020"] > 0 and r["worst_year"] > -0.20 and r["net_R_ex_top2pct"] > 0)


def run_symbol(symbol: str, only_family: str | None = None):
    spec = get_spec(symbol)
    df = build_dataset(symbol, START, DESIGN_END)
    recs = []
    grid = GRID if only_family is None else {only_family: GRID[only_family]}
    for fam, plist in grid.items():
        for p in plist:
            s = summarize(run_family(df, spec, fam, p))
            if s.get("n", 0) == 0:
                s = {"n": 0, "net_R": float("nan"), "median_R": float("nan"), "win": float("nan"),
                     "net_R_h1": float("nan"), "net_R_h2": float("nan"), "net_R_ex2020": float("nan"),
                     "worst_year": float("nan"), "net_R_ex_top2pct": float("nan"), "trades_per_year": 0.0}
            s.update({"symbol": symbol, "family": fam, "params": str(p)})
            s["survivor"] = is_survivor(s) if s["n"] else False
            recs.append(s)
    grid = pd.DataFrame(recs)
    cols = ["symbol", "family", "params", "n", "net_R", "median_R", "win", "net_R_h1", "net_R_h2",
            "net_R_ex2020", "worst_year", "net_R_ex_top2pct", "trades_per_year", "survivor"]
    grid = grid[cols].sort_values("net_R", ascending=False)
    suffix = f"_{only_family}" if only_family else ""
    path = OUT / f"screen_{symbol.split('.')[0]}{suffix}.csv"
    grid.to_csv(path, index=False)
    print(f"\n===== {symbol}  cells={len(grid)}  survivors={int(grid['survivor'].sum())}  -> {path.name} =====")
    print(grid.head(10).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    if grid["survivor"].any():
        print("\nSURVIVORS:")
        print(grid[grid["survivor"]].to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--family", default=None)
    a = ap.parse_args()
    run_symbol(a.symbol, a.family)
