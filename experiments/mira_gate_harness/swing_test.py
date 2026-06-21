"""Does drift x zone select a positive subset on intraday SWING-level reclaims (the 'more levels'
frequency lever)? Per swing-TF (5m/15m/30m) + pooled, per-symbol drift threshold (P70 frozen on 2026,
applied to 2025 OOS). Reports the STACK edge AND the frequency (trades/month) each TF adds."""
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "runs"
PCTL = 70
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
d = pd.read_parquet(R / "mbp1_stack_swing_levels_full.parquet")
d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() <= 5].copy()
d["yr"] = pd.to_datetime(d["session_date"]).dt.year
d["R"] = pd.to_numeric(d["trail_2R"], errors="coerce")
d["drift"] = pd.to_numeric(d["w90_drift_dir_ticks"], errors="coerce")
d["zf"] = d["zone_5m_has"] == 1
mo = pd.to_datetime(d["session_date"]).dt.to_period("M").nunique()

# per-symbol drift threshold frozen on 2026 zone-formed
thr = {}
for s in LIQ:
    z = d[(d["symbol"] == s) & d["zf"] & (d["yr"] == 2026)]["drift"].dropna()
    thr[s] = float(np.percentile(z, PCTL)) if len(z) > 30 else 29.33
d["stk"] = d["zf"] & (d["drift"] >= d["symbol"].map(thr))


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):5d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"swing-level stack ({len(d)} reclaims, zone-rate {d['zf'].mean():.2f}). per-sym drift thr {dict((k[:2],round(v,0)) for k,v in thr.items())}")
print(f"\n=== by swing-TF: baseline | STACK 2026 | STACK 2025-OOS | trades/mo ===")
for fam, g in d.groupby("level_family"):
    s = g[g["stk"]]
    s25, s26 = s[s["yr"] == 2025], s[s["yr"] == 2026]
    print(f"  {fam:9s} base {st(g['R'])} | STK26 {st(s26['R'])} | STK25-OOS {st(s25['R'])} | {len(s)/mo:5.0f}/mo")
allstk = d[d["stk"]]
o = allstk[allstk["yr"] == 2025]
print(f"\n=== POOLED swing stack ===")
print(f"  2025-OOS {st(o['R'])} | all {st(allstk['R'])} | {len(allstk)/mo:.0f} trades/mo")
print(f"  by symbol (2025-OOS): " + " ".join(f"{s[:2]}:{st(allstk[(allstk['symbol']==s)&(allstk['yr']==2025)]['R'])}" for s in LIQ))
print(f"\n  reference: standard-family index stack = +0.155 OOS, ~18.5/mo")
print(f"  -> if swing OOS > 0 at high freq, THIS is the frequency unlock")
