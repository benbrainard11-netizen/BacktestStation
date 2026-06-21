"""The 13-month drift x zone stack (bars + MBP-1). 2025 (May-Dec) = FRESH OOS the MBO never saw.
FIX: absolute drift>=29.33 ticks is mis-calibrated across symbols (NQ passes 13x more than ES). Use
a PER-SYMBOL drift threshold at a matched percentile, FROZEN on 2026, applied to 2025 (no leakage).
Liquid-3, ex opening_range."""
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "runs"
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
PCTL = 70  # per-symbol drift percentile among zone-formed (matched selectivity ~ top 30%)

d = pd.read_parquet(R / "mbp1_stack_features.parquet")
d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() <= 5].copy()
d = d[d["symbol"].isin(LIQ) & (d["level_family"] != "opening_range")].copy()
d["dt"] = pd.to_datetime(d["session_date"])
d["yr"] = d["dt"].dt.year
d["q"] = d["dt"].dt.to_period("Q").astype(str)
d["R"] = pd.to_numeric(d["trail_2R"], errors="coerce")
d["drift"] = pd.to_numeric(d["w90_drift_dir_ticks"], errors="coerce")
d["zf"] = d["zone_5m_has"] == 1

# per-symbol drift threshold FROZEN on 2026 zone-formed (the developed window), applied to 2025 OOS
thr = {}
for s in LIQ:
    z26 = d[(d["symbol"] == s) & d["zf"] & (d["yr"] == 2026)]["drift"].dropna()
    thr[s] = float(np.percentile(z26, PCTL)) if len(z26) > 10 else 29.33
d["thr"] = d["symbol"].map(thr)
d["stk"] = d["zf"] & (d["drift"] >= d["thr"])
d["stk_abs"] = d["zf"] & (d["drift"] >= 29.33)  # old absolute rule for contrast


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"13mo stack (liquid-3 ex OR): {len(d)} reclaims, symbols={d['symbol'].value_counts().to_dict()}")
print(f"per-symbol drift thresholds (P{PCTL} of 2026 zone-formed, frozen): "
      + ", ".join(f"{s[:2]}={v:.0f}tk" for s, v in thr.items()))
print(f"\n=== KEY TEST: 2025 FRESH-OOS vs 2026, PER-SYMBOL threshold ===")
print(f"  2025 May-Dec [FRESH OOS]  {st(d[d['stk'] & (d['yr']==2025)]['R'])}")
print(f"  2026 Jan-Jun              {st(d[d['stk'] & (d['yr']==2026)]['R'])}")
print(f"  POOLED 13mo               {st(d[d['stk']]['R'])}")
print(f"  (old ABSOLUTE 29.33: 2025 {st(d[d['stk_abs'] & (d['yr']==2025)]['R'])}  pooled {st(d[d['stk_abs']]['R'])})")

print(f"\n=== per-symbol stack (13mo, per-symbol threshold) — is it balanced now? ===")
for s, g in d.groupby("symbol"):
    print(f"  {s:8s} 2025 {st(g[g['stk'] & (g['yr']==2025)]['R'])}  | 2026 {st(g[g['stk'] & (g['yr']==2026)]['R'])}")

print(f"\n=== stack by quarter (per-symbol threshold) ===")
for q, g in d.groupby("q"):
    print(f"  {q}  {st(g[g['stk']]['R'])}")
n, mo = int(d["stk"].sum()), d["dt"].dt.to_period("M").nunique()
print(f"\n  frequency: {n} stack trades / {mo}mo = {n/mo:.1f}/mo")
