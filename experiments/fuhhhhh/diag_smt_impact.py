"""Check: is the sweep finding contaminated by the broken SMT confluence flag?

The review found SMT (ES/NQ index misalignment) = noise, so `confluence` (which counts
fired_smt) is partly garbage. Re-derive the headline sweep cell using an SMT-INDEPENDENT
'solo' = fired_sweep & ~fired_flow (ignore the broken smt flag entirely).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
OUT = Path(__file__).resolve().parent / "out"
df = pd.read_parquet(OUT / "events_v3t.parquet")


def cell(t, label):
    t = t.dropna(subset=["r_signed"])
    if len(t) < 25:
        print(f"{label}: n={len(t)} thin"); return
    bymo = t.groupby(t["date"].str.slice(0, 7))["r_signed"].mean()
    daily = t.groupby("date")["r_signed"].sum().sort_values()
    d1 = t["r_signed_d1"].dropna().mean()
    print(f"{label}: n={len(t)} meanR={t['r_signed'].mean():+.4f} "
          f"gross={(t['r_signed']+C.COST_PTS/t['stop_dist_pts']).mean():+.4f} "
          f"mo+{int((bymo>0).sum())}/{len(bymo)} dropbest5={t[~t['date'].isin(daily.index[-5:])]['r_signed'].mean():+.4f} "
          f"delayed={d1:+.4f}")


sw = df[df["fired_sweep"]]
print("-- headline cell under different 'solo' definitions (5m sweep, overshoot<=8, SHORT) --")
g = sw[(sw.swept_tf == "5m") & (sw.overshoot_tk <= 8) & (sw.dir == -1)]
cell(g[g.confluence == 1], "  confluence==1 (smt-contaminated)")
cell(g[~g.fired_flow], "  ~fired_flow (smt-independent)")
cell(g, "  all (incl confluence)")
print("\n-- broad sweep-short, smt-independent --")
cell(sw[(sw.dir == -1) & (~sw.fired_flow)], "  sweep SHORT ~flow (all TF)")
cell(sw[(sw.dir == -1) & (~sw.fired_flow) & (sw.swept_tf == "5m")], "  sweep SHORT ~flow 5m")
