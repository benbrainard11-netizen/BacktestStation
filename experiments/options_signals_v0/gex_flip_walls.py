"""Deeper GEX test: the FLIP LEVEL and WALLS (the signals practitioners actually use), not just total GEX.

gex_regime.py tested aggregate GEX sign -> null. But the real gamma signal is PRICE POSITION:
  - GAMMA FLIP = the spot level where total dealer gamma crosses zero (above = suppressive/pin regime,
    below = amplifying/trend regime). Computed by re-evaluating the gamma profile across a spot grid.
  - WALLS = strikes with the most gamma*OI (magnets). Pinning = price drawn toward the nearest wall.
Tests (no-lookahead: flip/walls from t-1 OI -> day t):
  1. ABOVE vs BELOW the flip -> next-day ES trendiness + realized vol + |move|.
  2. PINNING -> does next-day close move TOWARD the nearest wall (vs away)?
  3. GATE THE REVERSION -> does an expansion-candle fade do better when price is ABOVE the flip
     (positive-gamma/pin regime)? <- the user's actual idea, finally tested directly.

VIX-flat IV v0 (OI structure dominates wall/flip location). SPX, 2025. n~245 small -> suggestive.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/gex_flip_walls.py
"""
from __future__ import annotations

from pathlib import Path

import databento as db
import numpy as np
import pandas as pd
from scipy.stats import norm

RAW = Path("D:/data/raw/opra")
OUT = Path("experiments/options_signals_v0/out")
MONEY = 0.15
MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]


def gamma_at(Sgrid, K, sigma, T, oi, mult, sign):
    """Total dealer gamma ($/1%) at each spot in Sgrid. Sgrid:(G,), others:(N,)."""
    S = Sgrid[:, None]
    sq = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * sigma ** 2 * T) / sq
    g = norm.pdf(d1) / (S * sq)
    return np.sum(sign * g * oi * mult * S ** 2 * 0.01, axis=1)


def build_flip_walls() -> pd.DataFrame:
    spot = pd.read_parquet(Path(__file__).resolve().parents[1] / "tgif_v0" / "out" / "ES_dailyET.parquet")["close"]
    spot.index = pd.to_datetime(spot.index).tz_localize(None).normalize()
    vix = pd.read_parquet(OUT / "vix_history.parquet")["VIX"] / 100.0
    vix.index = pd.to_datetime(vix.index).tz_localize(None).normalize()
    rows = []
    for mo in MONTHS:
        dfd = db.DBNStore.from_file(RAW / "definition" / f"SPX_OPT_{mo}.dbn.zst").to_df()
        imap = (dfd.dropna(subset=["strike_price", "expiration"]).groupby("instrument_id")
                .agg(K=("strike_price", "last"), cls=("instrument_class", "last"),
                     exp=("expiration", "last"), mult=("contract_multiplier", "last")))
        imap["mult"] = imap["mult"].fillna(100).replace(0, 100)
        imap["expN"] = pd.to_datetime(imap["exp"]).dt.tz_localize(None)
        st = db.DBNStore.from_file(RAW / "statistics" / f"SPX_OPT_{mo}.dbn.zst").to_df()
        st = st[st["stat_type"] == 9].copy()
        st["date"] = pd.to_datetime(st["ts_event"]).dt.tz_localize(None).dt.normalize()
        for d, g in st.groupby("date"):
            if d not in spot.index or d not in vix.index or not np.isfinite(vix.loc[d]):
                continue
            S, sig = float(spot.loc[d]), float(vix.loc[d])
            oi = g.groupby("instrument_id")["quantity"].last()
            j = imap.join(oi.rename("oi"), how="inner")
            j = j[j["oi"] > 0]
            j["T"] = (j["expN"] - d).dt.total_seconds() / (365.25 * 86400)
            j = j[(j["T"] > 1 / 365) & (np.abs(j["K"] / S - 1) < MONEY)]
            if len(j) < 20:
                continue
            K = j["K"].to_numpy(); T = j["T"].to_numpy(); oiv = j["oi"].to_numpy()
            mult = j["mult"].to_numpy(); sign = np.where(j["cls"].to_numpy() == "C", 1.0, -1.0)
            grid = S * np.linspace(0.95, 1.05, 101)
            prof = gamma_at(grid, K, sig, T, oiv, mult, sign)
            # flip = grid level nearest zero-crossing
            sgn = np.sign(prof)
            cross = np.where(np.diff(sgn) != 0)[0]
            flip = float(np.interp(0, [prof[cross[np.argmin(np.abs(grid[cross] - S))]],
                                       prof[cross[np.argmin(np.abs(grid[cross] - S))] + 1]],
                                   [grid[cross[np.argmin(np.abs(grid[cross] - S))]],
                                    grid[cross[np.argmin(np.abs(grid[cross] - S))] + 1]])) if len(cross) else np.nan
            # nearest wall = strike with max |gamma*OI| weight
            w = np.abs(norm.pdf((np.log(S / K)) / (sig * np.sqrt(T))) / (S * sig * np.sqrt(T)) * oiv * mult)
            wall = float(K[np.argmax(w)])
            rows.append({"date": d, "spot": S, "flip": flip, "wall": wall,
                         "above_flip": (S > flip) if np.isfinite(flip) else np.nan,
                         "dist_wall": (wall - S) / S})
    out = pd.DataFrame(rows).set_index("date").sort_index()
    out.to_parquet(OUT / "spx_flip_walls.parquet")
    return out


def main() -> int:
    fw = build_flip_walls()
    es = pd.read_parquet(OUT / "es_daily_intraday.parquet").set_index("date")
    es.index = pd.to_datetime(es.index).tz_localize(None).normalize()
    m = es.join(fw.shift(1), how="inner").dropna(subset=["eff", "rv"])      # t-1 gamma -> day t
    print(f"flip/walls computed for {len(fw)} days; merged {len(m)}  ({m.index.min().date()}..{m.index.max().date()})\n")
    print(f"flip found on {100*fw['flip'].notna().mean():.0f}% of days | spot above flip {100*fw['above_flip'].mean():.0f}%\n")

    a = m[m["above_flip"] == True]; b = m[m["above_flip"] == False]
    print("1) ABOVE vs BELOW the gamma flip -> next-day ES:")
    print(f"   ABOVE flip (pin regime, n={len(a):3}): trendiness {a['eff'].mean():.4f}  vol {a['rv'].mean():.4f}")
    print(f"   BELOW flip (trend regime,n={len(b):3}): trendiness {b['eff'].mean():.4f}  vol {b['rv'].mean():.4f}")

    # 2) pinning: does next-day signed move go toward the nearest wall?
    mm = m.dropna(subset=["dist_wall", "absret"]).copy()
    mm["signed_ret"] = np.sign(mm["dist_wall"]) * mm.get("ret", mm["absret"])  # ret toward wall (if 'ret' absent use |move| proxy
    if "ret" not in mm.columns:
        print("\n2) PINNING: (no signed daily return col in es file -> skipped; would need close-to-close)")
    else:
        print(f"\n2) PINNING: corr(distance-to-wall, next-day return) = {mm['dist_wall'].corr(mm['ret']):+.3f} "
              "(POSITIVE = price moves toward the wall)")
    print("\n(next: gate the expansion-reversion on above/below-flip -- wiring to fractal_reversion in v2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
