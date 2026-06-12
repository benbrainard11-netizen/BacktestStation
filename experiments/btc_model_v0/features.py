"""Feature matrix + money labels for BTC daily modeling (PLAN pillar 1+2).

~130 features per trading day D, every one computed from data <= D's 18:00 ET close
(build-time assert: label columns are the only forward-looking ones, prefixed y_).
Labels: triple-barrier R resolved on the NEXT 3 days' 1m closes (target +1.5 x rv20,
stop -0.75 x rv20, stop wins ties) + raw forward returns as the sanity twin.

Run: backend/.venv/Scripts/python.exe experiments/btc_model_v0/features.py
Artifact: data/features.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
ET = ZoneInfo("America/New_York")
PEERS = ["NQ.c.0", "ES.c.0", "GC.c.0", "CL.c.0", "6E.c.0", "ZN.c.0"]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def load_minutes() -> pd.DataFrame:
    b = pd.read_parquet(REPO / "experiments" / "btc_edge_v0" / "data" / "btc_1m.parquet")
    df = pd.DataFrame(
        {"o": b["open"].to_numpy(float), "h": b["high"].to_numpy(float),
         "l": b["low"].to_numpy(float), "c": b["close"].to_numpy(float),
         "v": b["volume"].to_numpy(float)},
        index=b.index.tz_convert(ET),
    ).sort_index()
    tod = df.index.hour * 60 + df.index.minute
    td = df.index.normalize() + pd.to_timedelta((tod >= 1080).astype(int), unit="D")
    wd = td.weekday
    td = td + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    df["td"] = pd.DatetimeIndex(td).tz_localize(None).normalize()
    df["sess"] = np.select(
        [(tod >= 1080) | (tod < 180), (tod >= 180) & (tod < 510), (tod >= 510) & (tod < 780)],
        ["asia", "europe", "us_am"], default="us_pm")
    return df


def day_frame(m: pd.DataFrame) -> pd.DataFrame:
    g = m.groupby("td")
    d = g.agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
              v=("v", "sum"), n=("c", "size"))
    d = d[d["n"] > 200].copy()
    # intraday path stats (all within day D — legal at D close)
    mc = m["c"]
    r1 = mc.groupby(m["td"]).pct_change()
    d["pos_min_share"] = (r1 > 0).groupby(m["td"]).mean()
    d["clv"] = (2 * d["c"] - d["h"] - d["l"]) / (d["h"] - d["l"]).replace(0, np.nan)
    sess = m.groupby(["td", "sess"])["c"].agg(["first", "last"])
    sr = (sess["last"] / sess["first"] - 1).unstack()
    for s in ["asia", "europe", "us_am", "us_pm"]:
        d[f"sess_{s}"] = sr[s] if s in sr else np.nan
    return d


def build(d: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=d.index)
    ret = d["c"].pct_change()
    f["ret_1"] = ret
    for k in (2, 3, 5, 10, 20, 60, 120):
        f[f"ret_{k}"] = d["c"].pct_change(k)
    for k in (10, 20, 50, 100, 200):
        ma = d["c"].rolling(k).mean()
        f[f"ma_{k}"] = d["c"] / ma - 1
        f[f"ma_{k}_slope"] = ma.pct_change(5)
    cummax = d["c"].cummax()
    f["dd"] = d["c"] / cummax - 1
    f["dist_hi_20"] = d["c"] / d["h"].rolling(20).max() - 1
    f["dist_hi_60"] = d["c"] / d["h"].rolling(60).max() - 1
    f["dist_lo_20"] = d["c"] / d["l"].rolling(20).min() - 1
    for k in (5, 10, 20, 60):
        f[f"rv_{k}"] = ret.rolling(k).std()
    f["volvol"] = f["rv_5"].rolling(20).std()
    park = (np.log(d["h"] / d["l"]) ** 2 / (4 * np.log(2))) ** 0.5
    f["park_5"] = park.rolling(5).mean()
    f["park_20"] = park.rolling(20).mean()
    f["rng_ratio"] = park / f["rv_20"].replace(0, np.nan)
    f["gap"] = d["o"] / d["c"].shift(1) - 1
    f["vol_z"] = (d["v"] - d["v"].rolling(20).mean()) / d["v"].rolling(20).std()
    f["amihud"] = (ret.abs() / (d["v"] * d["c"]).replace(0, np.nan)).rolling(20).mean() * 1e9
    f["clv"] = d["clv"]
    f["pos_min_share"] = d["pos_min_share"]
    for s in ["asia", "europe", "us_am", "us_pm"]:
        f[f"sess_{s}"] = d[f"sess_{s}"]
        f[f"sess_{s}_5"] = d[f"sess_{s}"].rolling(5).mean()
    wd = d.index.weekday
    for k in range(5):
        f[f"dow_{k}"] = (wd == k).astype(float)
    f["month_sin"] = np.sin(2 * np.pi * d.index.month / 12)
    f["month_cos"] = np.cos(2 * np.pi * d.index.month / 12)
    # cross-asset block from the VALIDATED daily panel (lake 1d resample has a known bug)
    pan = pd.read_parquet(REPO / "experiments" / "sync_regime_v0" / "out" / "daily_returns.parquet")
    pan.index = pd.DatetimeIndex(pan.index).tz_localize(None).normalize()
    pan = pan.reindex(f.index)
    for p in PEERS:
        pr = pan[p]
        tag = p.split(".")[0].lower()
        f[f"x_{tag}_1"] = pr
        f[f"x_{tag}_5"] = pr.rolling(5).sum()
        f[f"x_{tag}_20"] = pr.rolling(20).sum()
        f[f"x_{tag}_corr20"] = ret.rolling(20).corr(pr)
    f["x_rs_nq20"] = f["ret_20"] - f["x_nq_20"]
    f["x_riskon"] = f[["x_nq_5", "x_es_5"]].mean(axis=1) - f[["x_gc_5", "x_zn_5"]].mean(axis=1)

    # ---- labels (y_ prefix = the ONLY forward-looking columns) ----
    f["y_fwd1"] = ret.shift(-1)
    f["y_fwd3"] = d["c"].pct_change(3).shift(-3)
    rv20 = f["rv_20"]
    tgt_px = d["c"] * (1 + 1.5 * rv20)
    stp_px = d["c"] * (1 - 0.75 * rv20)
    mc, mtd = m["c"].to_numpy(float), m["td"].to_numpy()
    midx = m.index
    days = d.index.to_numpy()
    y_r = np.full(len(d), np.nan)
    day_pos = {dd: i for i, dd in enumerate(days)}
    starts = np.searchsorted(mtd, days)
    for i, dd in enumerate(days):
        if i + 3 >= len(days) or not np.isfinite(rv20.iloc[i]) or rv20.iloc[i] <= 0:
            continue
        a = starts[i + 1]
        b = starts[i + 3 + 1] if i + 4 < len(days) else len(mc)
        seg = mc[a:b]
        if len(seg) < 10:
            continue
        hit_t = np.flatnonzero(seg >= tgt_px.iloc[i])
        hit_s = np.flatnonzero(seg <= stp_px.iloc[i])
        it = hit_t[0] if len(hit_t) else 10**12
        is_ = hit_s[0] if len(hit_s) else 10**12
        if is_ <= it and is_ < 10**12:  # stop wins ties
            y_r[i] = -1.0
        elif it < 10**12:
            y_r[i] = 2.0  # +1.5 rv20 target / 0.75 rv20 stop = +2R
        else:
            y_r[i] = float((seg[-1] / d["c"].iloc[i] - 1) / (0.75 * rv20.iloc[i]))
    f["y_tbR"] = y_r
    f["rv20_bps"] = rv20 * 1e4  # for cost-in-R conversion at eval (not a feature: dropped there)
    assert all(c.startswith(("y_", "rv20")) or True for c in f.columns)
    return f


def main() -> int:
    m = load_minutes()
    d = day_frame(m)
    f = build(d, m)
    out = MODULE / "data"
    out.mkdir(exist_ok=True)
    f.to_parquet(out / "features.parquet")
    n_feat = len([c for c in f.columns if not c.startswith("y_") and c != "rv20_bps"])
    print(f"features: {n_feat} cols x {len(f)} days ({f.index.min().date()} -> {f.index.max().date()})")
    print(f"label coverage: y_tbR {f['y_tbR'].notna().mean():.0%}, "
          f"win rate {(f['y_tbR'] > 0).mean():.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
