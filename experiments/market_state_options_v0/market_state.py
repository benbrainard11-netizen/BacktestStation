"""market_state — the packaged options market-state readout: one call per (index, time).

Combines the VALIDATED pieces into a single honest CONTEXT readout for a discretionary trader:
  - gamma regime (net dealer GEX sign/magnitude; short=trend/big-range, long=pin/chop)
  - PROJECTED range over 1h / 4h / EOD (regression range ~ trailing_range + GEX, fit per decision-time
    bucket on the validated mtf data; the additive-over-vol read that generalized NDX/SPX/RUT)
  - levels: zero-gamma flip, call/put walls, 0DTE pin
  - 0DTE expected move (ATM 0DTE straddle / spot)
  - vol regime: VIX level + term structure (VIX1D/VIX/VIX9D contango↔backwardation) + VVIX, prior-day (causal)
All causal (prior-day OI + chain ≤ time + prior-day vol indices). NOT a direction call — context only.

  python market_state.py NDX 20260612 690      # index, date, minute-of-day (690=11:30 ET)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data_io import load_option_panel  # noqa: E402
from build_regime import _panel_base, zero_gamma  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
VOLDIR = Path(__file__).resolve().parents[1] / "options_signals_v0" / "out" / "vol_indices"
ROOTS = {"NDX": "NDXP", "SPX": "SPXW", "RUT": "RUTW"}
DEC_TIMES = [600, 690, 780, 870]
HORIZONS = {"1h": 60, "4h": 240, "EOD": 999}


def fit_projection(index):
    """range ~ a + b*trailing_range + c*GEX per (decision-time bucket, horizon), from the mtf data."""
    cf = OUT / f"proj_{index}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    df = pd.read_csv(OUT / f"mtf_{ROOTS[index]}.csv")
    coefs = {}
    for T in DEC_TIMES:
        for hn in HORIZONS:
            s = df[(df["T"] == T) & (df["horizon"] == hn)].dropna(subset=["trail_rng", "gex", "fwd_range"])
            if len(s) < 30:
                continue
            X = np.c_[np.ones(len(s)), s.trail_rng.values, s.gex.values]
            b = np.linalg.lstsq(X, s.fwd_range.values, rcond=None)[0]
            coefs[f"{T}_{hn}"] = {"a": float(b[0]), "b_trail": float(b[1]), "c_gex": float(b[2]),
                                  "short_med": float(s[s.short_gamma == 1].fwd_range.median()),
                                  "long_med": float(s[s.short_gamma == 0].fwd_range.median())}
    cf.write_text(json.dumps(coefs, indent=2))
    return coefs


def _prior_close(name, date):
    f = VOLDIR / f"{name}.parquet"
    if not f.exists():
        return None
    d = pd.read_parquet(f)
    d = d[d.date < int(date)]
    return float(d.sort_values("date")["close"].iloc[-1]) if len(d) else None


def vol_regime(date):
    v, v1, v9, vv = (_prior_close(n, date) for n in ("VIX", "VIX1D", "VIX9D", "VVIX"))
    out = {"vix": v, "vix1d": v1, "vix9d": v9, "vvix": vv}
    if v is not None:
        out["level"] = "low" if v < 15 else "elevated" if v < 22 else "high"
    if v1 is not None and v is not None:
        out["term"] = "backwardation (near-term stress)" if v1 > v * 1.02 else "contango (calm)" if v1 < v * 0.98 else "flat"
    return out


def market_state(index: str, date: int, time_min: int) -> dict | None:
    root = ROOTS[index.upper()]
    df = load_option_panel(root, int(date))
    df = df[df.gamma.notna() & df.oi_prior.notna() & df.underlying_price.notna()]
    if not len(df):
        return None
    df = df.assign(min=(df.ms_of_day // 60000).astype(int),
                   sgn=np.where(df.right.astype(str).str.upper().str[0] == "C", 1.0, -1.0))
    df["g_oi"] = df.gamma * df.oi_prior * df.sgn
    df = df[df["min"] <= int(time_min)]                                  # causal: chain up to now
    if not len(df):
        return None
    spot_path = df.groupby("min").underlying_price.median()
    cur = int(spot_path.index.max())
    chain = df[df["min"] == cur]
    spot = float(spot_path.loc[cur])
    gex = float(chain["g_oi"].sum()) * spot * spot / 1e9
    net = chain.groupby("strike")["g_oi"].sum()
    zg, cw, pw = zero_gamma(net), float(net.idxmax()), float(net.idxmin())
    trail = spot_path.loc[spot_path.index >= cur - 60]
    trail_rng = float((trail.max() - trail.min()) / spot * 100) if len(trail) > 3 else 0.0
    # 0DTE expected move + pin
    z = chain[chain.dte <= 0.6]
    em = pin = None
    if len(z):
        atm = float(z.iloc[(z.strike - spot).abs().argmin()].strike)
        leg = z[z.strike == atm]
        c = leg[leg.right.astype(str).str.upper().str[0] == "C"]["mid"]
        p = leg[leg.right.astype(str).str.upper().str[0] == "P"]["mid"]
        if len(c) and len(p):
            em = float((c.iloc[0] + p.iloc[0]) / spot * 100)
        znet = z.groupby("strike")["g_oi"].apply(lambda s: s.abs().sum())
        pin = float(znet.idxmax()) if len(znet) else None
    # projections
    coefs = fit_projection(index.upper())
    Tb = min(DEC_TIMES, key=lambda t: abs(t - cur))
    proj = {}
    for hn in HORIZONS:
        k = f"{Tb}_{hn}"
        if k in coefs:
            c = coefs[k]
            proj[hn] = round(max(0.0, c["a"] + c["b_trail"] * trail_rng + c["c_gex"] * gex), 2)
    regime = "SHORT-gamma (trend-prone / big-range)" if gex < 0 else "LONG-gamma (pin-prone / chop)"
    return {"index": index.upper(), "date": int(date), "time": f"{cur // 60}:{cur % 60:02d}",
            "spot": round(spot, 1), "gamma_regime": regime, "gex_bn_per_1pct": round(gex, 2),
            "projected_range_pct": proj, "trailing_30m_range_pct": round(trail_rng, 2),
            "levels": {"zero_gamma": round(zg, 1) if np.isfinite(zg) else None,
                       "call_wall": round(cw, 1), "put_wall": round(pw, 1), "spot_vs_zero_gamma":
                       ("above" if (np.isfinite(zg) and spot > zg) else "below" if np.isfinite(zg) else None)},
            "zerodte": {"expected_move_pct": round(em, 2) if em else None, "pin": round(pin, 1) if pin else None},
            "vol_regime": vol_regime(date)}


def narrate(s):
    p = s["projected_range_pct"]; lv = s["levels"]; vr = s["vol_regime"]; z = s["zerodte"]
    pr = " / ".join(f"{h} {p[h]}%" for h in ("1h", "4h", "EOD") if h in p)
    return (f"{s['index']} {s['time']} | spot {s['spot']} | {s['gamma_regime']} (GEX {s['gex_bn_per_1pct']})\n"
            f"  PROJECTED RANGE: {pr}   (trailing 30m {s['trailing_30m_range_pct']}%)\n"
            f"  LEVELS: zero-gamma {lv['zero_gamma']} (spot {lv['spot_vs_zero_gamma']}) | walls {lv['put_wall']}/{lv['call_wall']}"
            f" | 0DTE pin {z['pin']} | 0DTE EM {z['expected_move_pct']}%\n"
            f"  VOL: VIX {vr.get('vix')} ({vr.get('level')}, {vr.get('term')}) | VVIX {vr.get('vvix')}\n"
            f"  CONTEXT (not a direction call): {'expect range/follow-through — size for movement' if s['gex_bn_per_1pct']<0 else 'expect chop/mean-reversion — fade extremes, smaller targets'}")


if __name__ == "__main__":
    idx = sys.argv[1] if len(sys.argv) > 1 else "NDX"
    dt = int(sys.argv[2]) if len(sys.argv) > 2 else None
    tm = int(sys.argv[3]) if len(sys.argv) > 3 else 690
    if dt is None:
        base = _panel_base(ROOTS[idx]); dt = sorted(int(p.name.split("=")[1]) for p in base.glob("date=*"))[-1]
    s = market_state(idx, dt, tm)
    print(json.dumps(s, indent=2) if s else "no state"); print()
    if s:
        print(narrate(s))
