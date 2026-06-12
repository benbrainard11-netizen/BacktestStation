"""ES feature matrix + DAY-FLAT money labels, with the options-surface block.

Price/vol/calendar/cross-asset blocks span 2015+ (lake 1m bars); the GEX block
(dist-to-walls, wall width, zero-gamma position, total-GEX z) spans 2025-05+ and is
evaluated as its own subset at model time. Options timing per constitution rule A7:
ONLY row D-1 feeds trading day D. Walls used in INDEX-relative form (normalized by
the row's own spot) so no futures-basis mapping is needed for daily features.

Labels: day-flat by construction — vol-scaled triple-barrier (+1.0 rv20 / -0.75 rv20)
resolved on the NEXT trading day's 1m closes only; unresolved = next-day close in R.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/features_index.py
Artifact: data/features_es.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(REPO / "backend"))
from app.data.reader import read_bars  # noqa: E402

ET = ZoneInfo("America/New_York")
SYM = "ES.c.0"  # default target; build(sym=...) parameterizes
ALL_PEERS = ["ES.c.0", "NQ.c.0", "GC.c.0", "6E.c.0", "ZN.c.0"]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def load_es_minutes(sym: str = SYM) -> pd.DataFrame:
    b = read_bars(symbol=sym, timeframe="1m", start="2015-01-01", end="2026-06-10")
    ts = pd.to_datetime(b["ts_event"], utc=True).dt.tz_convert(ET)
    df = pd.DataFrame(
        {
            "o": np.asarray(b["open"].to_numpy(), float),
            "h": np.asarray(b["high"].to_numpy(), float),
            "l": np.asarray(b["low"].to_numpy(), float),
            "c": np.asarray(b["close"].to_numpy(), float),
            "v": np.asarray(b["volume"].to_numpy(), float),
        },
        index=ts,
    ).sort_index()
    tod = df.index.hour * 60 + df.index.minute
    td = df.index.normalize() + pd.to_timedelta((tod >= 1080).astype(int), unit="D")
    wd = td.weekday
    td = td + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    df["td"] = pd.DatetimeIndex(td).tz_localize(None).normalize()
    return df


def build(sym: str = SYM) -> pd.DataFrame:
    peers = [p for p in ALL_PEERS if p != sym]
    m = load_es_minutes(sym)
    g = m.groupby("td")
    d = g.agg(
        o=("o", "first"),
        h=("h", "max"),
        l=("l", "min"),
        c=("c", "last"),
        v=("v", "sum"),
        n=("c", "size"),
    )
    d = d[d["n"] > 200]
    f = pd.DataFrame(index=d.index)
    ret = d["c"].pct_change()
    for k in (1, 2, 3, 5, 10, 20, 60):
        f[f"ret_{k}"] = d["c"].pct_change(k)
    for k in (10, 20, 50, 200):
        ma = d["c"].rolling(k).mean()
        f[f"ma_{k}"] = d["c"] / ma - 1
        f[f"ma_{k}_slope"] = ma.pct_change(5)
    for k in (5, 10, 20, 60):
        f[f"rv_{k}"] = ret.rolling(k).std()
    park = (np.log(d["h"] / d["l"]) ** 2 / (4 * np.log(2))) ** 0.5
    f["park_5"], f["park_20"] = park.rolling(5).mean(), park.rolling(20).mean()
    f["rng_ratio"] = park / f["rv_20"].replace(0, np.nan)
    f["gap"] = d["o"] / d["c"].shift(1) - 1
    f["vol_z"] = (d["v"] - d["v"].rolling(20).mean()) / d["v"].rolling(20).std()
    f["clv"] = (2 * d["c"] - d["h"] - d["l"]) / (d["h"] - d["l"]).replace(0, np.nan)
    f["dist_hi_20"] = d["c"] / d["h"].rolling(20).max() - 1
    f["dist_lo_20"] = d["c"] / d["l"].rolling(20).min() - 1
    wd = d.index.weekday
    for k in range(5):
        f[f"dow_{k}"] = (wd == k).astype(float)
    # cross-asset (validated panel + extension)
    pan = pd.read_parquet(
        REPO / "experiments" / "sync_regime_v0" / "out" / "daily_returns.parquet"
    )
    pan.index = pd.DatetimeIndex(pan.index).tz_localize(None).normalize()
    ext_p = REPO / "experiments" / "btc_model_v0" / "data" / "panel_ext.parquet"
    if ext_p.exists():
        ext = pd.read_parquet(ext_p).reindex(columns=pan.columns)
        pan = pd.concat([pan, ext[ext.index > pan.index.max()]]).sort_index()
    pan = pan.reindex(f.index)
    # self structural position (scale-free)
    self_pos20 = (d["c"] - d["l"].rolling(20).min()) / (
        d["h"].rolling(20).max() - d["l"].rolling(20).min()
    ).replace(0, np.nan)
    self_hi20 = d["c"] / d["c"].rolling(20).max() - 1
    self_ma50 = d["c"] / d["c"].rolling(50).mean() - 1
    for p_ in peers:
        tag = p_.split(".")[0].lower()
        f[f"x_{tag}_1"] = pan[p_]
        f[f"x_{tag}_5"] = pan[p_].rolling(5).sum()
        f[f"x_{tag}_corr20"] = ret.rolling(20).corr(pan[p_])
        # relative-STRUCTURE block (xs_): each asset's position vs its own concepts,
        # DIFFERENCED across assets — the SMT/divergence intuition as features.
        # Peer pseudo-price from cumulated returns (position metrics are scale-free).
        pp = (1 + pan[p_].fillna(0)).cumprod().where(pan[p_].notna())
        p_pos20 = (pp - pp.rolling(20).min()) / (
            pp.rolling(20).max() - pp.rolling(20).min()
        ).replace(0, np.nan)
        p_hi20 = pp / pp.rolling(20).max() - 1
        p_ma50 = pp / pp.rolling(50).mean() - 1
        f[f"xs_{tag}_div_pos20"] = self_pos20 - p_pos20
        f[f"xs_{tag}_div_hi20"] = self_hi20 - p_hi20
        f[f"xs_{tag}_div_ma50"] = self_ma50 - p_ma50
        f[f"xs_{tag}_self_hi_alone"] = (
            (self_hi20 > -0.001) & (p_hi20 < -0.005)
        ).astype(float)
        f[f"xs_{tag}_peer_hi_alone"] = (
            (p_hi20 > -0.001) & (self_hi20 < -0.005)
        ).astype(float)
    # ---- GEX / options-surface block (ES/SPX only; row D-1 per rule A7) ----
    if sym != "ES.c.0":
        return _finish(f, d, m, sym)
    gx = pd.read_parquet(
        REPO / "experiments" / "options_signals_v0" / "out" / "gex_levels_spx.parquet"
    )
    gx.index = pd.to_datetime(gx["date"], format="%Y%m%d")
    gx = gx.sort_index().reindex(f.index).shift(1)  # PRIOR-day row
    spot = gx["spot"]
    f["gx_dist_call"] = (gx["call_wall"] - spot) / spot
    f["gx_dist_put"] = (spot - gx["put_wall"]) / spot
    f["gx_width"] = (gx["call_wall"] - gx["put_wall"]) / spot
    f["gx_pos_in_range"] = (spot - gx["put_wall"]) / (
        gx["call_wall"] - gx["put_wall"]
    ).replace(0, np.nan)
    f["gx_zero_gamma_dist"] = (spot - gx["zero_gamma"]) / spot
    lg = np.sign(gx["total_gex"]) * np.log1p(gx["total_gex"].abs())
    f["gx_total_z20"] = (lg - lg.rolling(20).mean()) / lg.rolling(20).std()
    f["gx_width_chg5"] = f["gx_width"].diff(5)
    f["gx_pos_chg1"] = f["gx_pos_in_range"].diff(1)
    # ---- options SURFACE block (raw-cache scan; prior-day row per rule A7) ----
    sp = MODULE / "data" / "spx_surface.parquet"
    if sp.exists():
        ox = pd.read_parquet(sp)
        ox.index = pd.to_datetime(ox["date"], format="%Y%m%d")
        ox = ox.drop(columns=["date", "spot"]).sort_index()
        ox = ox.reindex(f.index).shift(1)  # PRIOR-day surface only
        for c in ox.columns:
            f[c] = ox[c]
        # variance risk premium: implied (annualized) minus realized (annualized)
        f["ox_vrp"] = f["ox_atm_iv30"] - f["rv_20"] * np.sqrt(252)
    return _finish(f, d, m, sym)


def _finish(
    f: pd.DataFrame, d: pd.DataFrame, m: pd.DataFrame, sym: str
) -> pd.DataFrame:
    # ---- labels: next-day path, day-flat (y_ prefix) ----
    rv20 = f["rv_20"]
    mc, mtd = m["c"].to_numpy(float), m["td"].to_numpy()
    days = d.index.to_numpy()
    starts = np.searchsorted(mtd, days)
    y = np.full(len(d), np.nan)
    for i in range(len(days) - 2):
        if not np.isfinite(rv20.iloc[i]) or rv20.iloc[i] <= 0:
            continue
        a, b = starts[i + 1], starts[i + 2]
        seg = mc[a:b]
        if len(seg) < 50:
            continue
        entry = seg[0]
        tgt, stp = entry * (1 + 1.0 * rv20.iloc[i]), entry * (1 - 0.75 * rv20.iloc[i])
        ht = np.flatnonzero(seg >= tgt)
        hs = np.flatnonzero(seg <= stp)
        it = ht[0] if len(ht) else 10**12
        is_ = hs[0] if len(hs) else 10**12
        if is_ <= it and is_ < 10**12:
            y[i] = -1.0
        elif it < 10**12:
            y[i] = 1.0 / 0.75
        else:
            y[i] = float((seg[-1] / entry - 1) / (0.75 * rv20.iloc[i]))
    f["y_tbR"] = y
    f["rv20_bps"] = rv20 * 1e4
    f["c_px"] = d["c"]
    out = MODULE / "data"
    out.mkdir(exist_ok=True)
    f = f.copy()
    tag = sym.split(".")[0].lower()
    f.to_parquet(out / f"features_{tag}.parquet")
    n_feat = len(
        [
            c
            for c in f.columns
            if not c.startswith("y_") and c not in ("rv20_bps", "c_px")
        ]
    )
    print(
        f"{sym} matrix: {n_feat} features x {len(f)} days ({f.index.min().date()} -> {f.index.max().date()})"
    )
    print(
        f"label coverage {f['y_tbR'].notna().mean():.0%}, win rate {(f['y_tbR'] > 0).mean():.0%}"
    )
    return f


if __name__ == "__main__":
    build()
