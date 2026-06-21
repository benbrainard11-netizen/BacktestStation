"""OFI-predictability profile dimension for ALL 26 symbols (TBBO-based, sampled).

Computes Cont-Kukanov-Stoikov L1 order-flow-imbalance from TBBO (top-of-book size/price changes), resamples
to 1s, and measures the IC + directional accuracy vs the forward 5s mid move -- "does order flow predict price
for this asset?" Research + our phase-1: large-tick rates high (ZN/ZB ~0.3 IC, 85% dir), small-tick index low.
This generalizes that one measure to the whole universe. Sampled ~1 day every ~6 weeks (last ~14 months) to
stay tractable; cached to out/ofi_predictability.parquet for the profile system to join.

Run (background): backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/ofi_predictability.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_tbbo  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
SYMS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0", "6A.c.0", "6B.c.0", "6C.c.0", "6E.c.0", "6J.c.0", "6N.c.0",
        "6S.c.0", "CL.c.0", "BZ.c.0", "HO.c.0", "NG.c.0", "RB.c.0", "GC.c.0", "SI.c.0", "HG.c.0", "ZB.c.0",
        "ZN.c.0", "ZF.c.0", "ZT.c.0", "ZC.c.0", "ZS.c.0", "ZW.c.0"]
# ~1 sample day every ~6 weeks over the last ~14 months (mid-month -> usually a trading day)
DAYS = ["2025-02-12", "2025-03-19", "2025-04-16", "2025-05-14", "2025-06-18", "2025-07-16", "2025-08-13",
        "2025-09-17", "2025-10-15", "2025-11-12", "2025-12-17", "2026-01-14", "2026-02-11", "2026-03-18"]
FWD = 5   # forward seconds


def ofi_day(sym: str, day: str) -> pd.DataFrame | None:
    nxt = (pd.Timestamp(day) + pd.Timedelta(days=1)).date().isoformat()
    try:
        t = read_tbbo(symbol=sym, start=day, end=nxt,
                      columns=["ts_event", "bid_px", "ask_px", "bid_sz", "ask_sz"])
    except Exception:  # noqa: BLE001
        return None
    t = t.dropna(subset=["bid_px", "ask_px", "bid_sz", "ask_sz"])
    if len(t) < 5000:
        return None
    bpx, apx = t["bid_px"].to_numpy(), t["ask_px"].to_numpy()
    bsz, asz = t["bid_sz"].to_numpy(float), t["ask_sz"].to_numpy(float)
    pbpx, papx = np.r_[bpx[0], bpx[:-1]], np.r_[apx[0], apx[:-1]]
    pbsz, pasz = np.r_[bsz[0], bsz[:-1]], np.r_[asz[0], asz[:-1]]
    dW = np.where(bpx > pbpx, bsz, np.where(bpx == pbpx, bsz - pbsz, -pbsz))
    dV = np.where(apx < papx, asz, np.where(apx == papx, asz - pasz, -pasz))
    df = pd.DataFrame({"ts": pd.to_datetime(t["ts_event"].to_numpy(), utc=True),
                       "ofi": dW - dV, "mid": (bpx + apx) / 2.0}).set_index("ts")
    g = df.resample("1s")
    s = pd.DataFrame({"ofi": g["ofi"].sum(), "mid": g["mid"].last().ffill()})
    s["fwd"] = s["mid"].shift(-FWD) - s["mid"]
    return s.dropna(subset=["ofi", "fwd"])[["ofi", "fwd"]]


def main() -> int:
    rows = {}
    for i, sym in enumerate(SYMS, 1):
        t0 = time.time()
        parts = [d for day in DAYS if (d := ofi_day(sym, day)) is not None]
        if not parts:
            rows[sym] = {"ofi_ic": np.nan, "ofi_diracc": np.nan, "n_obs": 0, "n_days": 0}
            print(f"  [{i:2}/{len(SYMS)}] {sym:8} NO DATA"); continue
        d = pd.concat(parts, ignore_index=True)
        ic = float(np.corrcoef(d["ofi"], d["fwd"])[0, 1])
        nz = d["fwd"].to_numpy() != 0
        dacc = float(np.mean(np.sign(d["ofi"][nz]) == np.sign(d["fwd"][nz]))) if nz.sum() else np.nan
        rows[sym] = {"ofi_ic": ic, "ofi_diracc": dacc, "n_obs": len(d), "n_days": len(parts)}
        print(f"  [{i:2}/{len(SYMS)}] {sym:8} IC={ic:+.3f} dir={dacc:.3f}  n={len(d):>6} "
              f"({len(parts)}d, {time.time()-t0:.0f}s)")
    out = pd.DataFrame(rows).T
    out.to_parquet(OUT / "ofi_predictability.parquet")
    print(f"\nwrote {OUT/'ofi_predictability.parquet'}")
    print(out.sort_values("ofi_ic", ascending=False).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
