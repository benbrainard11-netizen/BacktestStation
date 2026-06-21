"""Diagnose why the drift x zone STACK inverts on RTY, + exit comparison.
Prime suspect: drift threshold is an ABSOLUTE tick value (29.33) across 4 symbols with very
different tick/vol -> miscalibrated for RTY. Test a per-symbol vol-normalized drift (z-score from
DESIGN stats, applied to validation = no leakage)."""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
DRIFT_THR, REFILL_THR = 29.33, 0.9916
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}

sc = pd.read_parquet(R / "flow_at_scale_features.parquet")
zn = pd.read_parquet(R / "flow_at_zone_features.parquet")
df = sc.merge(zn[KEY + ["zone_5m_has", "5m_zone_add_refill_dir"]], on=KEY, how="inner")
df = df[pd.to_numeric(df["trail_2R"], errors="coerce").abs() <= 5].copy()
df["mo"] = pd.to_datetime(df["decision_ts_utc"], utc=True).dt.month
df["drift"] = pd.to_numeric(df["w90_drift_dir_ticks"], errors="coerce")
df["Zform"] = df["zone_5m_has"] == 1
df["D"] = df["drift"] >= DRIFT_THR
df["stk"] = df["Zform"] & df["D"]


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0          "


print("=== A) per-symbol decomposition (ALL 2026) — where does RTY break? ===")
print(f"{'sym':8s} {'baseline':>20s} {'drift-alone':>20s} {'zone-formed':>20s} {'STACK':>20s} {'ctrl drift|nozone':>22s}")
for s, g in df.groupby("symbol"):
    print(f"{s:8s} {st(g['trail_2R']):>20s} {st(g[g['D']]['trail_2R']):>20s} "
          f"{st(g[g['Zform']]['trail_2R']):>20s} {st(g[g['stk']]['trail_2R']):>20s} "
          f"{st(g[g['D'] & ~g['Zform']]['trail_2R']):>22s}")

print("\n=== B) drift calibration per symbol (is 29.33 ticks the wrong bar for RTY?) ===")
print(f"{'sym':8s} {'tick':>6s} {'drift med':>10s} {'drift std':>10s} {'%pass>=29.33':>13s}  stack-pass R")
for s, g in df.groupby("symbol"):
    dd = g["drift"].dropna()
    print(f"{s:8s} {TICK[s]:>6.2f} {dd.median():>10.1f} {dd.std():>10.1f} {100*(dd>=DRIFT_THR).mean():>12.1f}%  "
          f"{st(g[g['stk']]['trail_2R'])}")

print("\n=== C) VOL-NORMALIZED drift: per-symbol z-score (DESIGN stats -> applied OOS) ===")
des = df[df["mo"].isin([1, 2, 3])]
stats = des.groupby("symbol")["drift"].agg(["mean", "std"])
df = df.merge(stats.rename(columns={"mean": "dmean", "std": "dstd"}), on="symbol", how="left")
df["drift_z"] = (df["drift"] - df["dmean"]) / (df["dstd"] + 1e-9)
ZTHR = 0.43  # design-chosen to match the original ~33% drift pass-rate
df["Dz"] = df["drift_z"] >= ZTHR
df["stkz"] = df["Zform"] & df["Dz"]
val = df[df["mo"].isin([4, 5, 6])]
print(f"  z-threshold {ZTHR} (design-chosen). tick-abs vs vol-norm STACK per symbol:")
print(f"{'sym':8s} {'tick-abs STACK all26':>22s} {'VOLNORM STACK all26':>22s} {'volnorm STACK VAL':>22s}")
for s in TICK:
    g, gv = df[df["symbol"] == s], val[val["symbol"] == s]
    print(f"{s:8s} {st(g[g['stk']]['trail_2R']):>22s} {st(g[g['stkz']]['trail_2R']):>22s} "
          f"{st(gv[gv['stkz']]['trail_2R']):>22s}")
print(f"\n  POOLED tick-abs stack: all26 {st(df[df['stk']]['trail_2R'])}  | VAL {st(val[val['stk']]['trail_2R'])}")
print(f"  POOLED vol-norm stack: all26 {st(df[df['stkz']]['trail_2R'])}  | VAL {st(val[val['stkz']]['trail_2R'])}")

print("\n=== D) EXIT comparison on the (tick-abs) stack: trail_2R vs fixed_3R ===")
for pol in ["trail_2R", "fixed_3R"]:
    if pol not in df.columns:
        print(f"  {pol}: column missing"); continue
    print(f"  {pol:10s} stack all26 {st(df[df['stk']][pol])}  | VAL {st(val[val['stk']][pol])}")
