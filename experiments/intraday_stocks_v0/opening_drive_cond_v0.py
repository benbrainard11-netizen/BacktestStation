"""intraday_stocks_v0 — CONDITIONING pass. The unconditional drive->rest-of-day was weak fade (IC -0.026,
tiny). Now split it: does the fade/continuation sharpen by HORIZON, LIQUIDITY tier, or intraday VOLATILITY
(the inefficient-tail proxy)? Looking for a subgroup with a tradeable-magnitude separation.

Per (ticker, day): drive=p1000/o930-1; outcomes at +1h / +2h / close; range30=(hi-lo)/o930 over 09:30-10:00.
Dev slice only (recent stays sealed). Run: python opening_drive_cond_v0.py [START] [END]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data_io import load_polygon_flat  # noqa: E402

START = int(sys.argv[1]) if len(sys.argv) > 1 else 20240101
END = int(sys.argv[2]) if len(sys.argv) > 2 else 20240329
DVOL_FLOOR, PX_FLOOR = 3e6, 3.0
O, MID, H11, H12, CL = 570, 600, 660, 720, 959   # 09:30, 10:00, 11:00, 12:00, 15:59 ET


def bar_open(rth, minute):
    return rth.loc[rth["mod"] == minute].drop_duplicates("ticker").set_index("ticker")["open"]


def day_rows(yyyymmdd):
    try:
        df = load_polygon_flat("minute", yyyymmdd)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    et = pd.to_datetime(df["window_start"], utc=True).dt.tz_convert("America/New_York")
    df = df.assign(mod=et.dt.hour * 60 + et.dt.minute)
    rth = df[(df["mod"] >= O) & (df["mod"] <= CL)].sort_values(["ticker", "mod"])
    if rth.empty:
        return pd.DataFrame()
    pre = rth[rth["mod"] < MID]
    cols = {
        "o930": bar_open(rth, O), "p1000": bar_open(rth, MID),
        "p1100": bar_open(rth, H11), "p1200": bar_open(rth, H12),
        "pclose": rth.drop_duplicates("ticker", keep="last").set_index("ticker")["close"],
        "dvol30": (pre["volume"] * pre["close"]).groupby(pre["ticker"]).sum(),
        "hi30": pre.groupby("ticker")["high"].max(), "lo30": pre.groupby("ticker")["low"].min(),
    }
    out = pd.DataFrame(cols).reset_index().rename(columns={"index": "ticker"})
    out = out[(out["dvol30"] >= DVOL_FLOOR) & (out["o930"] >= PX_FLOOR)].dropna(subset=["o930", "p1000", "pclose"])
    out = out[out["o930"] > 0]
    out["date"] = yyyymmdd
    out["drive"] = out["p1000"] / out["o930"] - 1.0
    out["range30"] = (out["hi30"] - out["lo30"]) / out["o930"]
    out["r_1h"] = out["p1100"] / out["p1000"] - 1.0
    out["r_2h"] = out["p1200"] / out["p1000"] - 1.0
    out["r_close"] = out["pclose"] / out["p1000"] - 1.0
    return out


def ic(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 200:
        return (np.nan, m.sum())
    return (stats.spearmanr(x[m], y[m])[0], int(m.sum()))


def main():
    days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(str(START), str(END))]
    parts = [r for d in days if not (r := day_rows(d)).empty]
    big = pd.concat(parts, ignore_index=True)
    print(f"pooled name-days: {len(big):,}  ({big['date'].nunique()} days)\n")

    dr = big["drive"].to_numpy()
    print("=== HORIZON: IC(drive -> outcome) at each horizon (does shorter hold sharpen it?) ===")
    for h, lab in (("r_1h", "+1h (to 11:00)"), ("r_2h", "+2h (to 12:00)"), ("r_close", "to close")):
        r, n = ic(dr, big[h].to_numpy())
        print(f"  {lab:14} IC={r:+.4f}  n={n:,}")

    print("\n=== LIQUIDITY tier (dvol30 terciles): IC(drive -> r_close) — is the tail different? ===")
    big["liq"] = pd.qcut(big["dvol30"], 3, labels=["small $3-?", "mid", "large"])
    for t, g in big.groupby("liq", observed=True):
        r, n = ic(g["drive"].to_numpy(), g["r_close"].to_numpy())
        print(f"  {str(t):12} IC={r:+.4f}  n={n:,}  (median $vol {g['dvol30'].median()/1e6:.0f}M)")

    print("\n=== VOLATILITY tier (range30 terciles): IC(drive -> r_close) — the inefficient-tail hypothesis ===")
    big["volt"] = pd.qcut(big["range30"], 3, labels=["calm", "mid", "wild"])
    for t, g in big.groupby("volt", observed=True):
        r, n = ic(g["drive"].to_numpy(), g["r_close"].to_numpy())
        print(f"  {str(t):6} IC={r:+.4f}  n={n:,}  (median range {g['range30'].median():.1%})")

    print("\n=== WILD x close: decile of drive -> mean r_close (is the FADE now tradeable-sized?) ===")
    w = big[big["volt"] == "wild"].copy()
    w["dec"] = pd.qcut(w["drive"], 10, labels=False, duplicates="drop")
    tab = w.groupby("dec").agg(drive=("drive", "mean"), r=("r_close", "mean"), n=("r_close", "size"))
    for d, rr in tab.iterrows():
        print(f"  D{int(d):>2} drive={rr['drive']:+.2%} -> r_close {rr['r']:+.3%}  n={int(rr['n'])}")
    spread = tab["r"].iloc[0] - tab["r"].iloc[-1]
    print(f"  D0-vs-D9 spread = {spread:+.3%}  (vs ~0.07% unconditional — need it well above ~0.1% round-trip cost)")
    print("\nEXPLORATORY dev slice. Looking for a cut where the separation clears costs.")


if __name__ == "__main__":
    main()
