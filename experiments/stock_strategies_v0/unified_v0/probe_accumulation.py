"""ACCUMULATION FOOTPRINT probe (research-only, scratch).

Question: does a 20d-high breakout that occurs AFTER a window of institutional-accumulation
footprints in the daily OHLCV beat a RANDOM day in the same stock -- unlike a plain breakout
(which the LEDGER proved is WORSE than random, delta -0.2..-0.36R)?

Same null-control logic as run_breakout_selector.py, but the discriminator is computed on the
BASE (days before the breakout), so it can carve out a genuinely different sub-population rather
than re-weighting the same losers.

Signals computed on bars STRICTLY BEFORE the breakout day i (causal):
  obv_slope_20   : slope of OBV over [i-20,i-1], normalised by avg vol -> persistent net buying
  adl_slope_20   : slope of Accum/Dist line over [i-20,i-1], normalised  -> close-location money flow
  updown_vol_20  : sum(vol on up-closes)/sum(vol on down-closes) over [i-20,i-1]
  quiet_accum    : "tight & rising on rising vol": corr(vol, close)>0 over base AND base ATR% low
  vdu            : volume dry-up: min 5d-avg-vol in base / 50d-avg-vol  (low = dried up)
  pocket_pivot   : on day i-? the up-day vol > max down-day vol of prior 10d, while under/at 10dMA
  close_range_20 : avg daily close-location-value over base (closes near highs = accumulation)
  rvol_z         : z-score of breakout-day volume vs base (expansion off a quiet base)

For each signal we ask: among breakouts, does the HIGH-signal tercile beat random-day by MORE
(less-negative / positive) than the LOW-signal tercile? The decisive number is the null-control
DELTA (signal-selected breakout day R  minus  random-day R, same tickers), x20/x40 daily fwd.

Metric = market-relative 20d/40d forward continuation (x20/x40), same as setups.parquet, recomputed
here on the full 2016-2026 daily so the base window is always available.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
RNG = np.random.default_rng(0)

# ---- load all daily, build SPY market reference ----
df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
meta = pd.read_parquet(POLY / "meta.parquet")
cs = set(meta["ticker"])
spy = df[df["ticker"] == "SPY"].sort_values("date").set_index("date")["close"]
spy_d = spy.to_dict()
spy_ma50 = (spy.rolling(50).mean())
spy_above50_d = (spy > spy_ma50).to_dict()

g = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"])

# accumulators: per-signal lists of (signal_value, x20, x40, regime_up) for breakout days,
# plus a per-ticker pool of random non-breakout days for the null control.
brk_rows = []          # one row per breakout day with all signals + fwd returns
rand_pool = {}         # ticker -> list of (x20, x40) for random non-breakout days

def slope_norm(y):
    """OLS slope of y over its index, divided by mean|y| scale (unitless-ish)."""
    n = len(y)
    if n < 5:
        return np.nan
    x = np.arange(n)
    xm = x.mean()
    denom = ((x - xm) ** 2).sum()
    if denom == 0:
        return np.nan
    b = ((x - xm) * (y - y.mean())).sum() / denom
    scale = np.abs(y).mean() + 1e-9
    return b / scale

for t, d in g.groupby("ticker", sort=False):
    if len(d) < 320:
        continue
    o = d["open"].to_numpy(float); c = d["close"].to_numpy(float)
    hi = d["high"].to_numpy(float); lo = d["low"].to_numpy(float)
    vol = d["volume"].to_numpy(float); dts = d["date"].to_numpy()
    n = len(d)
    pc = np.roll(c, 1)
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - pc), np.abs(lo - pc)))
    atr14 = pd.Series(tr).rolling(14).mean().to_numpy()
    hi20 = pd.Series(hi).rolling(20).max().shift(1).to_numpy()
    ma10 = pd.Series(c).rolling(10).mean().to_numpy()
    avgv20 = pd.Series(vol).rolling(20).mean().shift(1).to_numpy()
    avgv50 = pd.Series(vol).rolling(50).mean().shift(1).to_numpy()
    dvol = pd.Series(c * vol).rolling(20).mean().shift(1).to_numpy()
    # OBV and ADL cumulative series
    sign = np.sign(np.diff(c, prepend=c[0]))
    obv = np.cumsum(sign * vol)
    clv = np.where((hi - lo) > 0, ((c - lo) - (hi - c)) / (hi - lo), 0.0)
    adl = np.cumsum(clv * vol)
    upday = c > pc

    rp = []
    for i in range(60, n - 41):
        is_brk = (not np.isnan(hi20[i])) and c[i] > hi20[i]
        tradeable = c[i] >= 5 and not np.isnan(dvol[i]) and dvol[i] >= 1e6
        di = int(dts[i])
        s0 = spy_d.get(di); s20 = spy_d.get(int(dts[i + 20])); s40 = spy_d.get(int(dts[i + 40]))
        if not (s0 and s20 and s40):
            continue
        x20 = (c[i + 20] / c[i] - 1) - (s20 / s0 - 1)
        x40 = (c[i + 40] / c[i] - 1) - (s40 / s0 - 1)
        if is_brk and tradeable:
            # --- accumulation signals on the BASE [i-20, i-1] (causal) ---
            base = slice(i - 20, i)
            cb = c[base]; vb = vol[base]; ud = upday[base]
            obv_s = slope_norm(obv[base])
            adl_s = slope_norm(adl[base])
            upv = vb[ud].sum(); dnv = vb[~ud].sum()
            updown = upv / dnv if dnv > 0 else np.nan
            cv = np.corrcoef(vb, cb)[0, 1] if vb.std() > 0 and cb.std() > 0 else np.nan
            base_atrpct = np.nanmean(atr14[i - 20:i]) / c[i - 1] if c[i - 1] else np.nan
            quiet = (cv if not np.isnan(cv) else 0) - (base_atrpct * 10 if not np.isnan(base_atrpct) else 0)
            v5min = pd.Series(vol[i - 20:i]).rolling(5).mean().min()
            vdu = v5min / avgv50[i] if avgv50[i] else np.nan
            clv_b = np.nanmean(clv[base])
            rvolz = (vol[i] - np.nanmean(vb)) / (np.nanstd(vb) + 1e-9)
            # pocket pivot: did ANY up-day in last 10 (before i) have vol>max down-vol prior 10?
            pp = 0
            for j in range(i - 10, i):
                if upday[j]:
                    prior = vol[max(0, j - 10):j]
                    pdn = vol[max(0, j - 10):j][c[max(0, j - 10):j] < pc[max(0, j - 10):j]] \
                        if j - 10 >= 0 else np.array([0.0])
                    pdn = vol[max(0, j - 10):j][~upday[max(0, j - 10):j]]
                    mx = pdn.max() if len(pdn) else 0
                    if vol[j] > mx and c[j] <= ma10[j] * 1.02:
                        pp = 1; break
            brk_rows.append(dict(
                ticker=t, date=di, regime_up=int(bool(spy_above50_d.get(di))),
                x20=x20, x40=x40,
                obv_slope=obv_s, adl_slope=adl_s, updown_vol=updown, quiet=quiet,
                vdu=vdu, clv=clv_b, rvolz=rvolz, pocket_pivot=pp,
            ))
        elif not is_brk and tradeable:
            rp.append((x20, x40))
    if rp:
        rand_pool[t] = rp

B = pd.DataFrame(brk_rows).replace([np.inf, -np.inf], np.nan)
print(f"breakouts: {len(B):,}  tickers w/ random pool: {len(rand_pool):,}")
print(f"  breakout mean x20 {B.x20.mean()*100:+.3f}%  x40 {B.x40.mean()*100:+.3f}%")

# random-day baseline (same tickers as breakouts), matched count via pooled draw
rand20, rand40 = [], []
for t in B["ticker"].unique():
    rp = rand_pool.get(t)
    if not rp:
        continue
    arr = np.array(rp)
    k = min(len(arr), 5)
    idx = RNG.choice(len(arr), k, replace=False)
    rand20.extend(arr[idx, 0]); rand40.extend(arr[idx, 1])
rand20 = np.array(rand20); rand40 = np.array(rand40)
print(f"  random non-breakout mean x20 {rand20.mean()*100:+.3f}%  x40 {rand40.mean()*100:+.3f}%  (n {len(rand20):,})")
base_delta20 = B.x20.mean() - rand20.mean()
print(f"  PLAIN breakout DELTA x20 vs random: {base_delta20*100:+.3f}%  (LEDGER: should be NEGATIVE)\n")

def boot_mean_ci(x, n=2000):
    x = np.asarray(x); x = x[~np.isnan(x)]
    idx = RNG.integers(0, len(x), (n, len(x)))
    m = x[idx].mean(1)
    return x.mean(), np.percentile(m, [2.5, 97.5])

SIGS = ["obv_slope", "adl_slope", "updown_vol", "quiet", "vdu", "clv", "rvolz"]
print("=== top-tercile breakout (by accumulation signal) vs bottom-tercile + vs random-day ===")
print(f"{'signal':<12} {'topX20':>8} {'botX20':>8} {'top-bot':>8} {'top-rand':>9} {'topCI':>20}")
for s in SIGS:
    v = B.dropna(subset=[s])
    if len(v) < 1000:
        print(f"{s:<12} (insufficient n={len(v)})"); continue
    q = v[s].quantile([1/3, 2/3]).to_numpy()
    top = v[v[s] >= q[1]]; bot = v[v[s] <= q[0]]
    tm, tci = boot_mean_ci(top.x20.to_numpy())
    bm = bot.x20.mean()
    print(f"{s:<12} {tm*100:>+7.3f}% {bm*100:>+7.3f}% {(tm-bm)*100:>+7.3f}% "
          f"{(tm-rand20.mean())*100:>+8.3f}% [{tci[0]*100:+.3f},{tci[1]*100:+.3f}]")

# pocket pivot is binary
pp1 = B[B.pocket_pivot == 1]; pp0 = B[B.pocket_pivot == 0]
ppm, ppci = boot_mean_ci(pp1.x20.to_numpy())
print(f"{'pocket_piv=1':<12} {ppm*100:>+7.3f}% {pp0.x20.mean()*100:>+7.3f}% "
      f"{(ppm-pp0.x20.mean())*100:>+7.3f}% {(ppm-rand20.mean())*100:>+8.3f}% [{ppci[0]*100:+.3f},{ppci[1]*100:+.3f}]  (n1={len(pp1)})")

# COMBINED accumulation score: rank-sum of the daily-flow signals (high = more accumulation)
v = B.dropna(subset=["obv_slope", "adl_slope", "updown_vol", "clv"]).copy()
for s in ["obv_slope", "adl_slope", "updown_vol", "clv"]:
    v[s + "_r"] = v[s].rank(pct=True)
v["accum_score"] = v[["obv_slope_r", "adl_slope_r", "updown_vol_r", "clv_r"]].mean(1)
top = v[v.accum_score >= v.accum_score.quantile(0.9)]
tm, tci = boot_mean_ci(top.x20.to_numpy())
print(f"\nCOMBINED accum top-decile x20 {tm*100:+.3f}% CI[{tci[0]*100:+.3f},{tci[1]*100:+.3f}] "
      f"vs random {rand20.mean()*100:+.3f}%  DELTA {(tm-rand20.mean())*100:+.3f}%  (n={len(top)})")
# regime-up only
topu = top[top.regime_up == 1]
print(f"  (regime-up only: x20 {topu.x20.mean()*100:+.3f}%  n={len(topu)})")
print("\nREAD: any signal where top-rand DELTA > 0 (CI clear of 0) = a real accumulation rescue.")
print("Else: accumulation footprints do NOT carve a positive breakout subset (joins the dead pile).")
