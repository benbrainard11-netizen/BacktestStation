"""Fast read: does NQ's OWN (NDX) gamma condition its opening drive better than SPX gamma?
Recent overlap only (walls_ndx exists 2025-09+). Descriptive corr + follow-rule R (small n).
If NDX-own doesn't clearly beat SPX here, own-gamma doesn't rescue the edge (ES+own already weak).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
od = pd.read_parquet(OUT / "open_dataset.parquet").dropna(subset=["or_drive_atr", "fwd_eod_atr", "r_long", "r_short"]).copy()
od["d"] = pd.to_datetime(od["date"])
# NDX own gamma (daily walls_ndx, prior-day)
wn = pd.read_parquet(OUT / "walls_ndx.parquet")
wn["d"] = pd.to_datetime(wn["date"].astype(int).astype(str), format="%Y%m%d")
wn = wn.sort_values("d")[["d", "gex_proxy"]].rename(columns={"gex_proxy": "ndx_gex"})
# SPX gamma (walls_v2, prior-day)
ws = pd.read_parquet(OUT / "walls_v2.parquet")
ws["d"] = pd.to_datetime(ws["date"].astype(int).astype(str), format="%Y%m%d")
ws = ws.sort_values("d")[["d", "gex_proxy"]].rename(columns={"gex_proxy": "spx_gex"})

m = pd.merge_asof(od.sort_values("d"), wn, on="d", direction="backward", allow_exact_matches=False)
m = pd.merge_asof(m.sort_values("d"), ws, on="d", direction="backward", allow_exact_matches=False)
m = m.dropna(subset=["ndx_gex", "spx_gex"]).reset_index(drop=True)
m["vol_b"] = pd.qcut(m["atr"], 3, labels=["lo", "mid", "hi"])
lm = m[m.vol_b != "hi"]
print(f"recent overlap with BOTH NDX+SPX gamma: {len(m)} days ({m.date.min()}..{m.date.max()})")
print(f"  agreement NDX<0 vs SPX<0: {(np.sign(m.ndx_gex)==np.sign(m.spx_gex)).mean():.2f}")


def c(s):
    return np.corrcoef(s["or_drive_atr"], s["fwd_eod_atr"])[0, 1] if len(s) > 20 else np.nan
def followR(s):
    d = np.sign(s["or_drive_atr"]); return np.where(d > 0, s["r_long"], s["r_short"])


print("\n### corr(or_drive, fwd_eod) by regime (lo/mid vol), NDX-own vs SPX")
for nm, col in [("NDX-own", "ndx_gex"), ("SPX", "spx_gex")]:
    sg = lm[lm[col] < 0]; lg = lm[lm[col] >= 0]
    rsg = followR(sg)
    print(f"  {nm:8s}: short-gamma corr={c(sg):+.3f} (n={len(sg)}) followR={rsg.mean():+.4f}  |  long-gamma corr={c(lg):+.3f} (n={len(lg)})")
print("\n(small recent n — directional read only; ES+own-gamma already weak over full history)")
