"""ONE-SHOT: frozen multi-moment rules on Apr-Jun validation (zone-formed).
(a) ix_sweep_aggr_x_retrace_refill >= -0.0789   (design +0.229, n=82)
(b) sw_delta_dir >= 0 AND rt_add_refill_dir <= 0.9916  (design +0.369, n=22)"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_parquet(HERE / "runs" / "multi_moment_features.parquet")
df["decision_ts_utc"] = pd.to_datetime(df["decision_ts_utc"], utc=True)
df["mo"] = df["decision_ts_utc"].dt.month
val = df[df["mo"].isin([4, 5, 6]) & (df["zone_5m_has"] == 1)].copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"VALIDATION Apr-Jun, zone-formed: baseline {st(val['trail_2R'])}")
a = val[val["ix_sweep_aggr_x_retrace_refill"] >= -0.0789]
print(f"\n(a) sweep_aggr x retrace_refill >= -0.079  (design +0.229)")
print(f"    PASS  {st(a['trail_2R'])}")
print(f"    FAIL  {st(val[val['ix_sweep_aggr_x_retrace_refill'] < -0.0789]['trail_2R'])}")
b = val[(val["sw_delta_dir"] >= 0) & (val["rt_add_refill_dir"] <= 0.9916)]
print(f"\n(b) sw_delta_dir>=0 AND rt_refill<=0.99  (design +0.369)")
print(f"    PASS  {st(b['trail_2R'])}")
