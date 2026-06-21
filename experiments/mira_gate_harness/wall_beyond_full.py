"""WALL-BEYOND-LEVEL at FULL SCALE (Ben's stop-hunt-into-dealer-wall headline).

A reclaim is hypothesized stronger when a dealer gamma WALL rests just BEYOND the swept level:
call wall just ABOVE a swept high (short), put wall just BELOW a swept low (long) -- the sweep grabs
the stop cluster AND hits the dealer barrier at one price. The pilot (gamma_confluence_pilot) saw
+0.44 vs +0.06 but on n=12 (gex_levels only covered 2025-05+). THIS runs the SAME flag on the full
reclaim universe (legal_bars_full, 79k entered reclaims, 2015-2026) x the already-built full-history
wall files (walls_v2/ndx/rut/djx, 2017/2018-2026) -> ~8 yrs, 4 indices, NO pull, NO rebuild.

Legality identical to gamma_wall_legal: wall for session D = most recent wall row with date < D
(prior trading day, built from D-1 EOD greeks), futures-mapped via prior-day 16:00-ET basis.
Controls: SHUFFLE null (permute wall->date within symbol), PLACEBO (wrong-side wall), per-year, per-family.
"""
from __future__ import annotations

import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
import legal_reclaim_bars as LB  # noqa: E402
import app.data.reader as R  # noqa: E402

TICK = LB.TICK
ET16 = dt.time(16, 0)
POL = "trail_2R"           # primary outcome (matches gamma_wall_legal); fixed_3R reported as 2nd
WALL_FILES = {
    "ES.c.0": (ROOT / "experiments/fuhhhhh/out/walls_v2.parquet", 1.0),
    "NQ.c.0": (ROOT / "experiments/fuhhhhh/out/walls_ndx.parquet", 1.0),
    "YM.c.0": (ROOT / "experiments/options_signals_v0/out/walls_djx.parquet", 100.0),
    "RTY.c.0": (ROOT / "experiments/options_signals_v0/out/walls_rut.parquet", 1.0),
}


def build_walls(sym: str) -> dict:
    """{session_date: (call_wall_fut, put_wall_fut)} futures-priced, prior-day-legal (date<D, <=7d)."""
    path, scale = WALL_FILES[sym]
    tick = TICK[sym]
    g = pd.read_parquet(path).sort_values("date")
    g["d"] = pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d").dt.date
    w0 = (pd.Timestamp(g["d"].min()) - pd.Timedelta(days=10)).date().isoformat()
    w1 = (pd.Timestamp(g["d"].max()) + pd.Timedelta(days=3)).date().isoformat()
    bars = R.read_bars(symbol=sym, timeframe="1m", start=w0, end=w1, columns=["ts_event", "close"])
    bi = pd.DatetimeIndex(pd.to_datetime(bars["ts_event"], utc=True))
    bc = bars["close"].to_numpy(float)
    basis: dict = {}
    for _, row in g.iterrows():
        ts = pd.Timestamp(dt.datetime.combine(row["d"], ET16), tz=LB.ET).tz_convert("UTC")
        pos = bi.searchsorted(ts, side="right") - 1
        if pos < 0 or (ts - bi[pos]) > pd.Timedelta(minutes=30):
            continue
        basis[row["d"]] = float(bc[pos]) - float(row["spot"]) * scale
    gex_dates = np.array([d for d in g["d"] if d in basis])
    by_date = g.set_index("d")
    out: dict = {}
    d = g["d"].min()
    end = g["d"].max() + dt.timedelta(days=5)
    while d <= end:
        idx = gex_dates.searchsorted(d) - 1  # most recent prior date
        if idx >= 0:
            src = gex_dates[idx]
            if (d - src).days <= 7:
                b = basis[src]
                cw = float(by_date.loc[src, "call_wall"]) * scale + b
                pw = float(by_date.loc[src, "put_wall"]) * scale + b
                out[d] = (round(cw / tick) * tick, round(pw / tick) * tick)
        d += dt.timedelta(days=1)
    print(f"  {sym}: {len(out)} sessions w/ prior-day walls (file {len(g)} days)", flush=True)
    return out


def flag(sym, side, lvl, walls_for_day, band_tk, wrong_side=False):
    """1 if a wall sits within band_tk BEYOND the swept level (correct side); -1 if no wall data."""
    if walls_for_day is None:
        return -1
    cw, pw = walls_for_day
    tick = TICK[sym]
    band = band_tk * tick
    want_call = (side == "high") ^ wrong_side  # short wants call-wall-above; placebo flips
    if want_call:
        return 1 if (np.isfinite(cw) and lvl <= cw <= lvl + band) else 0
    return 1 if (np.isfinite(pw) and lvl - band <= pw <= lvl) else 0


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):5d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=    0"


def lift(sub, col):
    a = pd.to_numeric(sub[sub[col] == 1][POL], errors="coerce").dropna()
    b = pd.to_numeric(sub[sub[col] == 0][POL], errors="coerce").dropna()
    return (a.mean() - b.mean()) if (len(a) and len(b)) else np.nan


