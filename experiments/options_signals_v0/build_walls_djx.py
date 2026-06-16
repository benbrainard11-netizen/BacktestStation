"""DJX (Dow/100) EOD walls from cached VENDOR GREEKS (eod_greeks) x open_interest.

Generalizes fuhhhhh/build_walls_v2.py (the SPX vendor-greeks template). The ONLY change
vs that template is the file-classifier: instead of the SPX underlying band
(3000 <= median <= 8500) we classify a cached greeks file as DJX when its file-median
underlying sits in [250, 520). DJX strikes are < ~600 (collide with nothing), so the band
is trivially clean — confirmed: 315 greeks files, 507 days, underlying 301..516, dates
20240603..20260610 (DJX is RECENT-ONLY; no pre-2024 DJX greeks in cache).

Everything else is byte-for-byte build_walls_v2: cache scan -> gamma>0 -> inner-join to OI
on (date,strike,right,expiration) -> <=30 DTE not-yet-expired -> SIGNED net dealer gamma
per strike (calls +, puts -) -> argmax=call_wall / argmin=put_wall / cumsum-crossing=
zero_gamma / |net| argmax = pin / gex_proxy.

OI parquet has NO underlying_price column (cannot band-filter), so OI is pre-restricted by
strike (< 950, a memory cut only — the inner-join is anchored to the already-DJX-classified
greeks, so non-DJX OI strikes are dropped by the join regardless).

Run: backend\\.venv\\Scripts\\python.exe experiments\\options_signals_v0\\build_walls_djx.py
Artifact: experiments/options_signals_v0/out/walls_djx.parquet
          [date, spot, call_wall, put_wall, zero_gamma, pin, gex_proxy]
Index->future map (manifest): DJX -> YM.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

THETA_RAW = Path(r"D:\data\raw\thetadata")
GREEKS = THETA_RAW / "bulk_hist_option_eod_greeks"
OI = THETA_RAW / "bulk_hist_option_open_interest"
OUTDIR = Path(__file__).resolve().parent / "out"
BARS = Path(r"D:\data\processed\bars\timeframe=1m")
DTE_MAX = 30

# DJX classifier: file-median underlying in [250, 520). The band ALSO catches a second ~327-400
# product (verified via diag_djx.py: 38% of naive days had spot off vs YM by 8-28%), so a band
# filter alone is NOT enough. Real DJX = Dow/100 ~= the YM future / 100. We anchor PER DATE to
# YM and keep only greeks rows whose underlying_price is within ANCHOR_TOL of YM/100, which drops
# the contaminant using independent ground truth.
DJX_LO, DJX_HI = 250.0, 520.0
OI_STRIKE_MAX = 950.0  # memory pre-cut for OI (join anchored to greeks anyway)
ANCHOR_TOL = 0.05      # keep underlying within 5% of YM_close/100 (basis is <2%; contaminant is >8%)


def ym_daily_spot() -> pd.Series:
    """Real DJX proxy per date: last YM 1m close / 100 -> Series indexed by int yyyymmdd."""
    d = ds.dataset(BARS / "symbol=YM.c.0", format="parquet").to_table(columns=["ts_event", "close"]).to_pandas()
    d["date"] = pd.to_datetime(d["ts_event"]).dt.strftime("%Y%m%d").astype(int)
    return d.sort_values("ts_event").groupby("date")["close"].last() * 0.01


def scan_greeks(cache: Path, cols: list[str]) -> pd.DataFrame:
    """Scan cached greeks files, keeping only DJX-classified files (median band)."""
    files = sorted(cache.glob("*.parquet"))
    print(f"scanning {len(files)} files in {cache.name} (DJX band [{DJX_LO},{DJX_HI}))", flush=True)
    parts = []
    kept = 0
    for i, fp in enumerate(files):
        try:
            d = pd.read_parquet(fp, columns=cols)
        except Exception:  # noqa: BLE001
            continue
        if d.empty:
            continue
        if not (DJX_LO <= d["underlying_price"].median() < DJX_HI):
            continue
        parts.append(d)
        kept += 1
        if (i + 1) % 500 == 0:
            print(f"  ..{i + 1}/{len(files)} (kept {kept})", flush=True)
    print(f"  kept {kept} DJX greeks files", flush=True)
    return pd.concat(parts, ignore_index=True)


def scan_oi(cache: Path, cols: list[str]) -> pd.DataFrame:
    """Scan cached OI files, pre-restricting by strike (< OI_STRIKE_MAX) to cut memory."""
    files = sorted(cache.glob("*.parquet"))
    print(f"scanning {len(files)} files in {cache.name} (strike < {OI_STRIKE_MAX})", flush=True)
    parts = []
    for i, fp in enumerate(files):
        try:
            d = pd.read_parquet(fp, columns=cols)
        except Exception:  # noqa: BLE001
            continue
        if d.empty:
            continue
        d = d[d["strike"] < OI_STRIKE_MAX]
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
    print(f"DJX gamma>0 greeks rows: {len(gk)}", flush=True)
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

    # ANCHOR to YM: drop the contaminating ~327-400 product, keep only real DJX (~YM/100).
    anchor = ym_daily_spot()
    j["anchor"] = j["date"].astype(int).map(anchor)
    before = len(j)
    j = j[j["anchor"].notna()].copy()
    keep = (j["underlying_price"] - j["anchor"]).abs() / j["anchor"] <= ANCHOR_TOL
    j = j[keep].copy()
    print(f"YM-anchor: kept {len(j)}/{before} contract-days within {ANCHOR_TOL:.0%} of Dow/100", flush=True)
    if j.empty:
        raise RuntimeError("anchor filter dropped everything (YM bars missing?)")

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
    out = OUTDIR / "walls_djx.parquet"
    w.to_parquet(out)
    yrs = pd.Series(pd.to_datetime(w["date"].astype(str), format="%Y%m%d").dt.year).value_counts().sort_index()
    print(f"\nwalls_djx: {len(w)} days {w['date'].min()} -> {w['date'].max()}; days/yr {yrs.to_dict()}", flush=True)
    print(f"wrote {out}", flush=True)

    # SELF-CONSISTENCY (no SPX intraday panel for DJX): walls should bracket spot.
    cw_above = (w["call_wall"] >= w["spot"]).mean()
    pw_below = (w["put_wall"] <= w["spot"]).mean()
    print(f"spot range: {w['spot'].min():.1f}..{w['spot'].max():.1f}", flush=True)
    print(f"call_wall>=spot: {cw_above:.0%}   put_wall<=spot: {pw_below:.0%}", flush=True)
    print(f"call_wall range: {w['call_wall'].min():.0f}..{w['call_wall'].max():.0f}  "
          f"put_wall range: {w['put_wall'].min():.0f}..{w['put_wall'].max():.0f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
