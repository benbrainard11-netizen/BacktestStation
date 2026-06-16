"""Build RUT (Russell 2000) dealer-gamma walls from cached VENDOR GREEKS + open_interest.

Generalizes experiments/fuhhhhh/build_walls_v2.py (the SPX vendor-greeks template) to RUT.
The scan / scan-join / <=30 DTE / signed-net-gamma argmax(call_wall)/argmin(put_wall) /
cumsum-crossing(zero_gamma) / argmax|net|(pin) / gex_proxy logic is byte-for-byte identical;
the ONLY change is the per-root classifier on the greeks scan.

ROOT CLASSIFIER (validated against the cache, NOT the task's draft spec):
  RUT  := file underlying-median in [1100, 3000)  AND  trade-year >= 2024.
  - DJX (median ~300-516) excluded by the 1100 lower bound.
  - SPX excluded: in 2024-2026 SPX traded 4700-6100, well above the 3000 upper bound, so the
    [1100,3000) band in those years is pure Russell. (Pre-2024 the same 2200-2800 band is SPX
    — 2017-2020 SPX — which is why the year>=2024 gate is required. There is NO RUT data in this
    cache before 2024-06; the draft spec's "2017 start / 877 days / median<2200 OR ...<2650"
    classifier swept in 356 SPX-2017 files + DJX and is wrong. Verified: this classifier yields
    exactly 783 greeks files / 507 trade-days / 20240603..20260610, spot tracks Russell 2000.)

OI side: open_interest parquet has no underlying_price (cannot band-filter); pre-restrict by
strike (900<=strike<2950 covers Russell chains), drop_duplicates, then inner-join to the
already-root-classified greeks on (date,strike,right,expiration) -- the join is anchored to
correctly-classified greeks so OI just attaches matching rows.

Run: backend\\.venv\\Scripts\\python.exe experiments\\options_signals_v0\\build_walls_rut.py
Artifact: out/walls_rut.parquet  [date, spot, call_wall, put_wall, zero_gamma, pin, gex_proxy]
Index->future map: RUT -> RTY.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

THETA_RAW = Path(r"D:\data\raw\thetadata")
OUTDIR = Path(__file__).resolve().parent / "out"
GREEKS = THETA_RAW / "bulk_hist_option_eod_greeks"
OI = THETA_RAW / "bulk_hist_option_open_interest"
DTE_MAX = 30

# RUT root classifier (see module docstring)
RUT_MED_LO, RUT_MED_HI = 1100.0, 3000.0
RUT_MIN_YEAR = 2024
# OI strike pre-restriction (memory cut; the inner-join to classified greeks is the real filter)
RUT_OI_STRIKE_LO, RUT_OI_STRIKE_HI = 900.0, 2950.0


def scan_greeks(cache: Path, cols: list[str]) -> pd.DataFrame:
    """Scan greeks files, keep only RUT (underlying band + year>=2024)."""
    files = sorted(cache.glob("*.parquet"))
    print(f"scanning {len(files)} files in {cache.name}", flush=True)
    parts = []
    for i, fp in enumerate(files):
        try:
            d = pd.read_parquet(fp, columns=cols)
        except Exception:  # noqa: BLE001
            continue
        if d.empty:
            continue
        med = d["underlying_price"].median()
        if not (RUT_MED_LO <= med < RUT_MED_HI):
            continue
        year = int(d["date"].iloc[0]) // 10000
        if year < RUT_MIN_YEAR:
            continue
        parts.append(d)
        if (i + 1) % 500 == 0:
            print(f"  ..{i + 1}/{len(files)}", flush=True)
    print(f"  RUT greeks files kept: {len(parts)}", flush=True)
    return pd.concat(parts, ignore_index=True)


def scan_oi(cache: Path, cols: list[str]) -> pd.DataFrame:
    """Scan OI files; pre-restrict by strike (no underlying_price to band on)."""
    files = sorted(cache.glob("*.parquet"))
    print(f"scanning {len(files)} files in {cache.name}", flush=True)
    parts = []
    for i, fp in enumerate(files):
        try:
            d = pd.read_parquet(fp, columns=cols)
        except Exception:  # noqa: BLE001
            continue
        if d.empty:
            continue
        d = d[(d["strike"] >= RUT_OI_STRIKE_LO) & (d["strike"] < RUT_OI_STRIKE_HI)]
        if d.empty:
            continue
        parts.append(d)
        if (i + 1) % 500 == 0:
            print(f"  ..{i + 1}/{len(files)}", flush=True)
    return pd.concat(parts, ignore_index=True)


def _zero_gamma(strikes: np.ndarray, prof: np.ndarray) -> float:
    cum = np.cumsum(prof)
    x = np.where(np.diff(np.sign(cum)) != 0)[0]
    if not len(x):
        return float("nan")
    i = x[0]
    if cum[i] == cum[i + 1]:
        return float(strikes[i])
    return float(np.interp(0, [cum[i], cum[i + 1]], [strikes[i], strikes[i + 1]]))


def main() -> int:
    gk = scan_greeks(GREEKS, ["date", "strike", "right", "expiration", "gamma", "underlying_price"])
    gk = gk[gk["gamma"] > 0].drop_duplicates(subset=["date", "strike", "right", "expiration"])
    oi = scan_oi(OI, ["date", "strike", "right", "expiration", "open_interest"])
    oi = oi[oi["open_interest"] > 0].drop_duplicates(subset=["date", "strike", "right", "expiration"])
    j = gk.merge(oi, on=["date", "strike", "right", "expiration"], how="inner")
    print(f"joined contract-days: {len(j)}", flush=True)
    if j.empty:
        raise RuntimeError("join produced 0 rows")

    # <=30 DTE, not-yet-expired (matches intraday_gex / build_walls_v2)
    dd = pd.to_datetime(j["date"].astype(int).astype(str), format="%Y%m%d")
    de = pd.to_datetime(j["expiration"].astype(int).astype(str), format="%Y%m%d")
    dte = (de - dd).dt.days
    j = j[(dte >= 0) & (dte <= DTE_MAX)].copy()
    sign = np.where(j["right"].astype(str).str.upper().str[0] == "C", 1.0, -1.0)
    j["net"] = j["gamma"].to_numpy(float) * j["open_interest"].to_numpy(float) * sign  # signed dealer gamma

    rows = []
    for dt_, g in j.groupby("date"):
        spot = float(g["underlying_price"].median())
        per = g.groupby("strike")["net"].sum().sort_index()
        if len(per) < 5:
            continue
        strikes = per.index.to_numpy(float)
        prof = per.to_numpy(float)
        aprof = g.groupby("strike")["net"].apply(lambda s: s.abs().sum()).reindex(per.index).to_numpy(float)
        rows.append({
            "date": int(dt_), "spot": spot,
            "call_wall": float(strikes[np.argmax(prof)]),
            "put_wall": float(strikes[np.argmin(prof)]),
            "zero_gamma": _zero_gamma(strikes, prof),
            "pin": float(strikes[np.argmax(aprof)]),
            "gex_proxy": float((prof * spot * spot * 0.01 * 100).sum()),
        })
    w = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    OUTDIR.mkdir(exist_ok=True)
    w.to_parquet(OUTDIR / "walls_rut.parquet")
    yrs = pd.Series(pd.to_datetime(w["date"].astype(str), format="%Y%m%d").dt.year).value_counts().sort_index()
    print(f"\nwalls_rut: {len(w)} days {w['date'].min()} -> {w['date'].max()}; days/yr {yrs.to_dict()}", flush=True)

    # sanity: walls should bracket spot
    below = (w["put_wall"] <= w["spot"]).mean()
    above = (w["call_wall"] >= w["spot"]).mean()
    print(f"sanity: put_wall<=spot {below:.0%}  call_wall>=spot {above:.0%}  "
          f"spot[{w['spot'].min():.0f},{w['spot'].max():.0f}]", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
