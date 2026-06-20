"""v0 signal test on the mid-tier pilot — train/validate ONLY (sealed holdout untouched).

Tests BOTH families on the inefficient tier, with the same confound controls that deflated the
mega-cap read:
  GAMMA -> VOL : do gamma-wall/regime features predict next-day & 3d realized vol, INCREMENTALLY
                 over {rv10, rv20, VIX, mom5, mom20, dist20high}? (price-structure controlled)
  FLOW  -> DIR : do options-flow features predict next-day return, INCREMENTALLY over {mom5, mom20, rv10}?

Causal: features as of day D, targets at D+1.. . HARD SEAL: only dates < HOLDOUT_START are touched here.
Run: backend\\.venv\\Scripts\\python.exe -u experiments/stock_options_flow_v0/signal_v0.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from data_io import load_polygon_daily  # noqa: E402
from feasibility_megacap import ic, load_vix, resid_on_baseline  # noqa: E402

WALLS = ROOT / "experiments" / "options_signals_v0" / "out"
FLOW = HERE / "out"
HOLDOUT_START = 20250701  # SEALED. Nothing >= this is read here. Registered verdict runs separately, once.
UNIVERSE = [ln.strip() for ln in (HERE / "universe_pilot.txt").read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


def panel(t: str, vix: pd.DataFrame) -> pd.DataFrame:
    wf, ff = WALLS / f"walls_{t.lower()}.parquet", FLOW / f"flow_{t.lower()}.parquet"
    if not wf.exists() and not ff.exists():
        return pd.DataFrame()
    d = load_polygon_daily(t)
    if d is None or d.empty:
        return pd.DataFrame()
    d = d[["date", "open", "high", "low", "close"]].copy()
    df = d.merge(vix, on="date", how="left")
    if wf.exists():
        df = df.merge(pd.read_parquet(wf), on="date", how="inner", suffixes=("", "_w"))
    if ff.exists():
        fl = pd.read_parquet(ff).drop(columns=["ticker"], errors="ignore")
        df = df.merge(fl, on="date", how="left", suffixes=("", "_f"))
    df = df.sort_values("date").reset_index(drop=True)
    df = df[df["date"] < HOLDOUT_START]                      # HARD SEAL
    if len(df) < 80:
        return pd.DataFrame()
    r = pd.Series(np.log(df["close"]).diff().to_numpy(), index=df.index)
    # baselines
    df["rv10"], df["rv20"] = r.rolling(10, min_periods=5).std(), r.rolling(20, min_periods=10).std()
    df["mom5"], df["mom20"] = r.rolling(5, min_periods=3).sum(), r.rolling(20, min_periods=10).sum()
    df["dist20high"] = (df["close"].rolling(20, min_periods=10).max() - df["close"]) / df["close"]
    # targets
    df["ret1"] = r.shift(-1)
    df["absret1"] = df["ret1"].abs()
    df["rvol3"] = pd.concat([r.shift(-k) for k in (1, 2, 3)], axis=1).std(axis=1)
    # gamma features (causal)
    if "gex_proxy" in df:
        roll = df["gex_proxy"].rolling(60, min_periods=20)
        df["gex_z"] = (df["gex_proxy"] - roll.mean()) / roll.std()
        df["flip_side"] = np.sign(df["close"] - df["zero_gamma"])
        df["d_call"] = (df["call_wall"] - df["close"]) / df["close"]
        df["d_put"] = (df["close"] - df["put_wall"]) / df["close"]
        df["pin_dist"] = (df["close"] - df["pin"]) / df["close"]
    # flow features (causal) -> logs/normalized
    for col in ("cp_vol_ratio", "cp_dollar_ratio", "cp_oi_ratio", "vol_oi", "atm_cp_vol"):
        if col in df:
            df["l_" + col] = np.log(df[col].clip(lower=1e-3))
    if "delta_flow" in df:
        z = df["delta_flow"].rolling(60, min_periods=20)
        df["delta_flow_z"] = (df["delta_flow"] - z.mean()) / z.std()
    df["ticker"] = t
    return df


def report(big: pd.DataFrame, feats, target, B, label):
    big = big.copy()
    big["_resid"] = resid_on_baseline(big[target], big[B].to_numpy(float))
    print(f"\n=== {label} (n={big['_resid'].notna().sum()}, train<{HOLDOUT_START}) ===")
    print(f"{'feature':16} {'rawIC':>14} {'INCR-IC vs baseline':>22}")
    for f in feats:
        if f not in big:
            continue
        x = big[f].to_numpy(float)
        r0, p0, _ = ic(x, big[target].to_numpy(float))
        r1, p1, n1 = ic(x, big["_resid"].to_numpy(float))
        print(f"{f:16} {r0:>7.3f}(p{p0:.0e}) {r1:>9.3f}(p{p1:.0e})  n={n1}")


def main() -> int:
    vix = load_vix()
    parts = [p for p in (panel(t, vix) for t in UNIVERSE) if not p.empty]
    if not parts:
        print("no panels yet — build walls (build_walls_stock per name, cache-only) + build_flow first")
        return 1
    big = pd.concat(parts, ignore_index=True)
    print(f"pooled name-days: {len(big)}  names: {big['ticker'].nunique()} "
          f"({sorted(big['ticker'].unique())})  dates {big['date'].min()}..{big['date'].max()}")

    # vol baseline uses per-stock ATM IV (full coverage + the proper 'beyond IV' control), not VIX
    # (VIX only covers 2024+, which would silently drop all of 2023 from the gamma test).
    Bvol = ["rv10", "rv20", "atm_iv", "mom5", "mom20", "dist20high"]
    gamma_feats = ["gex_z", "flip_side", "d_call", "d_put", "pin_dist"]
    report(big, gamma_feats, "rvol3", Bvol, "GAMMA -> 3d realized VOL")
    report(big, gamma_feats, "absret1", Bvol, "GAMMA -> next-day |ret|")

    Bdir = ["mom5", "mom20", "rv10"]
    flow_feats = ["l_cp_vol_ratio", "l_cp_dollar_ratio", "net_call_share", "delta_flow_z",
                  "l_vol_oi", "l_atm_cp_vol", "l_cp_oi_ratio"]
    report(big, flow_feats, "ret1", Bdir, "FLOW -> next-day RETURN (direction)")

    print("\n=== per-name INCR-IC, best gamma feature (d_call->rvol3) & flow (net_call_share->ret1) ===")
    bigv = big.copy(); bigv["_rv"] = resid_on_baseline(bigv["rvol3"], bigv[Bvol].to_numpy(float))
    bigd = big.copy(); bigd["_rd"] = resid_on_baseline(bigd["ret1"], bigd[Bdir].to_numpy(float))
    for t, g in big.groupby("ticker"):
        gv = bigv[bigv["ticker"] == t]; gd = bigd[bigd["ticker"] == t]
        rv = ic(gv["d_call"].to_numpy(float), gv["_rv"].to_numpy(float)) if "d_call" in g else (np.nan,)*3
        rd = ic(gd["net_call_share"].to_numpy(float), gd["_rd"].to_numpy(float)) if "net_call_share" in g else (np.nan,)*3
        print(f"  {t:6} gamma d_call->rvol3 INCRIC={rv[0]:>7.3f}  flow ncs->ret1 INCRIC={rd[0]:>7.3f}")
    print("\nEXPLORATORY (train only). A clear, sign-consistent INCR-IC here justifies the v1 backtest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
