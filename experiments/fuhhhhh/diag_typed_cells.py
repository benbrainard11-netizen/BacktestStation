"""Stability battery on the typed standout cells found in the v3t study."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
OUT = Path(__file__).resolve().parent / "out"


def battery(t: pd.DataFrame, label: str) -> None:
    t = t.dropna(subset=["r_signed"]).copy()
    if len(t) < 25:
        print(f"\n== {label} ==  n={len(t)} (thin)"); return
    cost_r = C.COST_PTS / t["stop_dist_pts"]
    bymo = t.groupby(t["date"].str.slice(0, 7))["r_signed"].mean()
    daily = t.groupby("date")["r_signed"].sum().sort_values()
    best5 = list(daily.index[-5:])
    d1 = t["r_signed_d1"].dropna()
    print(f"\n== {label} ==  n={len(t)}  meanR={t['r_signed'].mean():+.4f}  "
          f"gross={(t['r_signed'] + cost_r).mean():+.4f}  reach={t['reached'].mean():.0%}")
    print(f"  months+ {int((bymo > 0).sum())}/{len(bymo)}  "
          f"drop_best5={t[~t['date'].isin(best5)]['r_signed'].mean():+.4f}  "
          f"delayed={d1.mean():+.4f}  top3day%={daily.iloc[-3:].sum()/max(t['r_signed'].sum(),1e-9):+.0%}")


df = pd.read_parquet(OUT / "events_v3t.parquet")
sw = df[df["fired_sweep"] & (df["confluence"] == 1)]
# Rule 1: 5m-swept SHORT sweeps (the sweep carrier)
g = sw[(sw["swept_tf"] == "5m") & (sw["dir"] == -1)]
battery(g, "5m sweep SHORT (solo)")
battery(g[g["confirm_15m"]], "5m sweep SHORT + 15m-confirm")
# Rule 2: 15m SMT SHORT (the corrected SMT carrier)
sm = df[df["fired_smt"] & (df["confluence"] == 1) & (df["smt_tf"] == "15m") & (df["dir"] == -1)]
battery(sm, "15m SMT SHORT (solo)")
# Combo: 5m-sweep-short OR 15m-SMT-short
combo = pd.concat([g, sm]).drop_duplicates(subset=["date", "ms", "dir"])
battery(combo, "5m-sweep-short OR 15m-SMT-short (union)")
