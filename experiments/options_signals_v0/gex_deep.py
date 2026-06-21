"""Deeper GEX v2: wider flip detection + distance-to-flip as a continuous signal + GATE the reversion.

gex_flip_walls v1 found a FAINT right-direction signal (below-flip more trendy) but the +/-5% grid found
a flip on only 46% of days. This widens the strike band + grid, computes a signed distance-to-flip for
every day, and runs the tests that actually matter:
  A) distance-to-flip (continuous) -> next-day ES trendiness + realized vol (corr + terciles)
  B) GATE the daily expansion-reversion fade on ABOVE vs BELOW the flip  <- the user's actual idea
Honest: VIX-flat IV v0, SPX 2025, n~245 (small). Suggestive, not a verdict.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/gex_deep.py
"""
from __future__ import annotations

from pathlib import Path

import databento as db
import numpy as np
import pandas as pd
from scipy.stats import norm

RAW = Path("D:/data/raw/opra")
OUT = Path("experiments/options_signals_v0/out")
MONEYP, MONTHS = 0.25, [f"2025-{m:02d}" for m in range(1, 13)]


def profile(Sgrid, K, sig, T, oi, mult, sign):
    S = Sgrid[:, None]
    sq = sig * np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * sig ** 2 * T) / sq
    return np.sum(sign * norm.pdf(d1) / (S * sq) * oi * mult * S ** 2 * 0.01, axis=1)


