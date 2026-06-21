"""Can we test trigger->wall over a LONG history? Deep EOD walls go back to 2019, even
though intraday options features only exist for 11 months. A prior-day wall is a valid
intraday TARGET (a known price level) regardless of intraday gamma dynamics.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

walls = pd.read_parquet(C.WALLS_DEEP)
walls["d"] = pd.to_datetime(walls["date"].astype(int).astype(str), format="%Y%m%d").dt.date
print(f"deep EOD walls (walls_deep): {len(walls)} days, {walls['d'].min()} -> {walls['d'].max()}")
print(f"  columns: {list(walls.columns)}")
yrs = pd.Series([d.year for d in walls['d']]).value_counts().sort_index()
print(f"  days/year: {yrs.to_dict()}")

es_days = sorted(p.name.split("=")[1] for p in C.BARS_1M.glob("date=*"))
es_2019 = [d for d in es_days if d >= "2019-08-21" and pd.Timestamp(d).dayofweek < 5]
print(f"\nES 1m bar weekday sessions 2019-08+: {len(es_2019)} ({es_2019[0]}..{es_2019[-1]})")

# basis sanity over the deep history: prior-day ES close - SPX spot, sampled per year
print("\nES-SPX basis (prior-day ES close - walls_deep spot), sampled:")
wl = walls.set_index("d")
for yr in (2019, 2020, 2021, 2022, 2023, 2024, 2025):
    samp = [d for d in es_2019 if d.startswith(str(yr))]
    if not samp:
        continue
    bases = []
    for ds in samp[::20]:
        d = pd.Timestamp(ds).date()
        if d not in wl.index:
            continue
        p = C.BARS_1M / f"date={ds}" / "part-000.parquet"
        if not p.exists():
            continue
        b = pd.read_parquet(p, columns=["close"])
        bases.append(float(b["close"].iloc[-1]) - float(wl.loc[d, "spot"]))
    if bases:
        print(f"  {yr}: n={len(bases)}  basis mean {np.mean(bases):+.1f}  "
              f"min {np.min(bases):+.1f}  max {np.max(bases):+.1f}")

# MBP-1 (order flow) coverage — the part that's SHORT even in the long history
mbp_days = sorted(p.name.split("=")[1] for p in C.MBP1_ES.glob("date=*"))
print(f"\nMBP-1 order-flow coverage: {mbp_days[0]}..{mbp_days[-1]} ({len(mbp_days)} days)")
print("=> long-history triggers (sweep/SMT, bar-based) work 2019+; order-flow features only 2025-05+")
