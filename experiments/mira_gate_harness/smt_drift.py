"""SMT 'fully nailed': extract MBP-1 drift+aggression at BOTH the DIVERGENCE anchor (approach,
independent of confirmation) AND the DECISION anchor (confirmation strength, like reclaim's drift).
Test whether either selects a POSITIVE subset of SMT v2 entries on the 2025 fresh OOS. This is the
same treatment that rescued reclaim; if nothing crosses zero OOS, SMT is definitively dead."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flow_mbp1_stack as MS  # noqa: E402  (read_mbp1_trades, TICK, ONE_NS)

R = MS.RUNS
WIN = 90 * MS.ONE_NS
d = pd.read_parquet(R / "smt_legal_full.parquet")
d["decision_ts_utc"] = pd.to_datetime(d["decision_ts_utc"], utc=True)
d["divergence_ts_utc"] = pd.to_datetime(d["divergence_ts_utc"], utc=True)
d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() <= 5].copy()

rows = []
for (sym, day), g in d.groupby(["symbol", "session_date"]):
    if sym not in MS.TICK:
        continue
    divs = g["divergence_ts_utc"].astype("int64"); decs = g["decision_ts_utc"].astype("int64")
    try:
        ts, px, side, sz = MS.read_mbp1_trades(sym, day, int(divs.min()) - 100 * MS.ONE_NS, int(decs.max()))
    except Exception:
        continue
    tick = MS.TICK[sym]
    for r in g.itertuples():
        ds = 1 if r.side == "low" else -1
        rec = {"trail_2R": float(r.trail_2R), "symbol": sym, "session_date": day,
               "n_swept": int(r.n_swept), "side": r.side}
        for anchor, tag in ((int(pd.Timestamp(r.divergence_ts_utc).value), "div"),
                            (int(pd.Timestamp(r.decision_ts_utc).value), "dec")):
            w = (ts >= anchor - WIN) & (ts < anchor)
            if w.sum() >= 2:
                wp = px[w]
                rec[f"drift_{tag}"] = ds * (wp[-1] - wp[0]) / tick
                ws, wz = side[w], sz[w]
                buy = wz[ws == "B"].sum(); sell = wz[ws == "A"].sum(); tot = buy + sell
                rec[f"aggr_{tag}"] = ds * (buy - sell) / tot if tot > 0 else 0.0
            else:
                rec[f"drift_{tag}"], rec[f"aggr_{tag}"] = np.nan, np.nan
        rows.append(rec)

df = pd.DataFrame(rows)
df.to_parquet(R / "smt_drift.parquet", index=False)
df["yr"] = pd.to_datetime(df["session_date"]).dt.year
df["Rr"] = pd.to_numeric(df["trail_2R"], errors="coerce")
des, val = df[df["yr"] == 2026], df[df["yr"] == 2025]


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"SMT-drift base: {len(df)}  baseline {st(df['Rr'])} | 2026 {st(des['Rr'])} | 2025-OOS {st(val['Rr'])}")
print(f"\n=== does any orderflow anchor SELECT a positive subset? (design 2026 terciles + 2025-OOS top) ===")
for col in ["drift_div", "drift_dec", "aggr_div", "aggr_dec"]:
    x = pd.to_numeric(des[col], errors="coerce")
    q = x.quantile([1/3, 2/3])
    hi_des = des[x >= q.iloc[1]]
    lo_des = des[x <= q.iloc[0]]
    xv = pd.to_numeric(val[col], errors="coerce")
    hi_val = val[xv >= q.iloc[1]]  # frozen 2026 threshold applied to 2025 OOS
    print(f"  {col:9s} DESIGN top {st(hi_des['Rr'])} bot {st(lo_des['Rr'])} spread {hi_des['Rr'].mean()-lo_des['Rr'].mean():+.3f}"
          f"  | 2025-OOS top {st(hi_val['Rr'])}")
print(f"\n=== best-looking combo: high drift_div AND high drift_dec (both anchors), 2025-OOS ===")
qd = pd.to_numeric(des['drift_div'], errors='coerce').quantile(0.5)
qc = pd.to_numeric(des['drift_dec'], errors='coerce').quantile(0.5)
both = val[(pd.to_numeric(val['drift_div'], errors='coerce') >= qd) & (pd.to_numeric(val['drift_dec'], errors='coerce') >= qc)]
print(f"  drift_div>=med AND drift_dec>=med (2025-OOS): {st(both['Rr'])}")
