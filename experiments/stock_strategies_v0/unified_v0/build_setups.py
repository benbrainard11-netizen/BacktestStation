"""Build the UNIFIED upside-continuation setup table from the clean Polygon universe
(delisted-included common stocks, 2021-2026). A 'setup' = an upside thrust: a gap-up OR a
breakout (20d-high break). Each row is tagged (is_gap/is_breakout/big_gap) and carries the
'why it's moving + is it quality' features (catalyst proxy, relative strength, structure,
regime) + forward MARKET-RELATIVE continuation (20d/40d). One brain, many ignition types.
Causal: every feature uses data <= the setup day. Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
meta = pd.read_parquet(POLY / "meta.parquet")
cs = set(meta["ticker"])
active = dict(zip(meta["ticker"], meta["active"]))

# --- SPY reference (market): trailing + regime, indexed by date int ---
spy = df[df["ticker"] == "SPY"].sort_values("date").set_index("date")["close"]
spy_ret6 = spy / spy.shift(126) - 1
spy_ret60 = spy / spy.shift(60) - 1
spy_ma50 = spy.rolling(50).mean()
spy_close_d = spy.to_dict()
spy_ret6_d = spy_ret6.to_dict()
spy_ret60_d = spy_ret60.to_dict()
spy_above50_d = (spy > spy_ma50).to_dict()

g = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"])
rows = []
for t, d in g.groupby("ticker", sort=False):
    if len(d) < 280:
        continue
    o = d["open"].to_numpy()
    c = d["close"].to_numpy()
    hi = d["high"].to_numpy()
    lo = d["low"].to_numpy()
    vol = d["volume"].to_numpy()
    dts = d["date"].to_numpy()
    n = len(d)
    pc = np.roll(c, 1)
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - pc), np.abs(lo - pc)))
    atr14 = pd.Series(tr).rolling(14).mean().to_numpy()
    atr50 = pd.Series(tr).rolling(50).mean().to_numpy()
    ma50 = pd.Series(c).rolling(50).mean().to_numpy()
    hi20 = pd.Series(hi).rolling(20).max().shift(1).to_numpy()
    lo20 = pd.Series(lo).rolling(20).min().shift(1).to_numpy()
    hi252 = pd.Series(hi).rolling(252).max().to_numpy()
    avgv = pd.Series(vol).rolling(20).mean().shift(1).to_numpy()
    dvol = pd.Series(c * vol).rolling(20).mean().shift(1).to_numpy()
    act = active.get(t, False)
    for i in range(252, n - 40):
        gap = o[i] / c[i - 1] - 1
        is_gap = gap >= 0.03
        is_brk = c[i] > hi20[i] if not np.isnan(hi20[i]) else False
        if not (is_gap or is_brk):  # only upside thrusts
            continue
        if c[i] < 5 or np.isnan(dvol[i]) or dvol[i] < 1e6:  # tradeable
            continue
        di, dH20, dH40 = int(dts[i]), int(dts[i + 20]), int(dts[i + 40])
        s0 = spy_close_d.get(di)
        if not s0:
            continue
        s20, s40 = spy_close_d.get(dH20), spy_close_d.get(dH40)
        if not s20 or not s40:
            continue
        rows.append(
            {
                "ticker": t,
                "date": di,
                "active": act,
                "is_gap": int(is_gap),
                "is_breakout": int(is_brk),
                "big_gap": int(gap >= 0.075),
                "gap": gap,
                "vol_spike": vol[i] / avgv[i] if avgv[i] else np.nan,
                "ret_3m": c[i] / c[i - 63] - 1,
                "ret_6m": c[i] / c[i - 126] - 1,
                "ret_12_1": c[i - 21] / c[i - 252] - 1,
                "rs_6m": (c[i] / c[i - 126] - 1) - (spy_ret6_d.get(di) or 0),
                "high52_prox": c[i] / hi252[i] if hi252[i] else np.nan,
                "atr_pct": atr14[i] / c[i] if c[i] else np.nan,
                "vol_contract": atr14[i] / atr50[i] if atr50[i] else np.nan,
                "base_width": (hi20[i] - lo20[i]) / c[i] if c[i] and not np.isnan(hi20[i]) else np.nan,
                "dist_ma50": c[i] / ma50[i] - 1 if ma50[i] else np.nan,
                "regime_up": int(bool(spy_above50_d.get(di))),
                "spy_ret60": spy_ret60_d.get(di) or 0,
                "log_price": np.log(c[i]),
                "log_dvol": np.log(dvol[i] + 1),
                "x20": (c[i + 20] / c[i] - 1) - (s20 / s0 - 1),  # market-relative continuation
                "x40": (c[i + 40] / c[i] - 1) - (s40 / s0 - 1),
            }
        )

S = pd.DataFrame(rows).dropna(subset=["x20", "x40"])
S.to_parquet(OUT / "setups.parquet")
print(
    f"setups: {len(S):,}  ({S['is_gap'].sum():,} gaps, {S['is_breakout'].sum():,} breakouts, "
    f"{(S['is_gap']&S['is_breakout']).sum():,} both)"
)
print(
    f"  active {S['active'].sum():,} / delisted {(~S['active']).sum():,} | "
    f"{S['date'].min()}..{S['date'].max()} | tickers {S['ticker'].nunique()}"
)
print(f"  mean x20 {S['x20'].mean()*100:+.2f}%  x40 {S['x40'].mean()*100:+.2f}%")
