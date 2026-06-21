"""ONE-SHOT: frozen zone-flow rule (5m_zone_add_refill_dir <= 0.9916 among zone-formed) on
EVEN-side Apr-Jun validation. Plus a sanity compare to the drift champion."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_parquet(HERE / "runs" / "flow_at_zone_features.parquet")
df["decision_ts_utc"] = pd.to_datetime(df["decision_ts_utc"], utc=True)
df["mo"] = df["decision_ts_utc"].dt.month
val = df[df["mo"].isin([4, 5, 6])].copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


zf = val[val["zone_5m_has"] == 1]
rule_col = "5m_zone_add_refill_dir"
print("VALIDATION (Apr-Jun) one-shot: zone-flow refill rule among zone-formed")
print(f"  zone-formed all      {st(zf['trail_2R'])}")
passed = zf[zf[rule_col] <= 0.9916]
print(f"  rule PASS (refill<=0.99)  {st(passed['trail_2R'])}  (design ref +0.014)")
print(f"  rule FAIL                 {st(zf[zf[rule_col] > 0.9916]['trail_2R'])}")
print(f"  no-zone (val)        {st(val[val['zone_5m_has'] == 0]['trail_2R'])}")
