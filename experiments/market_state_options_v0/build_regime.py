"""market_state_options_v0 — options-REGIME market-state, characterized honestly (CONTEXT, not a signal).

Computes, per day at a causal decision minute (10:00 ET; prior-day OI + that-minute chain), the options
regime: net dealer GEX (sign+magnitude), 0DTE share, zero-gamma flip level, call/put walls, spot-vs-flip.
Then measures how the REST OF DAY historically behaves in each regime (realized range / trend-vs-chop /
close location). This is decision-support CONTEXT — gamma as a DIRECTIONAL predictor is null in this lab
(stock_options_flow, mstr_gamma, the GEX gate) — so we report regime BEHAVIOUR (range/pin), not buy/sell.

GEX convention: net = gamma * oi_prior * (call +1 / put -1); negative = dealers short gamma = trend-prone;
positive = long gamma = pin-prone. The SIGN/level vs history is what matters, not the absolute scale.

  python build_regime.py NDXP
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data_io import load_option_panel  # noqa: E402
import pyarrow.dataset as ds  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
DEC_MIN = 600        # 10:00 ET in minutes-of-day
DTE0 = 0.6           # ~same-session expiry


def _panel_base(root):
    for b in [Path(r"E:\data\processed\option_panels\panel"), Path(r"D:\data\processed\option_panels\panel")]:
        if (b / f"root={root}").exists():
            return b / f"root={root}"
    return None


def zero_gamma(per_strike: pd.Series) -> float:
    s = per_strike.sort_index()
    cum = s.cumsum().to_numpy()
    k = s.index.to_numpy(float)
    x = np.where(np.diff(np.sign(cum)) != 0)[0]
    if not len(x):
        return float("nan")
    i = x[0]
    return float(np.interp(0, [cum[i], cum[i + 1]], [k[i], k[i + 1]])) if cum[i] != cum[i + 1] else float(k[i])


def day_regime(root, date):
    df = load_option_panel(root, int(date))
    df = df[df.gamma.notna() & df.oi_prior.notna() & df.underlying_price.notna()]
    if len(df) < 1000:
        return None
    df = df.assign(min=(df.ms_of_day // 60000).astype(int),
                   sgn=np.where(df.right.astype(str).str.upper().str[0] == "C", 1.0, -1.0))
    df["g_oi"] = df.gamma * df.oi_prior * df.sgn
    spot = df.groupby("min").underlying_price.median()
    if DEC_MIN not in spot.index:
        return None
    # regime AT 10:00 (causal: prior-day OI + that-minute chain)
    chain = df[df["min"] == DEC_MIN]
    s0 = float(spot.loc[DEC_MIN])
    net = chain.groupby("strike")["g_oi"].sum()
    gex = float(chain["g_oi"].sum()) * s0 * s0 / 1e9
    z = chain[chain.dte <= DTE0]
    gex0 = float(z["g_oi"].sum()) * s0 * s0 / 1e9 if len(z) else np.nan
    zg = zero_gamma(net)
    cw = float(net.idxmax()); pw = float(net.idxmin())
    # rest-of-day behaviour (after 10:00)
    rod = spot.loc[spot.index >= DEC_MIN]
    hi, lo, cl = float(rod.max()), float(rod.min()), float(rod.iloc[-1])
    rng = (hi - lo) / s0 * 100
    trend = abs(cl - s0) / (hi - lo) if hi > lo else np.nan      # 1=pure trend, ~0=chop/round-trip
    close_above_zg = (cl > zg) if np.isfinite(zg) else np.nan
    return dict(date=int(date), spot=s0, gex=gex, gex0=gex0,
                short_gamma=int(gex < 0), zero_gamma=zg, call_wall=cw, put_wall=pw,
                dist_zg_pct=(s0 - zg) / s0 * 100 if np.isfinite(zg) else np.nan,
                rod_range_pct=rng, rod_trend=trend, close_above_zg=close_above_zg,
                rod_ret_pct=(cl - s0) / s0 * 100)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "NDXP"
    base = _panel_base(root)
    dates = sorted(int(p.name.split("=")[1]) for p in base.glob("date=*"))
    rows = []
    for i, d in enumerate(dates):
        try:
            r = day_regime(root, d)
            if r:
                rows.append(r)
        except Exception as e:
            print(f"  {d} ERR {type(e).__name__}: {str(e)[:50]}", flush=True)
        if i % 40 == 0:
            print(f"  {i}/{len(dates)}", flush=True)
    df = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / f"regime_{root}.csv", index=False)
    print(f"\n== {root} options-regime characterization ({len(df)} days) ==")
    print(f"  short-gamma days: {df.short_gamma.mean():.0%} | 0DTE share of |GEX| median: "
          f"{(df.gex0.abs()/(df.gex.abs()+1e-9)).median():.0%}")
    sg = df[df.short_gamma == 1]; lg = df[df.short_gamma == 0]
    print(f"\n  REST-OF-DAY behaviour by gamma regime (CONTEXT, not a direction call):")
    print(f"  {'regime':14} {'n':>4} {'med range%':>10} {'med trend':>10} {'range>1%':>9}")
    for nm, g in [("SHORT-gamma", sg), ("LONG-gamma", lg)]:
        if len(g):
            print(f"  {nm:14} {len(g):>4} {g.rod_range_pct.median():>10.2f} {g.rod_trend.median():>10.2f} "
                  f"{(g.rod_range_pct>1).mean():>8.0%}")
    # GEX magnitude vs realized range (does more positive gamma suppress range?)
    ic = df[["gex", "rod_range_pct"]].corr().iloc[0, 1]
    print(f"\n  corr(GEX, rest-of-day range) = {ic:+.3f}  (negative => more negative GEX/short-gamma = bigger range)")
    print(f"  corr(|dist to zero-gamma|, range) = {df[['dist_zg_pct','rod_range_pct']].assign(a=df.dist_zg_pct.abs())[['a','rod_range_pct']].corr().iloc[0,1]:+.3f}")
    print(f"  written: out/regime_{root}.csv")


if __name__ == "__main__":
    main()
