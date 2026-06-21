"""THE SYNTHESIS: do the two validated 2026 orderflow edges COMPOUND or are they REDUNDANT?

Edges (each validated OOS on Apr-Jun, frozen rules):
  DRIFT  : w90_drift_dir_ticks >= 29.33                         -> +0.086 (flow_at_scale)
  ZONE   : zone_5m_has==1 AND 5m_zone_add_refill_dir <= 0.9916  -> +0.155 (flow_at_zone)
  PATIENCE (pre-frozen, generic): depth_tk>8 AND wait_s>=300

They measure different things (generic momentum into the level vs the battle at the structure zone).
Question: stacking -> stronger single selection edge, or do they overlap?

DISCIPLINE: all exploration on DESIGN (Jan-Mar 2026). The "compound vs redundant" verdict rests
mostly on (a) signal CORRELATION and (b) joint-lift CELLS on design — neither burns validation.
ONE confirmatory Apr-Jun look at the end, flagged as a WORN validation set (drift/zone/multi-moment
already evaluated there). Champions to beat: drift +0.086, zone +0.155.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
DRIFT_THR, REFILL_THR = 29.33, 0.9916

sc = pd.read_parquet(R / "flow_at_scale_features.parquet")
zn = pd.read_parquet(R / "flow_at_zone_features.parquet")
df = sc.merge(zn[KEY + ["zone_5m_has", "5m_zone_add_refill_dir", "5m_zone_absorption",
                        "5m_zone_delta_dir"]], on=KEY, how="inner", suffixes=("", "_z"))
df = df[pd.to_numeric(df["trail_2R"], errors="coerce").abs() <= 5].copy()
df["decision_ts_utc"] = pd.to_datetime(df["decision_ts_utc"], utc=True)
df["mo"] = df["decision_ts_utc"].dt.month
des = df[df["mo"].isin([1, 2, 3])].copy()
val = df[df["mo"].isin([4, 5, 6])].copy()

# the two frozen signals
for d in (des, val, df):
    d["D"] = (pd.to_numeric(d["w90_drift_dir_ticks"], errors="coerce") >= DRIFT_THR)
    d["Zform"] = (d["zone_5m_has"] == 1)
    d["Z"] = d["Zform"] & (pd.to_numeric(d["5m_zone_add_refill_dir"], errors="coerce") <= REFILL_THR)
    d["P"] = (pd.to_numeric(d["depth_tk"], errors="coerce") > 8) & (pd.to_numeric(d["wait_s"], errors="coerce") >= 300)


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=   0  (empty)"


print(f"universe: {len(df)} reclaims (2026 MBO). design(Jan-Mar)={len(des)}  val(Apr-Jun)={len(val)}")
print(f"\n=== [DESIGN] single-edge baselines ===")
print(f"  ALL                 {st(des['trail_2R'])}")
print(f"  DRIFT pass          {st(des[des.D]['trail_2R'])}")
print(f"  ZONE pass           {st(des[des.Z]['trail_2R'])}")
print(f"  PATIENCE pass       {st(des[des.P]['trail_2R'])}")

print(f"\n=== [DESIGN] REDUNDANT vs ADDITIVE: signal correlation (zone-formed subset) ===")
zf = des[des.Zform].copy()
a = pd.to_numeric(zf["w90_drift_dir_ticks"], errors="coerce")
b = -pd.to_numeric(zf["5m_zone_add_refill_dir"], errors="coerce")  # higher = cleaner zone = better
m = a.notna() & b.notna()
if m.sum() > 5:
    pr = np.corrcoef(a[m], b[m])[0, 1]
    sr = pd.Series(a[m]).rank().corr(pd.Series(b[m]).rank())
    print(f"  corr(drift, -refill) among zone-formed: Pearson {pr:+.3f}  Spearman {sr:+.3f}")
    print(f"  (near 0 => independent signals => stacking should ADD; high => redundant)")

print(f"\n=== [DESIGN] joint-lift cells: D x Z partition ===")
for label, mask in [("neither", ~des.D & ~des.Z), ("DRIFT only", des.D & ~des.Z),
                    ("ZONE only", ~des.D & des.Z), ("BOTH (D&Z)", des.D & des.Z)]:
    print(f"  {label:12s} {st(des[mask]['trail_2R'])}")

print(f"\n=== [DESIGN] funnels (does each ADD on top of the other?) ===")
print(f"  zone-formed base    {st(des[des.Zform]['trail_2R'])}")
print(f"   +DRIFT on zoneform {st(des[des.Zform & des.D]['trail_2R'])}")
print(f"  ZONE-pass base      {st(des[des.Z]['trail_2R'])}")
print(f"   +DRIFT on ZONE     {st(des[des.Z & des.D]['trail_2R'])}")
print(f"  DRIFT-pass base     {st(des[des.D]['trail_2R'])}")
print(f"   +ZONE on DRIFT     {st(des[des.D & des.Z]['trail_2R'])}")
print(f"   +PATIENCE on D&Z   {st(des[des.D & des.Z & des.P]['trail_2R'])}")

print(f"\n=== [DESIGN] combined SCORE (z(drift) + z(-refill)) on zone-formed, terciles ===")
zf = des[des.Zform].copy()
zf["zdrift"] = (pd.to_numeric(zf["w90_drift_dir_ticks"], errors="coerce")
                - a[m].mean()) / (a[m].std() + 1e-9)
zf["zclean"] = (-pd.to_numeric(zf["5m_zone_add_refill_dir"], errors="coerce")
                - b[m].mean()) / (b[m].std() + 1e-9)
zf["score"] = zf["zdrift"].fillna(0) + zf["zclean"].fillna(0)
zf["terc"] = pd.qcut(zf["score"], 3, labels=["lo", "mid", "hi"], duplicates="drop")
for t, sub in zf.groupby("terc"):
    print(f"  score {str(t):4s}  {st(sub['trail_2R'])}")

print("\n" + "=" * 70)
print("Interpretation guide: BOTH > max(DRIFT-only, ZONE-only) by >~0.1R AND low corr => COMPOUND.")
print("BOTH ~ the better single, or high corr => REDUNDANT (same trades).")
print("Pre-register the winning stack rule below, then run the ONE validation block.")
