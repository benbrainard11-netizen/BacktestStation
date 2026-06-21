"""CONFLUENCE score (Ben's idea): a reclaim is stronger when more independent reasons stack at its
price/moment. Two FREE full-13-month pieces (no options):
  same_asset_cluster = # of OTHER-family levels within CLUSTER_TK of this level (same sym+date)
  cross_asset_count  = # of OTHER index symbols with a reclaim TOUCH within +/-W_MIN of this touch
Tests: (1) does confluence raise reaction-R on its own? (2) does it STACK with the drift x zone edge?
Discipline: 2025 = fresh OOS (the 13mo split). liquid-3 ex opening_range.
"""
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "runs"
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
CLUSTER_TK = 6      # other-family levels within this many ticks = clustered
W_MIN = 10          # cross-asset touch window (minutes)
ONE_NS = 1_000_000_000

# 13-month scored universe (drift + zone + R) and the full reclaim context for confluence
A = pd.read_parquet(R / "mbp1_stack_features.parquet")
A["decision_ts_utc"] = pd.to_datetime(A["decision_ts_utc"], utc=True)
L = pd.read_parquet(R / "legal_bars_full.parquet")
L = L[L["symbol"].isin(TICK)].copy()
L["touch_ts_utc"] = pd.to_datetime(L["touch_ts_utc"], utc=True)
L["decision_ts_utc"] = pd.to_datetime(L["decision_ts_utc"], utc=True)
L = L[L["session_date"] >= "2025-05-01"].dropna(subset=["touch_ts_utc"])

# --- same-asset cluster: count other-family level prices within CLUSTER_TK on same sym+date ---
lvls = {}  # (sym, date) -> list of (price, family)
for (sym, date), g in L.groupby(["symbol", "session_date"]):
    lvls[(sym, date)] = list(zip(g["level_price"].to_numpy(float), g["level_family"].astype(str)))


def same_cluster(sym, date, price, fam):
    band = CLUSTER_TK * TICK[sym]
    seen = set()
    for p, f in lvls.get((sym, date), []):
        if f != fam and abs(p - price) <= band:
            seen.add(round(p / TICK[sym]))  # distinct other-family prices within band
    return len(seen)


# --- cross-asset: per-symbol sorted touch ns; count other syms with a touch within +/-W of this dec ---
touch_ns = {s: np.sort(L[L["symbol"] == s]["touch_ts_utc"].astype("int64").to_numpy()) for s in TICK}
WIN = W_MIN * 60 * ONE_NS


def cross_count(sym, dec_ns):
    c = 0
    for s in TICK:
        if s == sym:
            continue
        arr = touch_ns[s]
        i = np.searchsorted(arr, dec_ns - WIN)
        if i < len(arr) and arr[i] <= dec_ns + WIN:
            c += 1
    return c


A["same_cluster"] = [same_cluster(r.symbol, r.session_date, float(r.level_price), str(r.level_family))
                     for r in A.itertuples()]
A["cross_count"] = [cross_count(r.symbol, int(r.decision_ts_utc.value)) for r in A.itertuples()]
A["confluence"] = A["same_cluster"] + A["cross_count"]  # total stacked reasons

A = A[pd.to_numeric(A["trail_2R"], errors="coerce").abs() <= 5].copy()
A = A[A["symbol"].isin(LIQ) & (A["level_family"] != "opening_range")].copy()
A["yr"] = pd.to_datetime(A["session_date"]).dt.year
A["Rr"] = pd.to_numeric(A["trail_2R"], errors="coerce")
A["stk"] = (A["zone_5m_has"] == 1) & (pd.to_numeric(A["w90_drift_dir_ticks"], errors="coerce") >= 29.33)


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"confluence base: {len(A)} reclaims. same_cluster dist {A['same_cluster'].value_counts().sort_index().to_dict()}")
print(f"  cross_count dist {A['cross_count'].value_counts().sort_index().to_dict()}")
print(f"\n=== (1) does confluence raise reaction-R on its own (all reclaims)? ===")
for col in ["same_cluster", "cross_count", "confluence"]:
    print(f"  by {col}:")
    for v, g in A.groupby(np.where(A[col] >= 3, "3+", A[col].astype(str))):
        print(f"     {col}={v:3s}  {st(g['Rr'])}  | 2025-OOS {st(g[g['yr']==2025]['Rr'])}")
print(f"\n=== (2) does confluence STACK with drift x zone? (on the stack subset) ===")
s = A[A["stk"]]
print(f"  stack all                  {st(s['Rr'])}  | 2025-OOS {st(s[s['yr']==2025]['Rr'])}")
print(f"  stack & confluence>=2       {st(s[s['confluence']>=2]['Rr'])}  | 2025-OOS {st(s[(s['confluence']>=2)&(s['yr']==2025)]['Rr'])}")
print(f"  stack & confluence==0       {st(s[s['confluence']==0]['Rr'])}")
print(f"  stack & cross_count>=1      {st(s[s['cross_count']>=1]['Rr'])}  | 2025-OOS {st(s[(s['cross_count']>=1)&(s['yr']==2025)]['Rr'])}")
print(f"  stack & same_cluster>=1     {st(s[s['same_cluster']>=1]['Rr'])}")
A.to_parquet(R / "confluence_scored.parquet", index=False)
print(f"\nwrote runs/confluence_scored.parquet")
