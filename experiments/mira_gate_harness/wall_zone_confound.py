"""Is the wall+LTF-zone lift REAL, or a proxy for a simpler covariate (price lingered at the wall ->
more wait/depth -> mechanically better reclaim)? Merge zone flags with the wall universe's patience
features and test: (a) is zone-formed just longer-wait/deeper? (b) does zone still lift WITHIN
wait/depth buckets? (c) does a wait/depth filter alone reproduce the lift (zone redundant)?
(d) FVG-standalone shuffle null at its own n."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
POL = "trail_2R"

z = pd.read_parquet(RUNS / "wall_zone_react_feats.parquet")
u = pd.read_parquet(RUNS / "legal_bars_wall_full.parquet")
u = u[(u["status"] == "entered") & (u["level_family"] == "gamma_wall")].copy()
u["session_date"] = u["session_date"].astype(str)
key = ["symbol", "session_date", "level_type", "side", "level_price"]
z["session_date"] = z["session_date"].astype(str)
m = z.merge(u[key + ["wait_s", "depth_tk", "risk_tk"]].drop_duplicates(key), on=key, how="left")
m = m[pd.to_numeric(m[POL], errors="coerce").abs() < 50].copy()
m["R"] = pd.to_numeric(m[POL], errors="coerce")


def mean(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return x.mean() if len(x) else np.nan


print(f"merged {len(m)} (wait/depth non-null {m['wait_s'].notna().sum()})")
zf, nz = m[m["any_zone"] == 1], m[m["any_zone"] == 0]
print(f"\n(a) is zone-formed just more patient/deeper?")
print(f"  zone-formed: wait_s med {zf['wait_s'].median():.0f} depth_tk med {zf['depth_tk'].median():.1f} "
      f"risk_tk med {zf['risk_tk'].median():.1f}")
print(f"  no-zone    : wait_s med {nz['wait_s'].median():.0f} depth_tk med {nz['depth_tk'].median():.1f} "
      f"risk_tk med {nz['risk_tk'].median():.1f}")

print(f"\n(b) does zone still lift WITHIN wait_s terciles? (if yes -> not just a patience proxy)")
m["wbucket"] = pd.qcut(m["wait_s"].rank(method="first"), 3, labels=["wait_lo", "wait_mid", "wait_hi"])
for b, g in m.groupby("wbucket"):
    a, n = g[g["any_zone"] == 1], g[g["any_zone"] == 0]
    print(f"  {b} (wait {g['wait_s'].min():.0f}-{g['wait_s'].max():.0f}s): "
          f"zone {mean(a['R']):+.3f} (n{len(a)}) | none {mean(n['R']):+.3f} (n{len(n)}) | "
          f"lift {mean(a['R'])-mean(n['R']):+.3f}")
print(f"  within-depth terciles:")
m["dbucket"] = pd.qcut(m["depth_tk"].rank(method="first"), 3, labels=["dep_lo", "dep_mid", "dep_hi"])
for b, g in m.groupby("dbucket"):
    a, n = g[g["any_zone"] == 1], g[g["any_zone"] == 0]
    print(f"  {b}: zone {mean(a['R']):+.3f} (n{len(a)}) | none {mean(n['R']):+.3f} (n{len(n)}) | "
          f"lift {mean(a['R'])-mean(n['R']):+.3f}")

print(f"\n(c) does a PATIENCE filter alone reproduce the +0.178 zone lift? (zone redundant if so)")
for feat in ["wait_s", "depth_tk"]:
    hi = m[m[feat] >= m[feat].median()]
    lo = m[m[feat] < m[feat].median()]
    print(f"  {feat}>=median: {mean(hi['R']):+.3f} (n{len(hi)}) | <median {mean(lo['R']):+.3f} | "
          f"lift {mean(hi['R'])-mean(lo['R']):+.3f}")
# zone lift AFTER also requiring high patience -> does zone add on top of patience?
hp = m[m["wait_s"] >= m["wait_s"].median()]
a, n = hp[hp["any_zone"] == 1], hp[hp["any_zone"] == 0]
print(f"  WITHIN high-wait: zone {mean(a['R']):+.3f} (n{len(a)}) | none {mean(n['R']):+.3f} | "
      f"lift {mean(a['R'])-mean(n['R']):+.3f}  <- zone adds on top of patience?")

print(f"\n(d) FVG-standalone: is +0.049 (n316) real vs a label-shuffle null?")
m["is_fvg"] = (m["z_5m_kind"].fillna(m["z_3m_kind"]).fillna(m["z_1m_kind"]) == "fvg").astype(int)
rng = np.random.default_rng(3)
real = mean(m[m["is_fvg"] == 1]["R"]) - mean(m[m["is_fvg"] == 0]["R"])
null = []
for _ in range(500):
    p = rng.permutation(m["is_fvg"].to_numpy())
    null.append(mean(m[p == 1]["R"]) - mean(m[p == 0]["R"]))
null = np.array(null)
print(f"  fvg lift {real:+.4f} | null {null.mean():+.4f} +/- {null.std():.4f} | "
      f"z={(real-null.mean())/null.std():+.2f} p={float((null>=real).mean()):.3f}")
