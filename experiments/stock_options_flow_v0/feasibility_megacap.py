"""FEASIBILITY READ (exploratory, free) — does single-stock dealer-gamma regime predict
next-day behavior on the 8 mega-caps whose walls we ALREADY have? No pull.

Mega-caps are the efficient end → a conservative test. If the signal shows here it should be
fatter on the inefficient mid-tier we'd pull. This does NOT touch the pre-registered mid-tier holdout.

Causal: features from walls[D] (EOD options) + daily[<=D]; targets from daily[D+1..]. Trade-able at D+1.
Bar = INCREMENTAL rank-IC over a {trailing realized vol, VIX} baseline — the signal must add beyond price.

Run: backend\\.venv\\Scripts\\python.exe -u experiments/stock_options_flow_v0/feasibility_megacap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data_io import load_polygon_daily  # noqa: E402

WALL_DIR = ROOT / "experiments" / "options_signals_v0" / "out"
NAMES = ["NVDA", "AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "META", "AVGO"]


def load_vix() -> pd.DataFrame:
    v = pd.read_parquet(WALL_DIR / "vol_indices" / "VIX.parquet")[["date", "close"]]
    return v.rename(columns={"close": "vix"}).drop_duplicates("date")


def panel_for(name: str, vix: pd.DataFrame) -> pd.DataFrame:
    w = pd.read_parquet(WALL_DIR / f"walls_{name.lower()}.parquet")
    d = load_polygon_daily(name)[["date", "open", "high", "low", "close"]].copy()
    df = d.merge(w, on="date", how="inner").merge(vix, on="date", how="left").sort_values("date").reset_index(drop=True)
    if len(df) < 80:
        return pd.DataFrame()
    c = df["close"].to_numpy(float)
    lr = np.concatenate([[np.nan], np.diff(np.log(c))])           # daily log return, causal up to D
    df["lr"] = lr
    # ---- causal features as of day D ----
    df["gex"] = df["gex_proxy"].astype(float)
    roll = df["gex"].rolling(60, min_periods=20)
    df["gex_z"] = (df["gex"] - roll.mean()) / roll.std()          # per-name normalized net dealer gamma
    df["gex_sign"] = np.sign(df["gex"])
    df["flip_side"] = np.sign(df["close"] - df["zero_gamma"])     # +1 above gamma flip (long-gamma side)
    df["d_call"] = (df["call_wall"] - df["close"]) / df["close"]  # room to call wall (+ = below it)
    df["d_put"] = (df["close"] - df["put_wall"]) / df["close"]    # room to put wall (+ = above it)
    df["pin_dist"] = (df["close"] - df["pin"]) / df["close"]
    # ---- baseline (price/vol only), causal ----
    df["rv10"] = pd.Series(lr, index=df.index).rolling(10, min_periods=5).std()
    df["mom5"] = pd.Series(lr, index=df.index).rolling(5, min_periods=3).sum()
    # ---- forward targets (D+1 and D+1..D+3) ----
    df["ret1"] = df["lr"].shift(-1)                                # next-day return (direction)
    df["absret1"] = df["ret1"].abs()                              # next-day realized-vol proxy
    fwd3 = pd.Series(lr, index=df.index).shift(-3).rolling(3).std()  # crude; replaced below
    # realized vol over next 3 days = std of lr[D+1..D+3]
    r = pd.Series(lr, index=df.index)
    df["rvol3"] = pd.concat([r.shift(-k) for k in (1, 2, 3)], axis=1).std(axis=1)
    df["name"] = name
    return df


def ic(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 50:
        return np.nan, np.nan, int(m.sum())
    rho, p = stats.spearmanr(x[m], y[m])
    return rho, p, int(m.sum())


def resid_on_baseline(y, B):
    """Residualize target y on baseline matrix B (drop rows with any NaN), return resid aligned (NaN elsewhere)."""
    y = np.asarray(y, float)
    B = np.asarray(B, float)
    m = np.isfinite(y) & np.isfinite(B).all(axis=1)
    out = np.full_like(y, np.nan)
    if m.sum() < 50:
        return out
    X = np.column_stack([np.ones(m.sum()), B[m]])
    beta, *_ = np.linalg.lstsq(X, y[m], rcond=None)
    out[m] = y[m] - X @ beta
    return out


def main() -> int:
    vix = load_vix()
    panels = [p for p in (panel_for(n, vix) for n in NAMES) if not p.empty]
    big = pd.concat(panels, ignore_index=True)
    print(f"pooled name-days: {len(big)}  names: {big['name'].nunique()}  "
          f"dates {big['date'].min()}..{big['date'].max()}\n")

    # baseline matrices
    Bvol = big[["rv10", "vix"]].to_numpy(float)
    Bdir = big[["mom5", "rv10"]].to_numpy(float)
    big["absret1_resid"] = resid_on_baseline(big["absret1"], Bvol)
    big["rvol3_resid"] = resid_on_baseline(big["rvol3"], Bvol)
    big["ret1_resid"] = resid_on_baseline(big["ret1"], Bdir)

    print("=== VOL READ: do gamma features predict next-day realized vol BEYOND {rv10, VIX}? ===")
    print(f"{'feature':10} {'rawIC vs absret1':>18} {'INCRIC vs resid':>18} {'INCRIC vs rvol3resid':>22}")
    for f in ("gex_z", "gex_sign", "flip_side", "d_call", "d_put", "pin_dist"):
        x = big[f].to_numpy(float)
        r0, p0, n0 = ic(x, big["absret1"].to_numpy(float))
        r1, p1, _ = ic(x, big["absret1_resid"].to_numpy(float))
        r2, p2, _ = ic(x, big["rvol3_resid"].to_numpy(float))
        print(f"{f:10} {r0:>9.3f}(p{p0:.0e}) {r1:>9.3f}(p{p1:.0e}) {r2:>11.3f}(p{p2:.0e})")

    print("\n=== DIRECTION READ: do wall/regime features predict next-day return BEYOND {mom5, rv10}? ===")
    print(f"{'feature':10} {'rawIC vs ret1':>16} {'INCRIC vs resid':>18}")
    for f in ("flip_side", "gex_sign", "d_call", "d_put", "pin_dist"):
        x = big[f].to_numpy(float)
        r0, p0, _ = ic(x, big["ret1"].to_numpy(float))
        r1, p1, _ = ic(x, big["ret1_resid"].to_numpy(float))
        print(f"{f:10} {r0:>9.3f}(p{p0:.0e}) {r1:>9.3f}(p{p1:.0e})")

    print("\n=== per-name incremental IC (gex_z vs absret1_resid) — is it consistent across names? ===")
    for n, g in big.groupby("name"):
        r1, p1, nn = ic(g["gex_z"].to_numpy(float), g["absret1_resid"].to_numpy(float))
        print(f"  {n:6} INCRIC={r1:>7.3f} (p={p1:.2g}, n={nn})")

    print("\nNOTE: structural prior = long gamma (positive gex) -> LOWER next-day vol, so a NEGATIVE")
    print("gex_z IC vs realized vol is the hypothesized sign. Consistency of sign across names matters")
    print("more than any single pooled number. This is EXPLORATORY (mega-cap), not the registered verdict.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
