"""Accumulation probe v2 -- reconcile the baseline + ask the only question that matters:
does breakout-WITH-accumulation produce a POSITIVE-expectancy subset (x20>0, CI clear of 0)?

The v1 "+DELTA vs random" was misleading: random non-breakout days (mean x20 -2.8%) are mostly
weak/declining-stock days, so any up-thrust looks good vs that pool. The honest bar is ABSOLUTE:
is the accumulation-selected breakout subset's forward continuation POSITIVE (not just less-bad)?
And a tighter null: random day drawn from the SAME ticker but restricted to UPTREND context
(close>ma50, regime_up) so the baseline isn't dominated by downtrending junk.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
RNG = np.random.default_rng(0)
df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
meta = pd.read_parquet(POLY / "meta.parquet"); cs = set(meta["ticker"])
spy = df[df["ticker"] == "SPY"].sort_values("date").set_index("date")["close"]
spy_d = spy.to_dict(); spy_above50_d = (spy > spy.rolling(50).mean()).to_dict()
g = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"])

def slope_norm(y):
    n = len(y)
    if n < 5: return np.nan
    x = np.arange(n); xm = x.mean(); den = ((x-xm)**2).sum()
    if den == 0: return np.nan
    return (((x-xm)*(y-y.mean())).sum()/den)/(np.abs(y).mean()+1e-9)

brk_rows, rand_up = [], {}
for t, d in g.groupby("ticker", sort=False):
    if len(d) < 320: continue
    c = d["close"].to_numpy(float); hi = d["high"].to_numpy(float); lo = d["low"].to_numpy(float)
    vol = d["volume"].to_numpy(float); dts = d["date"].to_numpy(); n = len(d); pc = np.roll(c, 1)
    hi20 = pd.Series(hi).rolling(20).max().shift(1).to_numpy()
    ma50 = pd.Series(c).rolling(50).mean().to_numpy()
    dvol = pd.Series(c*vol).rolling(20).mean().shift(1).to_numpy()
    sign = np.sign(np.diff(c, prepend=c[0])); obv = np.cumsum(sign*vol)
    clv = np.where((hi-lo) > 0, ((c-lo)-(hi-c))/(hi-lo), 0.0); adl = np.cumsum(clv*vol)
    upday = c > pc
    ru = []
    for i in range(60, n-41):
        is_brk = (not np.isnan(hi20[i])) and c[i] > hi20[i]
        trad = c[i] >= 5 and not np.isnan(dvol[i]) and dvol[i] >= 1e6
        if not trad: continue
        di = int(dts[i]); s0 = spy_d.get(di); s20 = spy_d.get(int(dts[i+20]))
        if not (s0 and s20): continue
        x20 = (c[i+20]/c[i]-1) - (s20/s0-1)
        uptrend = (not np.isnan(ma50[i])) and c[i] > ma50[i] and bool(spy_above50_d.get(di))
        if is_brk:
            base = slice(i-20, i); cb = c[base]; vb = vol[base]; ud = upday[base]
            upv, dnv = vb[ud].sum(), vb[~ud].sum()
            brk_rows.append(dict(ticker=t, x20=x20, uptrend=int(uptrend),
                obv=slope_norm(obv[base]), adl=slope_norm(adl[base]),
                updown=(upv/dnv if dnv > 0 else np.nan), clv=np.nanmean(clv[base])))
        elif uptrend:  # tighter null: same ticker, uptrend, non-breakout
            ru.append(x20)
    if ru: rand_up[t] = ru

B = pd.DataFrame(brk_rows).replace([np.inf, -np.inf], np.nan)
def boot(x, n=2000):
    x = np.asarray(x); x = x[~np.isnan(x)]
    idx = RNG.integers(0, len(x), (n, len(x))); m = x[idx].mean(1)
    return x.mean(), np.percentile(m, [2.5, 97.5]), len(x)

# tighter random-up baseline (same tickers)
ru20 = []
for t in B.ticker.unique():
    rp = rand_up.get(t)
    if rp:
        arr = np.array(rp); ru20.extend(arr[RNG.choice(len(arr), min(len(arr), 5), replace=False)])
ru20 = np.array(ru20)
print(f"breakouts {len(B):,} | breakout x20 {B.x20.mean()*100:+.3f}% | "
      f"UPTREND-random x20 {ru20.mean()*100:+.3f}% (n{len(ru20):,})")
print(f"  breakout(uptrend-only) x20 {B[B.uptrend==1].x20.mean()*100:+.3f}%  "
      f"delta vs uptrend-random {(B[B.uptrend==1].x20.mean()-ru20.mean())*100:+.3f}%")

# combined accumulation score, ask ABSOLUTE positivity at progressively tighter cuts
v = B.dropna(subset=["obv", "adl", "updown", "clv"]).copy()
for s in ["obv", "adl", "updown", "clv"]:
    v[s+"_r"] = v[s].rank(pct=True)
v["score"] = v[["obv_r", "adl_r", "updown_r", "clv_r"]].mean(axis=1)
print("\n=== combined accumulation score: ABSOLUTE x20 at top cuts (is it POSITIVE?) ===")
for qq, lbl in [(0.5, "top-50%"), (0.75, "top-25%"), (0.9, "top-10%"), (0.95, "top-5%"), (0.99, "top-1%")]:
    top = v[v.score >= v.score.quantile(qq)]
    m, ci, nn = boot(top.x20.to_numpy())
    tu = top[top.uptrend == 1]; mu, ciu, nu = boot(tu.x20.to_numpy())
    print(f"  {lbl:<8} ALL x20 {m*100:+.3f}% CI[{ci[0]*100:+.3f},{ci[1]*100:+.3f}] n{nn:<6} | "
          f"UPTREND x20 {mu*100:+.3f}% CI[{ciu[0]*100:+.3f},{ciu[1]*100:+.3f}] n{nu}")
print("\nREAD: a real edge needs ABSOLUTE x20 > 0 with CI clear of 0 at a usable cut.")
