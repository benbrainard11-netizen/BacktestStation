"""Discipline check on the gamma-wall reaction: temporal design/validation split + generic ref.
The patience filter (wait>=5m) is ALREADY frozen (task #17, generic levels even-yr). Here we ask:
does gamma_wall + wait>=5m hold on a never-looked-at later slice, and does it beat the SAME filter
on generic levels in the SAME window? Split: design <= 2026-02-28, validation >= 2026-03-01."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_parquet(HERE / "runs" / "legal_bars_gw.parquet")
ent = df[df["status"] == "entered"].copy()
ent["d"] = pd.to_datetime(ent["session_date"]).dt.date
SPLIT = pd.Timestamp("2026-03-01").date()
gw = ent[ent["level_family"] == "gamma_wall"]
gen = ent[ent["level_family"] != "gamma_wall"]
pol = "trail_2R"


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


def split(sub, label):
    de, va = sub[sub["d"] < SPLIT], sub[sub["d"] >= SPLIT]
    print(f"  {label:34s} design {st(de[pol])}   | VALID {st(va[pol])}")


print("=== gamma_wall reaction: temporal design(<=Feb26)/validation(>=Mar26) ===")
split(gw, "gamma_wall (all)")
split(gw[gw["wait_s"] >= 300], "gamma_wall wait>=5m  [frozen]")
split(gw[(gw["depth_tk"] > 8) & (gw["wait_s"] >= 300)], "gamma_wall depth>8 & wait>=5m")
split(gw[gw["level_type"] == "gwp"], "gamma_wall PUT (support/long)")
split(gw[(gw["level_type"] == "gwp") & (gw["wait_s"] >= 300)], "gamma_wall PUT & wait>=5m")
print("\n=== same frozen filter on GENERIC levels (apples-to-apples reference) ===")
split(gen[gen["wait_s"] >= 300], "generic wait>=5m")
split(gen[(gen["depth_tk"] > 8) & (gen["wait_s"] >= 300)], "generic depth>8 & wait>=5m")
print("\n=== per-symbol gamma_wall + wait>=5m (pooled both halves) ===")
for s, sub in gw[gw["wait_s"] >= 300].groupby("symbol"):
    print(f"  {s:9s} {st(sub[pol])}")
