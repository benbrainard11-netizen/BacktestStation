"""Order-flow-at-the-break test (the Mira-for-equities probe). For a stratified SAMPLE of breakout
setups, pull the 15-min post-break trade tape (Polygon REST /v3/trades) and engineer order-flow
features the OHLCV bars can't see -- then test whether they predict follow-through R.

NBBO quotes are NOT entitled on this tier, so aggression uses the TICK RULE (uptick=buy / downtick=
sell, carrying the prior sign over ties) rather than at-bid/at-ask. Features: signed aggression,
large-print imbalance, large-print fraction, price push, push-per-volume, avg trade size, volume.
Reads env POLYGON_API_KEY. Writes orderflow_sample.parquet. Run with backend\\.venv\\Scripts\\python.exe -u.
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, r"C:\Users\benbr\BacktestStation")
from data_io import load_polygon_daily, load_polygon_minute  # noqa: E402

KEY = os.environ["POLYGON_API_KEY"]
OUT = __import__("pathlib").Path(__file__).resolve().parent / "out"
WINDOW_NS = 15 * 60 * 1_000_000_000  # 15 min after the break
N_PER_YEAR = 600
_S = requests.Session()


def break_ms(tkr, date, hi20):
    m = load_polygon_minute(tkr, date)
    if not len(m):
        return None
    cross = m[m["h"] >= hi20 * 1.001]
    return int(cross["t"].iloc[0]) if len(cross) else None


def of_features(args):
    tkr, date, R, hi20 = args
    bms = break_ms(tkr, date, hi20)
    if bms is None:
        return None
    g = bms * 1_000_000
    rows = []
    url = f"https://api.polygon.io/v3/trades/{tkr}"
    params = {"timestamp.gte": g, "timestamp.lt": g + WINDOW_NS, "limit": 50000, "apiKey": KEY}
    for _ in range(2):  # up to 2 pages
        try:
            r = _S.get(url, params=params, timeout=30)
        except Exception:
            return None
        if r.status_code != 200:
            return None
        j = r.json()
        rows += j.get("results", [])
        nu = j.get("next_url")
        if not nu:
            break
        url, params = nu, {"apiKey": KEY}
    if len(rows) < 20:
        return None
    t = pd.DataFrame(rows)
    px = t["price"].to_numpy(float)
    sz = t["size"].to_numpy(float)
    d = np.sign(np.diff(px, prepend=px[0]))
    for i in range(1, len(d)):  # tick rule: carry prior sign over ties
        if d[i] == 0:
            d[i] = d[i - 1]
    vol = sz.sum()
    buyv, sellv = sz[d > 0].sum(), sz[d < 0].sum()
    thr = np.quantile(sz, 0.95)
    large = sz >= thr
    lv = sz[large].sum()
    lb, ls = sz[large & (d > 0)].sum(), sz[large & (d < 0)].sum()
    push = px[-1] / px[0] - 1.0
    return dict(
        tkr=tkr,
        date=int(date),
        R=R,
        of_aggr=(buyv - sellv) / vol if vol else 0.0,
        of_largeimb=(lb - ls) / lv if lv else 0.0,
        of_largefrac=lv / vol if vol else 0.0,
        of_push=push,
        of_pushpervol=push / np.log1p(vol),
        of_avgsize=sz.mean(),
        of_ntr=len(t),
        of_vol=int(vol),
    )


def main():
    R = pd.read_parquet(OUT / "intraday_entry_results_full.parquet")[["tkr", "date", "R"]]
    S = pd.read_parquet(OUT / "setups.parquet")
    S = S[S["is_breakout"] == 1][["ticker", "date"]]
    df = R.merge(S, left_on=["tkr", "date"], right_on=["ticker", "date"], how="inner")
    df["yr"] = df["date"] // 10000
    samp = pd.concat(
        [g.sample(min(len(g), N_PER_YEAR), random_state=0) for _, g in df.groupby("yr")],
        ignore_index=True,
    )
    print(f"sample: {len(samp):,} setups across {samp['yr'].nunique()} years", flush=True)

    # hi20 lookup for sampled tickers (causal: prior 20d high)
    daily = load_polygon_daily()
    daily = daily[daily["ticker"].isin(set(samp["tkr"]))].sort_values(["ticker", "date"])
    daily["hi20"] = daily.groupby("ticker")["high"].transform(lambda s: s.rolling(20).max().shift(1))
    hi = dict(zip(zip(daily["ticker"], daily["date"]), daily["hi20"]))
    jobs = [
        (t, int(dt), r, hi.get((t, int(dt))))
        for t, dt, r in zip(samp["tkr"], samp["date"], samp["R"])
        if hi.get((t, int(dt))) and not np.isnan(hi.get((t, int(dt))))
    ]
    print(f"jobs with valid hi20: {len(jobs):,}", flush=True)

    out = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(of_features, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            if r:
                out.append(r)
            if i % 500 == 0:
                print(f"  {i}/{len(jobs)}  kept={len(out)}", flush=True)
    res = pd.DataFrame(out)
    res.to_parquet(OUT / "orderflow_sample.parquet")
    print(f"DONE: {len(res):,} setups with order-flow features -> orderflow_sample.parquet", flush=True)


if __name__ == "__main__":
    main()
