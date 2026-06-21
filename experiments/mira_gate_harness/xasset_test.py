"""Does the reclaim + drift x zone edge GENERALIZE to cross-asset futures (metals/energy/FX/rates/
crypto)? Per market: drift threshold at a matched percentile (frozen on 2026, applied to 2025 OOS),
since a 29-tick drift means totally different things across 6J/BTC/ZN. Structure is negative (like
indices); the test is whether the SELECTION picks a positive subset per market."""
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "runs"
PCTL = 70
d = pd.read_parquet(R / "mbp1_stack_legal_bars_xasset.parquet")
d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() <= 5].copy()
d = d[d["level_family"] != "opening_range"].copy()
d["yr"] = pd.to_datetime(d["session_date"]).dt.year
d["R"] = pd.to_numeric(d["trail_2R"], errors="coerce")
d["drift"] = pd.to_numeric(d["w90_drift_dir_ticks"], errors="coerce")
d["zf"] = d["zone_5m_has"] == 1


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=  0"


print(f"cross-asset stack test ({len(d)} reclaims, zone-rate {d['zf'].mean():.2f})")
print(f"{'market':9s} {'baseline':>20s} {'zone-formed':>20s} {'STACK 2026':>20s} {'STACK 2025-OOS':>22s}")
pos_oos = 0
summary = []
for sym, g in d.groupby("symbol"):
    z26 = g[g["zf"] & (g["yr"] == 2026)]["drift"].dropna()
    thr = float(np.percentile(z26, PCTL)) if len(z26) > 10 else 29.33
    stk = g[g["zf"] & (g["drift"] >= thr)]
    s25, s26 = stk[stk["yr"] == 2025], stk[stk["yr"] == 2026]
    print(f"{sym:9s} {st(g['R']):>20s} {st(g[g['zf']]['R']):>20s} {st(s26['R']):>20s} {st(s25['R']):>22s}")
    oos = pd.to_numeric(s25["R"], errors="coerce").dropna()
    if len(oos) >= 8 and oos.mean() > 0:
        pos_oos += 1
    summary.append((sym, len(oos), oos.mean() if len(oos) else np.nan))

print(f"\n=== generalization verdict ===")
print(f"  markets with POSITIVE 2025-OOS stack (n>=8): {pos_oos}/{len(summary)}")
allstk = pd.concat([g[g['zf'] & (g['drift'] >= (np.percentile(g[g['zf'] & (g['yr']==2026)]['drift'].dropna(), PCTL)
                    if len(g[g['zf'] & (g['yr']==2026)]) > 10 else 29.33))] for _, g in d.groupby('symbol')])
o = allstk[allstk['yr'] == 2025]
print(f"  POOLED cross-asset stack: 2025-OOS {st(o['R'])} | all {st(allstk['R'])}")
print(f"  (index reclaim stack for reference: liquid-3 2025-OOS +0.155)")
