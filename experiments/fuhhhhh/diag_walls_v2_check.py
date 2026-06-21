"""Re-validate walls_v2 with the CORRECT day pairing + check near-spot sensibility.

intraday_gex panel for trade-day D uses the D-1 chain repriced at day-D spot. walls_v2
for date D uses day-D's own EOD chain. So the right comparison is:
  intraday_panel[D] @ OPEN   vs   walls_v2[D-1]
(both ~ the D-1 chain at ~D-1-close spot). And the long-history requirement isn't an
exact match — it's that the put_wall (short-side target) sits NEAR spot, not far-OTM.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

v2 = pd.read_parquet(Path(__file__).resolve().parent / "out" / "walls_v2.parquet")
old = pd.read_parquet(C.WALLS_DEEP)

# near-spot sensibility: distance of each wall from spot (points)
for name, w in (("walls_v2 (new defn)", v2), ("walls_deep (old defn)", old)):
    cw = (w["call_wall"] - w["spot"])
    pw = (w["spot"] - w["put_wall"])
    print(f"{name}: call_wall above spot median {cw.median():+.0f}pt (p90 {cw.quantile(.9):.0f}); "
          f"put_wall below spot median {pw.median():+.0f}pt (p90 {pw.quantile(.9):.0f})")

# correct-pairing validation: intraday[D]@open vs v2[D-1]
intr = pd.read_parquet(C.INTRADAY_GEX)
op = intr.sort_values("ms_of_day").groupby("date").first().reset_index()[["date", "call_wall", "put_wall"]]
op["d"] = pd.to_datetime(op["date"].astype(int).astype(str), format="%Y%m%d").dt.date
v2x = v2.copy()
v2x["d"] = pd.to_datetime(v2x["date"].astype(int).astype(str), format="%Y%m%d").dt.date
v2map = v2x.set_index("d")
v2days = sorted(v2map.index)
import bisect
rows = []
for _, r in op.iterrows():
    j = bisect.bisect_left(v2days, r["d"]) - 1     # most recent v2 day strictly before D
    if j < 0:
        continue
    pv = v2map.loc[v2days[j]]
    rows.append((abs(r["call_wall"] - pv["call_wall"]), abs(r["put_wall"] - pv["put_wall"])))
arr = np.array(rows)
print(f"\ncorrect-pairing  intraday[D]@open vs walls_v2[D-1]  (n={len(arr)}):")
print(f"  call_wall |diff| median {np.median(arr[:,0]):.1f}pt  within5pt {(arr[:,0]<=5).mean():.0%}  "
      f"within10 {(arr[:,0]<=10).mean():.0%}")
print(f"  put_wall  |diff| median {np.median(arr[:,1]):.1f}pt  within5pt {(arr[:,1]<=5).mean():.0%}  "
      f"within10 {(arr[:,1]<=10).mean():.0%}")
