"""Survivorship probe: do earnings-like gap-ups in DELISTED names drift like the SURVIVORS,
or worse? Detects the same price-gap PROXY (gap 7.5-50% + volume spike + open>prior-high) on
both universes and compares forward MARKET-RELATIVE drift (vs SPY). If delisted gaps drift
WORSE, the survivors-only earnings edge was inflated. Approximate (no earnings calendar for
delisted; ThetaData delisted EOD is RAW; final pre-delisting gap lacks forward data -> lower
bound on the harm). Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import loaders as L  # noqa: E402

HZ = [5, 10, 20, 40]
spy = L.load_etf("SPY").set_index("dt")["close"]
SURV = Path(r"D:\data\processed\stocks\daily")
DELI = Path(r"D:\data\processed\stocks\delisted")


def gaps_for_universe(folder: Path, label: str) -> pd.DataFrame:
    rows = []
    files = sorted(folder.glob("*.parquet"))
    for p in files:
        try:
            d = pd.read_parquet(p, columns=["date", "open", "high", "low", "close", "volume"])
        except Exception:
            continue
        if len(d) < 80:
            continue
        d["dt"] = pd.to_datetime(d["date"].astype(int).astype(str), format="%Y%m%d")
        d = d[d["dt"] >= "2016-01-01"].reset_index(drop=True)
        if len(d) < 80:
            continue
        o, c, hi, vol = d["open"].to_numpy(), d["close"].to_numpy(), d["high"].to_numpy(), d["volume"].to_numpy()
        pc, ph = np.roll(c, 1), np.roll(hi, 1)
        gap = o / pc - 1
        avgv = pd.Series(vol).rolling(20).mean().shift(1).to_numpy()
        for i in range(21, len(d) - max(HZ)):
            if not (0.075 <= gap[i] <= 0.50):            # earnings-like up-gap (cap 50% = drop split/error)
                continue
            if o[i] <= ph[i] or c[i - 1] < 5 or not (vol[i] >= 1.5 * avgv[i]):
                continue
            gday = d["dt"].iloc[i]
            sp, sf = spy.get(gday), spy.get(d["dt"].iloc[i + 20])
            rec = {"u": label, "ticker": p.stem}
            for H in HZ:
                spf = spy.get(d["dt"].iloc[i + H])
                rec[f"x{H}"] = (c[i + H] / o[i] - 1) - (spf / sp - 1) if (sp and spf) else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


s = gaps_for_universe(SURV, "survivors")
dl = gaps_for_universe(DELI, "delisted")
print(f"survivors gaps: {len(s)} over {s['ticker'].nunique()} names")
print(f"delisted  gaps: {len(dl)} over {dl['ticker'].nunique()} names\n")
print(f"{'universe':10s} {'n':>6} " + " ".join(f"x{H}d_%" for H in HZ) + "  win20%")
for lab, df in [("survivors", s), ("delisted", dl)]:
    if not len(df):
        print(f"{lab:10s} 0"); continue
    print(f"{lab:10s} {len(df):6d} " + " ".join(f"{df[f'x{H}'].mean()*100:+5.2f}" for H in HZ)
          + f"  {(df['x20']>0).mean()*100:4.0f}%")
if len(s) and len(dl):
    infl = s["x20"].mean() - dl["x20"].mean()
    print(f"\nSURVIVORSHIP INFLATION (survivors x20 - delisted x20): {infl*100:+.2f}%")
    print("delisted drift < survivors => the survivors-only earnings edge was inflated; the true")
    print("universe sits between (closer to survivors, since delisted are a minority of name-years).")
