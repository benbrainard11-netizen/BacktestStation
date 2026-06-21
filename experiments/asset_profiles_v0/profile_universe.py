"""26-asset behavioral profile + strategy-routing system (the 'asset DNA' the user asked for).

For each symbol in the macro futures universe, compute a behavioral profile vector:
  DAILY (from the daily-return panel): annualized vol, return autocorr (trend>0 / reversal<0),
    variance ratio (>1 trend / <1 mean-revert), beta to the equal-weight common factor (systematic-ness),
    mean correlation to its own group (RV-partner availability).
  INTRADAY (from 5-min bars, comparable to the NQ 4H live edge): variance ratio + lag-1 autocorr of 5m
    returns, and the SWEEP-RECLAIM-RUNNER response -- gross trail-1R expectancy, % months positive, and
    90th-pct MFE in R (does this asset EXPAND after a sweep? the NQ-vs-ES axis from the validated edge).
Then cluster assets on the standardized profile (do equity/rates/energy/fx/metals/grains fall out naturally
or does behavior cross the nominal lines?), and build a transparent routing table mapping each asset to its
best-fit strategy: sweep-reclaim-runner / RV-cointegration / OFI-execution overlay.

Honest framing: this is DESCRIPTIVE + ROUTING (which strategy fits which asset), not a black-box predictor
(those failed). The sweep-reclaim numbers are gross (cost ~negligible at HTF scale) and R-normalized so they
compare across instruments without tick tables.

Run: backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/profile_universe.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
PANEL = Path(__file__).resolve().parents[1] / "sync_regime_v0" / "out" / "daily_returns.parquet"
START, END = "2023-01-01", "2026-04-23"
LB, K, HOLD, TRAIL = 48, 6, 48, 1.0            # 5m bars: 4h level / 30m reclaim / 4h hold / 1R trail
# MBP-1 phase-1 OFI->price IC (VALIDATED). The TBBO shortcut for all-26 FAILED (didn't reproduce ZN/ZB's
# +0.35 -> trade-sampled book != MBP-1) so it's discarded; the other 19 need the proper MBP-1 OFI build.
OFI_IC = {"ZN.c.0": 0.346, "ZB.c.0": 0.359, "CL.c.0": 0.185, "ES.c.0": 0.024,
          "NQ.c.0": 0.018, "YM.c.0": 0.020, "RTY.c.0": 0.017}

GROUP = {}
for g, mem in {
    "equity": ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"],
    "fx": ["6A.c.0", "6B.c.0", "6C.c.0", "6E.c.0", "6J.c.0", "6N.c.0", "6S.c.0"],
    "energy": ["CL.c.0", "BZ.c.0", "HO.c.0", "NG.c.0", "RB.c.0"],
    "metals": ["GC.c.0", "SI.c.0", "HG.c.0"],
    "rates": ["ZB.c.0", "ZN.c.0", "ZF.c.0", "ZT.c.0"],
    "grains": ["ZC.c.0", "ZS.c.0", "ZW.c.0"],
}.items():
    for s in mem:
        GROUP[s] = g


def variance_ratio(x: np.ndarray, q: int) -> float:
    x = x[~np.isnan(x)]
    if len(x) < q * 5 or x.var() == 0:
        return np.nan
    xq = np.convolve(x, np.ones(q), "valid")
    return float((xq.var() / q) / x.var())


def daily_profile(R: pd.DataFrame) -> pd.DataFrame:
    factor = R.mean(axis=1)
    fvar = factor.var()
    rows = {}
    for s in R.columns:
        x = R[s]
        members = [m for m in R.columns if GROUP.get(m) == GROUP.get(s) and m != s]
        rows[s] = {
            "group": GROUP.get(s, "?"),
            "ann_vol": float(x.std() * np.sqrt(252)),
            "ac1_d": float(x.autocorr(1)),
            "vr_d": variance_ratio(x.to_numpy(), 5),
            "beta_factor": float(np.cov(x, factor)[0, 1] / fvar),
            "corr_group": float(R[members].corrwith(x).mean()) if members else np.nan,
        }
    return pd.DataFrame(rows).T


def coint_partners(R: pd.DataFrame) -> pd.DataFrame:
    """Count within-group Engle-Granger cointegrated partners (p<0.05) -> RV-strategy suitability.
    Uses cumsum of log-returns as an affine log-price proxy (cointegration is invariant to the constant)."""
    try:
        from statsmodels.tsa.stattools import coint
    except ImportError:
        print("  (statsmodels missing -> coint_partners=NaN)")
        return pd.DataFrame({s: {"coint_partners": np.nan} for s in R.columns}).T
    logP = R.cumsum()
    out = {}
    for s in R.columns:
        members = [m for m in R.columns if GROUP.get(m) == GROUP.get(s) and m != s]
        cnt = 0
        for m in members:
            try:
                if coint(logP[s], logP[m])[1] < 0.05:
                    cnt += 1
            except Exception:  # noqa: BLE001
                pass
        out[s] = {"coint_partners": cnt}
    return pd.DataFrame(out).T


def sweep_reclaim(b: pd.DataFrame) -> dict:
    """Confirmed-sweep -> reclaim -> tight wick stop -> 1R trailing exit, gross, R-normalized."""
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ts = b.index
    n = len(b)
    lvl = b["low"].rolling(LB, min_periods=LB // 2).min().shift(1).to_numpy()
    pen = l < lvl
    fresh = pen & ~np.r_[False, pen[:-1]]
    starts = np.where(fresh & ~np.isnan(lvl))[0]
    rs, dates, mfes = [], [], []
    for t0 in starts:
        L = lvl[t0]
        t_r = next((t for t in range(t0, min(t0 + K, n - 1) + 1) if c[t] > L), -1)
        if t_r < 0:
            continue
        entry, stop = c[t_r], l[t0:t_r + 1].min()
        risk = entry - stop
        if risk <= 0:
            continue
        end = min(t_r + HOLD, n - 1)
        peak, tstop, r, mfe = entry, stop, None, 0.0
        for t in range(t_r + 1, end + 1):
            mfe = max(mfe, (h[t] - entry) / risk)
            if l[t] <= tstop:
                r = (tstop - entry) / risk
                break
            peak = max(peak, h[t])
            tstop = max(tstop, peak - TRAIL * risk)
        rs.append((c[end] - entry) / risk if r is None else r)
        dates.append(ts[t_r])
        mfes.append(mfe)
    if len(rs) < 50:
        return {"sweep_er": np.nan, "sweep_pctm": np.nan, "mfe90": np.nan, "n_sweep": len(rs)}
    rs = np.array(rs)
    ym = pd.DatetimeIndex(dates).tz_localize(None).to_period("M")
    monthly = pd.Series(rs).groupby(ym).mean()
    return {"sweep_er": float(rs.mean()), "sweep_pctm": float((monthly > 0).mean()),
            "mfe90": float(np.quantile(mfes, 0.9)), "n_sweep": len(rs)}


def intraday_profile(sym: str) -> dict:
    try:
        b = read_bars(symbol=sym, timeframe="5m", start=START, end=END)
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:40]}
    if len(b) < 2000:
        return {"n_sweep": 0}
    b = b.set_index("ts_event")[["open", "high", "low", "close", "volume"]].sort_index()
    b = b[~b.index.duplicated(keep="first")]
    r5 = np.log(b["close"]).diff().to_numpy()
    out = {"vr_5m": variance_ratio(r5, 12), "ac1_5m": float(pd.Series(r5).autocorr(1))}
    vbh = pd.Series(np.abs(r5), index=b.index).groupby(b.index.hour).mean()   # intraday seasonality
    out["peak_hour"] = int(vbh.idxmax()) if vbh.notna().any() else -1         # UTC hour of peak activity
    out["seas_conc"] = float(vbh.nlargest(4).sum() / vbh.sum()) if vbh.sum() > 0 else np.nan  # top-4h share
    out.update(sweep_reclaim(b))
    return out


def route(r: pd.Series) -> str:
    if r.get("n_sweep", 0) < 1000:                                       # sparse 5m bars -> sweep metric unreliable
        return "insufficient intraday data"
    if r.get("sweep_pctm", 0) >= 0.65 and r.get("sweep_er", -9) >= 0.04:  # trending: expands after a sweep
        return "sweep-reclaim-runner"
    # mean-reverter with partners: cointegrated OR highly group-correlated (full-sample E-G misses
    # break-cointegrated rates after the 2022 selloff -> the corr_group arm rescues them).
    if r.get("sweep_er", 9) < 0.02 and (r.get("coint_partners", 0) >= 1 or r.get("corr_group", 0) >= 0.60):
        return "RV-cointegration"
    return "monitor / no strong fit"


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="recompute intraday (else use cache)")
    a = ap.parse_args(argv)
    R = pd.read_parquet(PANEL)
    R.index = pd.to_datetime(R.index)
    syms = list(R.columns)
    print(f"universe: {len(syms)} symbols  daily panel {R.shape}  intraday window {START}..{END}")
    prof = daily_profile(R)

    cache = OUT / "intraday_cache.parquet"
    if cache.exists() and not a.rebuild:
        intr_df = pd.read_parquet(cache)
        print(f"  loaded intraday cache ({len(intr_df)} symbols; pass --rebuild to recompute)")
    else:
        intr = {}
        for i, s in enumerate(syms, 1):
            t = time.time()
            intr[s] = intraday_profile(s)
            print(f"  [{i:2}/{len(syms)}] {s:8} {intr[s].get('n_sweep','-'):>5} sweeps  "
                  f"er={intr[s].get('sweep_er', float('nan')):+.3f}  ({time.time()-t:.0f}s)")
        intr_df = pd.DataFrame(intr).T
        intr_df.to_parquet(cache)
    prof = prof.join(intr_df)
    prof = prof.join(coint_partners(R))
    prof["ofi_ic"] = [OFI_IC.get(s, np.nan) for s in prof.index]
    prof["ofi_exec"] = prof["ofi_ic"] > 0.10
    prof["route"] = prof.apply(route, axis=1)
    prof.to_parquet(OUT / "profile_table.parquet")

    num = ["ann_vol", "ac1_d", "vr_d", "coint_partners", "vr_5m", "seas_conc", "sweep_er", "sweep_pctm", "n_sweep", "ofi_ic"]
    show = prof[["group"] + num + ["route"]].copy()
    print("\n================ ASSET PROFILE TABLE ================")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(show.round(3).to_string())

    # cluster on standardized behavioral dims (do nominal groups fall out?)
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.preprocessing import StandardScaler
    cl_dims = ["ann_vol", "ac1_d", "vr_d", "beta_factor", "vr_5m", "ac1_5m", "sweep_er", "mfe90", "seas_conc"]
    X = prof[cl_dims].astype(float)
    X = X.fillna(X.mean())
    Z = StandardScaler().fit_transform(X)
    prof["cluster"] = AgglomerativeClustering(n_clusters=6).fit_predict(Z)
    print("\n================ BEHAVIORAL CLUSTERS (vs nominal group) ================")
    for cid in sorted(prof["cluster"].unique()):
        sub = prof[prof["cluster"] == cid]
        groups = ", ".join(f"{s.split('.')[0]}({sub.loc[s,'group']})" for s in sub.index)
        print(f"  cluster {cid}: {groups}")

    print("\n================ STRATEGY ROUTING ================")
    for rt in sorted(prof["route"].unique()):
        members = [s.split(".")[0] for s in prof[prof["route"] == rt].index]
        print(f"  {rt:24} <- {', '.join(members)}")
    ov = prof[prof["ofi_exec"]].sort_values("ofi_ic", ascending=False)
    tags = ", ".join(f"{s.split('.')[0]}({ov.loc[s, 'ofi_ic']:.2f})" for s in ov.index)
    print(f"  + OFI-execution overlay  <- {tags}  (MBP-1 phase-1; other 19 need the MBP-1 OFI build)")
    print(f"\nwrote {OUT/'profile_table.parquet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