def build() -> pd.DataFrame:
    spot = pd.read_parquet(Path(__file__).resolve().parents[1] / "tgif_v0" / "out" / "ES_dailyET.parquet")["close"]
    spot.index = pd.to_datetime(spot.index).tz_localize(None).normalize()
    vix = pd.read_parquet(OUT / "vix_history.parquet")["VIX"] / 100.0
    vix.index = pd.to_datetime(vix.index).tz_localize(None).normalize()
    rows = []
    for mo in MONTHS:
        dfd = db.DBNStore.from_file(RAW / "definition" / f"SPX_OPT_{mo}.dbn.zst").to_df()
        im = (dfd.dropna(subset=["strike_price", "expiration"]).groupby("instrument_id")
              .agg(K=("strike_price", "last"), cls=("instrument_class", "last"),
                   exp=("expiration", "last"), mult=("contract_multiplier", "last")))
        im["mult"] = im["mult"].fillna(100).replace(0, 100)
        im["expN"] = pd.to_datetime(im["exp"]).dt.tz_localize(None)
        st = db.DBNStore.from_file(RAW / "statistics" / f"SPX_OPT_{mo}.dbn.zst").to_df()
        st = st[st["stat_type"] == 9].copy()
        st["date"] = pd.to_datetime(st["ts_event"]).dt.tz_localize(None).dt.normalize()
        for d, g in st.groupby("date"):
            if d not in spot.index or d not in vix.index or not np.isfinite(vix.loc[d]):
                continue
            S, sig = float(spot.loc[d]), float(vix.loc[d])
            oi = g.groupby("instrument_id")["quantity"].last()
            j = im.join(oi.rename("oi"), how="inner")
            j = j[j["oi"] > 0]
            j["T"] = (j["expN"] - d).dt.total_seconds() / (365.25 * 86400)
            j = j[(j["T"] > 1 / 365) & (np.abs(j["K"] / S - 1) < MONEYP)]
            if len(j) < 20:
                continue
            K, T, oiv = j["K"].to_numpy(), j["T"].to_numpy(), j["oi"].to_numpy()
            mult, sign = j["mult"].to_numpy(), np.where(j["cls"].to_numpy() == "C", 1.0, -1.0)
            grid = S * np.linspace(0.85, 1.15, 301)
            pr = profile(grid, K, sig, T, oiv, mult, sign)
            cr = np.where(np.diff(np.sign(pr)) != 0)[0]
            if len(cr):
                i = cr[np.argmin(np.abs(grid[cr] - S))]
                flip = float(np.interp(0, [pr[i], pr[i + 1]], [grid[i], grid[i + 1]]))
                dist = (S - flip) / S
            else:                                   # no crossing: deep one-sided gamma
                flip, dist = np.nan, (0.15 if pr[len(pr) // 2] > 0 else -0.15)
            rows.append({"date": d, "spot": S, "flip": flip, "dist_flip": dist})
    out = pd.DataFrame(rows).set_index("date").sort_index()
    out.to_parquet(OUT / "spx_flip_v2.parquet")
    return out


def daily_fade(es: pd.DataFrame, K=1.5, RET=0.33, BUF=0.25) -> pd.DataFrame:
    o, h, l, c = (es[x].to_numpy() for x in ["open", "high", "low", "close"])
    rng = h - l
    avg = pd.Series(rng).rolling(20).mean().shift(1).to_numpy()
    rows = []
    for t in range(20, len(es) - 1):
        if not np.isfinite(avg[t]) or rng[t] <= 0 or rng[t] <= K * avg[t]:
            continue
        up = c[t] > o[t]
        side = -1 if up else 1                       # fade
        entry = o[t + 1]
        if side == -1:
            stop, tgt = h[t] + BUF * rng[t], entry - RET * rng[t]; risk = stop - entry
            r = -1.0 if h[t + 1] >= stop else ((entry - tgt) / risk if l[t + 1] <= tgt else (entry - c[t + 1]) / risk)
        else:
            stop, tgt = l[t] - BUF * rng[t], entry + RET * rng[t]; risk = entry - stop
            r = -1.0 if l[t + 1] <= stop else ((tgt - entry) / risk if h[t + 1] >= tgt else (c[t + 1] - entry) / risk)
        if risk > 0:
            rows.append({"date": es.index[t], "side": side, "r": r - 1.0 * 0.25 / risk})
    return pd.DataFrame(rows).set_index("date")


def main() -> int:
    fw = build()
    es = pd.read_parquet(OUT / "es_daily_intraday.parquet").set_index("date")
    es.index = pd.to_datetime(es.index).tz_localize(None).normalize()
    m = es.join(fw[["dist_flip"]].shift(1), how="inner").dropna(subset=["eff", "rv", "dist_flip"])
    print(f"built flip for {len(fw)} days | flip-in-grid {100*fw['flip'].notna().mean():.0f}% | merged {len(m)}\n")
    print("A) distance-to-flip (signed; +=above/pin, -=below/trend) -> next-day ES")
    m = m.copy(); m["b"] = pd.qcut(m["dist_flip"], 3, labels=["below", "mid", "above"], duplicates="drop")
    print(m.groupby("b", observed=True).agg(n=("eff", "size"), trendiness=("eff", "mean"),
          vol=("rv", "mean")).to_string(float_format=lambda x: f"{x:.4f}"))
    print(f"   corr(dist_flip, trendiness) = {m['dist_flip'].corr(m['eff']):+.3f}  "
          f"corr(dist_flip, vol) = {m['dist_flip'].corr(m['rv']):+.3f}\n")

    esd = pd.read_parquet(Path(__file__).resolve().parents[1] / "tgif_v0" / "out" / "ES_dailyET.parquet")
    esd.index = pd.to_datetime(esd.index).tz_localize(None).normalize()
    fade = daily_fade(esd).join(fw[["flip", "dist_flip"]], how="inner").dropna(subset=["r"])
    fade["above"] = fade["dist_flip"] > 0
    print("B) GATE the daily expansion-reversion fade on flip position:")
    for sd, sl in [(1, "long "), (-1, "short")]:
        for ab, al in [(True, "ABOVE flip (pin)"), (False, "BELOW flip (trend)")]:
            r = fade[(fade["side"] == sd) & (fade["above"] == ab)]["r"]
            tag = f"E[R]={r.mean():+.3f} n={len(r)}" if len(r) >= 10 else f"n={len(r)} thin"
            print(f"   {sl} {al:20} {tag}")
    allr = fade["r"]
    print(f"   (ungated fade overall: E[R]={allr.mean():+.3f} n={len(allr)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
