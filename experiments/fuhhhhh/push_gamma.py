"""Push the gamma-conditioned opening-drive: run-it exit + vol-clean refinement (2019-2026).

Mechanism prediction: short-gamma = dealers amplify = moves EXTEND, so following the opening
drive in short-gamma should benefit a LOT from letting winners run. Bar-level fills (tick~=bar
proven). Also refine out the vol confound (gamma adds in lo/mid vol, not hi-vol).
Rule: on short-gamma days, FOLLOW the opening drive (dir=sign(or_drive)); risk=0.5*ATR.
"""
import sys
from datetime import date as Date
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(43)
OPEN_MS = 9 * 3600_000 + 30 * 60_000
DEC_MS = 9 * 3600_000 + 45 * 60_000
EOD_MS = 16 * 3600_000
RISK_ATR = 0.5
COMM = C.COMMISSION_RT / C.POINT_VALUE_NQ

od = pd.read_parquet(OUT / "open_dataset.parquet").dropna(subset=["or_drive_atr"]).copy()
od["d"] = pd.to_datetime(od["date"])
w = pd.read_parquet(OUT / "walls_v2.parquet")
w["d"] = pd.to_datetime(w["date"].astype(int).astype(str), format="%Y%m%d")
m = pd.merge_asof(od.sort_values("d"), w[["d", "gex_proxy"]].sort_values("d"),
                  on="d", direction="backward", allow_exact_matches=False)
m = m.dropna(subset=["gex_proxy"]).reset_index(drop=True)
m["short_gamma"] = m["gex_proxy"] < 0
m["vol_b"] = pd.qcut(m["atr"], 3, labels=["lo", "mid", "hi"])
sg = m[m.short_gamma & (m.or_drive_atr.abs() > 1e-9)].copy()
print(f"short-gamma trade-days: {len(sg)}")


def sim_day(day, entry, direction, risk):
    df = D.load_bars_sym(C.BARS_1M_NQ, day)
    if df is None:
        return None
    f = df[(df["et"] >= D.et_ts(day, DEC_MS)) & (df["et"] < D.et_ts(day, EOD_MS))]
    if len(f) < 5:
        return None
    hi, lo, cl = f["high"].to_numpy(float), f["low"].to_numpy(float), f["close"].to_numpy(float)
    out = {}
    for nm, tgtR, trailR in [("fix1R", 1.0, None), ("tgt3R", 3.0, None), ("trail1R", None, 1.0), ("holdEOD", None, None)]:
        if direction > 0:
            stop = entry - risk
            if trailR is not None:
                tstop = np.maximum.accumulate(np.concatenate([[entry], hi[:-1]])) - trailR * risk
                lvl = np.maximum(stop, tstop)
                hit = np.argmax(lo <= lvl) if (lo <= lvl).any() else None
                ex = lvl[hit] if hit is not None else cl[-1]
            else:
                tgt = entry + tgtR * risk if tgtR else np.inf
                hs = np.argmax(lo <= stop) if (lo <= stop).any() else None
                ht = np.argmax(hi >= tgt) if (hi >= tgt).any() else None
                ex = cl[-1] if hs is None and ht is None else (stop if ht is None else (tgt if hs is None else (stop if hs <= ht else tgt)))
            out[nm] = (ex - entry) / risk - COMM / risk
        else:
            stop = entry + risk
            if trailR is not None:
                tstop = np.minimum.accumulate(np.concatenate([[entry], lo[:-1]])) + trailR * risk
                lvl = np.minimum(stop, tstop)
                hit = np.argmax(hi >= lvl) if (hi >= lvl).any() else None
                ex = lvl[hit] if hit is not None else cl[-1]
            else:
                tgt = entry - tgtR * risk if tgtR else -np.inf
                hs = np.argmax(hi >= stop) if (hi >= stop).any() else None
                ht = np.argmax(lo <= tgt) if (lo <= tgt).any() else None
                ex = cl[-1] if hs is None and ht is None else (stop if ht is None else (tgt if hs is None else (stop if hs <= ht else tgt)))
            out[nm] = (entry - ex) / risk - COMM / risk
    return out


rows = []
for _, s in sg.iterrows():
    r = sim_day(Date.fromisoformat(s.date), float(s.entry), float(np.sign(s.or_drive_atr)), RISK_ATR * float(s.atr))
    if r:
        rows.append({"date": s.date, "yr": s.yr, "vol_b": s.vol_b, **r})
f = pd.DataFrame(rows)
EX = ["fix1R", "tgt3R", "trail1R", "holdEOD"]


def show(df, lab):
    print(f"\n{lab} (n={len(df)})")
    for e in EX:
        r = df[e].to_numpy(); byyr = df.groupby("yr")[e].mean()
        days = df.date.to_numpy(); by = {d: r[days == d] for d in np.unique(days)}
        bm = np.array([np.concatenate([by[d] for d in RNG.choice(list(by), len(by), True)]).mean() for _ in range(2000)])
        print(f"  {e:8s} meanR={r.mean():+.4f} p={ (bm<=0).mean():.3f} win%={(r>0).mean()*100:.0f} yrs+={int((byyr>0).sum())}/{len(byyr)}")


show(f, "ALL short-gamma (follow drive)")
show(f[f.vol_b != "hi"], "short-gamma + lo/mid vol (vol-clean)")
