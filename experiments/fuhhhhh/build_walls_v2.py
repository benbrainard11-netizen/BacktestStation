"""Recompute deep EOD walls with the INTRADAY-CONSISTENT definition (cache-only).

The stored walls_deep uses gamma*OI split by side (call_wall = max-GEX call strike,
put_wall = max-GEX put strike) -> far-OTM put strike, ~100pt off the intraday wall
(diag_longhist_accuracy). The intraday panel (intraday_gex.py) instead uses SIGNED net
dealer gamma per strike (calls +, puts -, <=30 DTE) and takes argmax (call_wall) /
argmin (put_wall) / cumsum-crossing (zero_gamma) near spot. This builder replicates THAT
definition over the cached 2017+ EOD greeks x OI so the long-history target matches the
recent-window target. Auto-extends as the backfill fills the 2021-2022 gap.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_walls_v2.py
Artifact: out/walls_v2.parquet  [date, spot, call_wall, put_wall, zero_gamma, pin, gex_proxy]
Validation: prints |diff| vs the intraday_gex panel on overlap (should be ~0 now).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUTDIR = Path(__file__).resolve().parent / "out"
GREEKS = C.THETA_RAW / "bulk_hist_option_eod_greeks"
OI = C.THETA_RAW / "bulk_hist_option_open_interest"
DTE_MAX = 30


def scan(cache: Path, cols: list[str], spx_filter: bool) -> pd.DataFrame:
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
        if spx_filter:
            med = d["underlying_price"].median()
            yr = int(d["date"].iloc[0]) // 10000
            # SPX band [1800,8500]. SPX traded in [1800,3000) in 2017-2020, so that sub-band is
            # SPX pre-2024; but in 2024+ the same sub-band is RUT (no pre-2024 RUT in cache), so
            # drop [1800,3000) only for year>=2024. Extends SPX walls back to 2017 + fills 2021.
            if not (1800 <= med <= 8500) or (yr >= 2024 and med < 3000):
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
    gk = scan(GREEKS, ["date", "strike", "right", "expiration", "gamma", "underlying_price"], True)
    gk = gk[gk["gamma"] > 0].drop_duplicates(subset=["date", "strike", "right", "expiration"])
    oi = scan(OI, ["date", "strike", "right", "expiration", "open_interest"], False)
    oi = oi[oi["open_interest"] > 0].drop_duplicates(subset=["date", "strike", "right", "expiration"])
    j = gk.merge(oi, on=["date", "strike", "right", "expiration"], how="inner")
    print(f"joined contract-days: {len(j)}", flush=True)
    if j.empty:
        raise RuntimeError("join produced 0 rows")

    # <=30 DTE, not-yet-expired (matches intraday_gex)
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
    w.to_parquet(OUTDIR / "walls_v2.parquet")
    yrs = pd.Series(pd.to_datetime(w["date"].astype(str), format="%Y%m%d").dt.year).value_counts().sort_index()
    print(f"\nwalls_v2: {len(w)} days {w['date'].min()} -> {w['date'].max()}; days/yr {yrs.to_dict()}", flush=True)

    # VALIDATION vs intraday_gex panel (near-EOD wall) — should be ~0 now
    intr = pd.read_parquet(C.INTRADAY_GEX)
    intr_last = intr.sort_values("ms_of_day").groupby("date").last().reset_index()[
        ["date", "call_wall", "put_wall"]]
    m = w.merge(intr_last, on="date", suffixes=("_v2", "_intr"))
    if len(m):
        cwd = (m["call_wall_v2"] - m["call_wall_intr"]).abs()
        pwd = (m["put_wall_v2"] - m["put_wall_intr"]).abs()
        print(f"VALIDATION vs intraday panel ({len(m)} overlap days):")
        print(f"  call_wall |diff| median {cwd.median():.1f}pt p90 {cwd.quantile(.9):.1f}  "
              f"within5pt {(cwd <= 5).mean():.0%}")
        print(f"  put_wall  |diff| median {pwd.median():.1f}pt p90 {pwd.quantile(.9):.1f}  "
              f"within5pt {(pwd <= 5).mean():.0%}")
        print("  (old walls_deep was call~10 / put~100 median; v2 should be far smaller)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
