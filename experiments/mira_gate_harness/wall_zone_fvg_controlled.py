"""FINAL wall-zone test: among PATIENCE-MATCHED wall reclaims (the deep/patient subset that actually
forms zones), does FVG-at-wall add a REAL residual edge over the patient baseline, and is it
profitable? Controls the wait/depth confound that explained most of the headline +0.178 lift."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"

z = pd.read_parquet(RUNS / "wall_zone_react_feats.parquet")
u = pd.read_parquet(RUNS / "legal_bars_wall_full.parquet")
u = u[(u["status"] == "entered") & (u["level_family"] == "gamma_wall")].copy()
u["session_date"] = u["session_date"].astype(str)
z["session_date"] = z["session_date"].astype(str)
key = ["symbol", "session_date", "level_type", "side", "level_price"]
m = z.merge(u[key + ["wait_s", "depth_tk", "fixed_3R"]].drop_duplicates(key), on=key, how="left",
            suffixes=("", "_u"))
m = m[pd.to_numeric(m["trail_2R"], errors="coerce").abs() < 50].copy()
m["R"] = pd.to_numeric(m["trail_2R"], errors="coerce")
m["R3"] = pd.to_numeric(m["fixed_3R"], errors="coerce")
m["kind"] = m["z_5m_kind"].fillna(m["z_3m_kind"]).fillna(m["z_1m_kind"])
m["yr"] = pd.to_datetime(m["session_date"]).dt.year


def desc(x, col="R"):
    x = pd.to_numeric(x[col], errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


# PATIENT subset = the deep+patient wall reclaims (matches the operating-point depth>8 & wait>=5m spirit)
pat = m[(m["wait_s"] >= 300) & (m["depth_tk"] > 8)].copy()
print(f"PATIENT subset (wait>=300 & depth>8): {len(pat)} of {len(m)} wall reclaims")
print(f"  patient baseline (no zone req): trail2R {desc(pat)} | fixed3R {desc(pat,'R3')}")
print(f"\n=== within PATIENT, does zone KIND add edge over the patient baseline? ===")
noz = pat[pat["any_zone"] == 0]
ob = pat[(pat["any_zone"] == 1) & (pat["kind"] == "ob")]
fvg = pat[(pat["any_zone"] == 1) & (pat["kind"] == "fvg")]
print(f"  no-zone : trail2R {desc(noz)} | fixed3R {desc(noz,'R3')}")
print(f"  OB-zone : trail2R {desc(ob)} | fixed3R {desc(ob,'R3')}")
print(f"  FVG-zone: trail2R {desc(fvg)} | fixed3R {desc(fvg,'R3')}")

print(f"\n=== FVG vs no-zone WITHIN patient subset, shuffle null (patience-controlled), N=500 ===")
sub = pat[(pat["any_zone"] == 0) | (pat["kind"] == "fvg")].copy()
sub["is_fvg"] = (sub["kind"] == "fvg").astype(int)
rng = np.random.default_rng(5)


def lift(d, flag="is_fvg"):
    a = pd.to_numeric(d[d[flag] == 1]["R"], errors="coerce").dropna()
    b = pd.to_numeric(d[d[flag] == 0]["R"], errors="coerce").dropna()
    return (a.mean() - b.mean()) if len(a) and len(b) else np.nan


real = lift(sub)
null = np.array([lift(sub.assign(is_fvg=rng.permutation(sub["is_fvg"].to_numpy()))) for _ in range(500)])
null = null[np.isfinite(null)]
z_ = (real - null.mean()) / null.std() if null.std() > 0 else np.nan
print(f"  FVG-in-patient lift {real:+.4f} | null {null.mean():+.4f} +/- {null.std():.4f} | "
      f"z={z_:+.2f} p(null>=real)={float((null>=real).mean()):.3f}")

print(f"\n=== FVG-in-patient per-year + per-side (is it stable or one-off?) ===")
for y in sorted(fvg["yr"].unique()):
    g = fvg[fvg["yr"] == y]
    print(f"  {y}: {desc(g)}")
for lt, g in fvg.groupby("level_type"):
    print(f"  {('call/short' if lt=='gwc' else 'put/long')}: {desc(g)}")
des, oos = fvg[fvg["yr"] <= 2022], fvg[fvg["yr"] >= 2023]
print(f"  DESIGN<=2022 {desc(des)} | OOS>=2023 {desc(oos)}")
