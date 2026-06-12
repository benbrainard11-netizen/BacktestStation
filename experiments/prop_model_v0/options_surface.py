"""SPX EOD options-surface features from the RAW theta cache — CACHE-ONLY scan.

Reads every landed bulk_hist_option_eod_greeks parquet directly (never touches the
Theta Terminal — the other session's backfill owns it). Root classified by
underlying_price magnitude (SPX 3000-8000). Per trading date, the documented
surface features the model has never seen (walls were just 2 numbers; this is the
surface): ATM IV at ~30d tenor, term slope (60d+ vs <=10d ATM IV), risk-reversal
skew (OTM put IV - OTM call IV at 2-5% moneyness, 20-60 DTE), put/call VOLUME
ratio (flow), total volume, and ATM IV change. Coverage = whatever the newest-first
backfill has landed; report prints it.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/options_surface.py
Artifact: data/spx_surface.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
CACHE = Path("D:/data/raw/thetadata/bulk_hist_option_eod_greeks")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def day_features(g: pd.DataFrame) -> dict:
    """Surface stats for one (date) group of SPX contract rows."""
    s = float(g["underlying_price"].median())
    m = g["strike"].to_numpy(float) / s - 1.0
    dte = (
        pd.to_datetime(g["expiration"].astype(str), format="%Y%m%d")
        - pd.to_datetime(str(int(g["date"].iloc[0])), format="%Y%m%d")
    ).dt.days.to_numpy()
    iv = g["implied_vol"].to_numpy(float)
    vol = g["volume"].to_numpy(float)
    right = g["right"].astype(str).str.upper().str[0].to_numpy()
    ok = (iv > 0.01) & (iv < 3.0)
    out = {"spot": s}
    atm30 = iv[ok & (np.abs(m) <= 0.01) & (dte >= 20) & (dte <= 45)]
    atm_near = iv[ok & (np.abs(m) <= 0.01) & (dte >= 1) & (dte <= 10)]
    atm_far = iv[ok & (np.abs(m) <= 0.01) & (dte >= 60) & (dte <= 120)]
    out["ox_atm_iv30"] = float(np.median(atm30)) if len(atm30) >= 3 else np.nan
    out["ox_term_slope"] = (
        float(np.median(atm_far) - np.median(atm_near))
        if len(atm_near) >= 3 and len(atm_far) >= 3
        else np.nan
    )
    putw = iv[
        ok & (right == "P") & (m <= -0.02) & (m >= -0.05) & (dte >= 20) & (dte <= 60)
    ]
    callw = iv[
        ok & (right == "C") & (m >= 0.02) & (m <= 0.05) & (dte >= 20) & (dte <= 60)
    ]
    out["ox_skew"] = (
        float(np.median(putw) - np.median(callw))
        if len(putw) >= 3 and len(callw) >= 3
        else np.nan
    )
    pv, cv = float(vol[right == "P"].sum()), float(vol[right == "C"].sum())
    out["ox_pc_vol"] = pv / cv if cv > 0 else np.nan
    out["ox_tot_vol"] = pv + cv
    return out


def main() -> int:
    files = sorted(CACHE.glob("*.parquet"))
    print(f"scanning {len(files)} cached eod_greeks files (cache-only, no Terminal)")
    parts = []
    for i, fp in enumerate(files):
        try:
            d = pd.read_parquet(
                fp,
                columns=[
                    "date",
                    "strike",
                    "right",
                    "expiration",
                    "implied_vol",
                    "volume",
                    "underlying_price",
                ],
            )
        except Exception:  # noqa: BLE001
            continue
        if d.empty:
            continue
        u = d["underlying_price"].median()
        if not (3000 <= u <= 8500):  # SPX band (NDX ~5-figure, RUT ~2k, DJX ~3-figure)
            continue
        parts.append(d)
        if (i + 1) % 300 == 0:
            print(f"  ..{i + 1}/{len(files)}")
    if not parts:
        raise RuntimeError("no SPX rows found in cache")
    allr = pd.concat(parts, ignore_index=True)
    allr = allr.drop_duplicates(subset=["date", "strike", "right", "expiration"])
    print(f"SPX contract-day rows: {len(allr)}")
    rows = []
    for dt_, g in allr.groupby("date"):
        r = day_features(g)
        r["date"] = int(dt_)
        rows.append(r)
    f = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    f["ox_iv_chg5"] = f["ox_atm_iv30"].diff(5)
    f["ox_pc_vol_z20"] = (f["ox_pc_vol"] - f["ox_pc_vol"].rolling(20).mean()) / f[
        "ox_pc_vol"
    ].rolling(20).std()
    f["ox_vol_z20"] = (f["ox_tot_vol"] - f["ox_tot_vol"].rolling(20).mean()) / f[
        "ox_tot_vol"
    ].rolling(20).std()
    (MODULE / "data").mkdir(exist_ok=True)
    f.to_parquet(MODULE / "data" / "spx_surface.parquet")
    cov = f.dropna(subset=["ox_atm_iv30"])
    print(
        f"surface days: {len(f)} total, {len(cov)} with ATM IV "
        f"({cov['date'].min()} -> {cov['date'].max()})"
    )
    print(f.describe().loc[["mean", "50%"]].round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