def main() -> int:
    print("=== building full-history walls (futures-mapped, prior-day-legal) ===", flush=True)
    WALLS = {s: build_walls(s) for s in WALL_FILES}

    d = pd.read_parquet(LB.RUNS / "legal_bars_full.parquet")
    d = d[d["status"] == "entered"].copy()
    # drop degenerate near-zero-risk rows (risk_pts ~ 0 -> R explodes); 1 such row taints pooled means
    n0 = len(d)
    d = d[pd.to_numeric(d["risk_tk"], errors="coerce") >= 0.5]
    d = d[(pd.to_numeric(d["trail_2R"], errors="coerce").abs() < 50) &
          (pd.to_numeric(d["fixed_3R"], errors="coerce").abs() < 50)]
    print(f"dropped {n0-len(d)} degenerate rows; {len(d):,} clean entered reclaims", flush=True)
    d["sd"] = pd.to_datetime(d["session_date"]).dt.date
    d["yr"] = pd.to_datetime(d["session_date"]).dt.year
    d["wday"] = [WALLS.get(s, {}).get(sd) for s, sd in zip(d["symbol"], d["sd"])]

    for b in (10, 20, 40):
        d[f"wb{b}"] = [flag(s, sd_side, lp, w, b) for s, sd_side, lp, w in
                       zip(d["symbol"], d["side"], d["level_price"].astype(float), d["wday"])]
    d["wb20_placebo"] = [flag(s, sd_side, lp, w, 20, wrong_side=True) for s, sd_side, lp, w in
                         zip(d["symbol"], d["side"], d["level_price"].astype(float), d["wday"])]
    cov = d[d["wb20"] >= 0].copy()
    print(f"\nwall-data coverage: {len(cov):,}/{len(d):,} reclaims have prior-day walls "
          f"(by symbol {cov['symbol'].value_counts().to_dict()})")
    print(f"covered years: {sorted(cov['yr'].unique())}")

    print(f"\n=== (1) HEADLINE: wall-beyond vs none, pooled, by band [{POL}] ===")
    for b in (10, 20, 40):
        has = cov[cov[f"wb{b}"] == 1]
        no = cov[cov[f"wb{b}"] == 0]
        print(f"  band {b:2d}tk: WALL-BEYOND {st(has[POL])} | none {st(no[POL])} | "
              f"lift {lift(cov, f'wb{b}'):+.3f}  (wb count {len(has)})")
    print(f"  PLACEBO (wrong-side wall, 20tk): {st(cov[cov['wb20_placebo']==1][POL])} | "
          f"lift {lift(cov.assign(_p=cov['wb20_placebo']), '_p'):+.3f}  <- should be ~0")

    print(f"\n=== (2) per-YEAR stability (band 20tk lift) ===")
    for y in sorted(cov["yr"].unique()):
        s = cov[cov["yr"] == y]
        has = s[s["wb20"] == 1]
        print(f"  {y}: WALL-BEYOND {st(has[POL])} | lift {lift(s,'wb20'):+.3f}")
    des = cov[cov["yr"] <= 2022]
    oos = cov[cov["yr"] >= 2023]
    print(f"  DESIGN 2018-2022: lift {lift(des,'wb20'):+.3f} (wb {int((des['wb20']==1).sum())}) | "
          f"OOS 2023-2026: lift {lift(oos,'wb20'):+.3f} (wb {int((oos['wb20']==1).sum())})")

    print(f"\n=== (3) per-SYMBOL (band 20tk) ===")
    for s, g in cov.groupby("symbol"):
        print(f"  {s:8s}: WALL-BEYOND {st(g[g['wb20']==1][POL])} | none {st(g[g['wb20']==0][POL])} | "
              f"lift {lift(g,'wb20'):+.3f}")

    print(f"\n=== (4) per-LEVEL-FAMILY (band 20tk lift; thesis: concentrates on liquidity/stop-cluster) ===")
    for fam, g in cov.groupby("level_family"):
        if (g["wb20"] == 1).sum() >= 20:
            print(f"  {fam:16s}: wb {st(g[g['wb20']==1][POL])} | lift {lift(g,'wb20'):+.3f}")

    print(f"\n=== (5) SHUFFLE NULL: permute wall->date within symbol, N=200 (real lift vs null) ===")
    rng = np.random.default_rng(7)
    real = lift(cov, "wb20")
    null = []
    cov_sym = {s: cov[cov["symbol"] == s].copy() for s in WALL_FILES}
    for _ in range(200):
        parts = []
        for s, g in cov_sym.items():
            dates = list(WALLS[s].keys())
            wl = list(WALLS[s].values())
            perm = rng.permutation(len(wl))
            shuf = {dates[i]: wl[perm[i]] for i in range(len(dates))}
            wb = [flag(s, sd_side, lp, shuf.get(sd), 20) for sd_side, lp, sd in
                  zip(g["side"], g["level_price"].astype(float), g["sd"])]
            gg = g.assign(_wb=wb)
            parts.append(gg)
        nn = pd.concat(parts)
        null.append(lift(nn.rename(columns={"_wb": "x"}), "x") if "_wb" not in nn else
                    (pd.to_numeric(nn[nn["_wb"] == 1][POL], errors="coerce").dropna().mean() -
                     pd.to_numeric(nn[nn["_wb"] == 0][POL], errors="coerce").dropna().mean()))
    null = np.array([x for x in null if np.isfinite(x)])
    z = (real - null.mean()) / null.std() if null.std() > 0 else np.nan
    p = float((null >= real).mean())
    print(f"  real lift {real:+.4f} | null mean {null.mean():+.4f} std {null.std():.4f} | "
          f"z={z:+.2f} p(null>=real)={p:.3f}")

    print(f"\n=== (6) fixed_3R cross-check (band 20tk) ===")
    pol2 = "fixed_3R"
    a = pd.to_numeric(cov[cov["wb20"] == 1][pol2], errors="coerce").dropna()
    b = pd.to_numeric(cov[cov["wb20"] == 0][pol2], errors="coerce").dropna()
    print(f"  WALL-BEYOND n={len(a)} R={a.mean():+.3f} | none n={len(b)} R={b.mean():+.3f} | "
          f"lift {a.mean()-b.mean():+.3f}")

    cov.to_parquet(LB.RUNS / "wall_beyond_full_scored.parquet", index=False)
    print(f"\nwrote {LB.RUNS/'wall_beyond_full_scored.parquet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
