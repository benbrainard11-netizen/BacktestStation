"""FREE intraday-gamma test: does price PIN to the gamma walls? (the core 0DTE mechanism)

No new data -- uses the daily chains we own + ES daily/intraday we already have. For each day:
  - nearest GAMMA WALL = strike with the most gamma*OI near spot (the magnet)
  - gamma SIGN at spot (positive = dealers suppress -> should PIN; negative = amplify -> should repel)
Test: does the CLOSE land closer to the wall than the OPEN (pinning), and is that pull STRONGER on
positive-gamma days? Also: does ES spend the day drawn toward the wall (close-to-wall vs day's range)?
Both directions / honest. n~245 (2025). If pinning shows here -> the $56/yr minute data (time-based
0DTE cycles) is worth it; if null -> save it.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/intraday_pin.py
"""
from __future__ import annotations

from pathlib import Path

import databento as db
import numpy as np
import pandas as pd
from scipy.stats import norm

RAW = Path("D:/data/raw/opra")
OUT = Path("experiments/options_signals_v0/out")
MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]


def build_walls() -> pd.DataFrame:
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
            j = j[(j["T"] > 1 / 365) & (np.abs(j["K"] / S - 1) < 0.15)]
            if len(j) < 20:
                continue
            K, T, oiv = j["K"].to_numpy(), j["T"].to_numpy(), j["oi"].to_numpy()
            sq = sig * np.sqrt(T)
            gam = norm.pdf(np.log(S / K) / sq) / (S * sq)
            w = gam * oiv * j["mult"].to_numpy()
            sign = np.where(j["cls"].to_numpy() == "C", 1.0, -1.0)
            gex_sign = float(np.sign(np.sum(sign * w * S ** 2 * 0.01)))
            # nearest dominant wall (weight by total gamma*OI, take the closest of the top-5 magnets)
            top = np.argsort(w)[-5:]
            wall = float(K[top][np.argmin(np.abs(K[top] - S))])
            rows.append({"date": d, "spot": S, "wall": wall, "pos_gamma": gex_sign > 0})
    return pd.DataFrame(rows).set_index("date").sort_index()


def main() -> int:
    wl = build_walls()
    es = pd.read_parquet(Path(__file__).resolve().parents[1] / "tgif_v0" / "out" / "ES_dailyET.parquet")
    es.index = pd.to_datetime(es.index).tz_localize(None).normalize()
    m = es.join(wl, how="inner").dropna(subset=["wall"])
    # pinning: did close move toward the wall vs the open? (positive = pulled to wall), in % of spot
    m["pin"] = (np.abs(m["open"] - m["wall"]) - np.abs(m["close"] - m["wall"])) / m["spot"]
    # close proximity to wall vs the day's range (0=at wall, 1=a full range away)
    m["close_to_wall"] = np.abs(m["close"] - m["wall"]) / (m["high"] - m["low"]).replace(0, np.nan)
    print(f"days {len(m)}  ({m.index.min().date()}..{m.index.max().date()})")
    print(f"avg distance spot->nearest wall: {100*np.abs(m['spot']-m['wall']).div(m['spot']).mean():.2f}% of spot\n")
    print("PINNING: did CLOSE move toward the gamma wall vs OPEN? (pin>0 = pulled to wall)")
    for lbl, sub in [("positive-gamma (should PIN)", m[m["pos_gamma"]]),
                     ("negative-gamma (should REPEL)", m[~m["pos_gamma"]]),
                     ("ALL days", m)]:
        p = sub["pin"].dropna()
        frac = 100 * (p > 0).mean()
        print(f"  {lbl:30} mean pin {p.mean()*100:+.3f}% of spot | toward-wall {frac:.0f}% of days | n={len(p)}")
    print(f"\nIf positive-gamma days pull to the wall (+pin, >55% toward) and negative don't -> intraday "
          "gamma is real for ES -> the $56/yr minute data is worth it. Flat/equal -> save it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
