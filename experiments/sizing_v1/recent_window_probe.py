"""Probe recent Mira candidate yield by day/symbol before full export."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "live_engine" / "engine"))

import detect as D  # noqa: E402
import gate as G  # noqa: E402

OPP = "combined.sweep_setup_event_id"
SYMS = ["ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0"]


def date_range(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def probe_one(symbol: str, day: dt.date, gate: G.Gate) -> dict[str, object]:
    c = D.compute_candidates(symbol, day, day, sweep_quality=None)
    if c is None or c.empty:
        return {"symbol": symbol, "day": day.isoformat(), "rows": 0, "types": {}, "pss_l": 0, "pss_s": 0, "g_l": 0, "g_s": 0}
    types = Counter(c["trigger_type"].astype(str).fillna("na"))
    c["trigger_ts_utc"] = pd.to_datetime(c["trigger_ts_utc"], utc=True)
    pss = c[
        (c["trigger_type"] == "post_sweep_smt")
        & (c["smt_anchor_side"].isin(["low", "high"]))
        & c["trigger_price"].notna()
    ].copy()
    if OPP in pss.columns:
        pss = pss[pss[OPP].notna()].copy()
    pss_l = int((pss["smt_anchor_side"] == "low").sum()) if len(pss) else 0
    pss_s = int((pss["smt_anchor_side"] == "high").sum()) if len(pss) else 0
    g_l = g_s = 0
    if len(pss):
        pss["gate_score"] = gate.score(pss)
        gated = pss[pss["gate_score"] >= gate.threshold].copy()
        if OPP in gated.columns and len(gated):
            gated = gated.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").groupby(OPP, sort=False).head(1)
        g_l = int((gated["smt_anchor_side"] == "low").sum())
        g_s = int((gated["smt_anchor_side"] == "high").sum())
    return {"symbol": symbol, "day": day.isoformat(), "rows": len(c), "types": dict(types), "pss_l": pss_l, "pss_s": pss_s, "g_l": g_l, "g_s": g_s}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--end", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--symbols", default=",".join(SYMS))
    args = parser.parse_args()
    symbols = [part.strip() for part in args.symbols.split(",") if part.strip()]
    gate = G.Gate()
    print(f"gate threshold={gate.threshold:.4f}")
    grand = np.zeros(4, dtype=int)
    for day in date_range(args.start, args.end):
        day_tot = np.zeros(4, dtype=int)
        print(f"\n=== {day} ===")
        for symbol in symbols:
            rec = probe_one(symbol, day, gate)
            day_tot += np.array([rec["pss_l"], rec["pss_s"], rec["g_l"], rec["g_s"]], dtype=int)
            print(
                f"{symbol:8s} rows={rec['rows']:4d} types={rec['types']} "
                f"pss L/S={rec['pss_l']}/{rec['pss_s']} gated L/S={rec['g_l']}/{rec['g_s']}"
            )
        grand += day_tot
        print(f"TOTAL pss L/S={day_tot[0]}/{day_tot[1]} gated L/S={day_tot[2]}/{day_tot[3]} longs_only={day_tot[2]}")
    print(f"\nGRAND pss L/S={grand[0]}/{grand[1]} gated L/S={grand[2]}/{grand[3]} longs_only={grand[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
