"""intraday_stocks_v0 — EXPLORATORY first look: does the opening 30-min DRIVE predict the rest of the day?

On each day, for liquid movers (first-30-min $vol >= floor, price >= $3):
  drive   = price@10:00 / open@09:30 - 1     (the opening drive, known at 10:00)
  outcome = close@16:00 / price@10:00 - 1     (rest of day, what we'd trade)
Pooled rank-IC(drive, outcome): positive = CONTINUATION (ride it), negative = FADE (mean-revert).
Huge sample (thousands of name-days) -> finally enough power for an honest read. Dev slice only;
recent data stays sealed for a later holdout. Honest fills come later — this is just "is there signal?".

Run: backend\\.venv\\Scripts\\python.exe -u opening_drive_v0.py [START=20240101] [END=20240331]
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
END = int(sys.argv[2]) if len(sys.argv) > 2 else 20240331
DVOL_FLOOR = 3e6        # first-30-min dollar volume floor (liquid, tradeable movers)
PX_FLOOR = 3.0          # avoid sub-$3 junk
OPEN_MIN, MID_MIN, CLOSE_MIN = 570, 600, 959   # ET minute-of-day: 09:30, 10:00, 15:59


def day_rows(yyyymmdd: int) -> pd.DataFrame:
    try:
        df = load_polygon_flat("minute", yyyymmdd)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    et = pd.to_datetime(df["window_start"], utc=True).dt.tz_convert("America/New_York")
    df = df.assign(mod=et.dt.hour * 60 + et.dt.minute)
    rth = df[(df["mod"] >= OPEN_MIN) & (df["mod"] <= CLOSE_MIN)].sort_values(["ticker", "mod"])
    if rth.empty:
        return pd.DataFrame()
    # vectorized bar picks (no per-group apply)
    o930 = rth.loc[rth["mod"] == OPEN_MIN].drop_duplicates("ticker").set_index("ticker")["open"]
    p1000 = rth.loc[rth["mod"] == MID_MIN].drop_duplicates("ticker").set_index("ticker")["open"]
    pclose = rth.drop_duplicates("ticker", keep="last").set_index("ticker")["close"]
    pre = rth[rth["mod"] < MID_MIN]
    dvol30 = (pre["volume"] * pre["close"]).groupby(pre["ticker"]).sum()
    out = pd.DataFrame({"o930": o930, "p1000": p1000, "pclose": pclose, "dvol30": dvol30}).reset_index()
    out["date"] = yyyymmdd
    out = out[(out["dvol30"] >= DVOL_FLOOR) & (out["o930"] >= PX_FLOOR)]
    out = out.dropna(subset=["o930", "p1000", "pclose"])
    out = out[(out["o930"] > 0) & (out["p1000"] > 0)]
    out["drive"] = out["p1000"] / out["o930"] - 1.0
    out["outcome"] = out["pclose"] / out["p1000"] - 1.0
    return out[["date", "ticker", "drive", "outcome", "dvol30"]]


def main() -> int:
    days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(str(START), str(END))]
    parts = []
    for i, d in enumerate(days):
        r = day_rows(d)
        if not r.empty:
            parts.append(r)
        if (i + 1) % 20 == 0:
            print(f"  ..{i+1}/{len(days)} days, {sum(len(p) for p in parts):,} name-days", flush=True)
    if not parts:
        print("no data in range"); return 1
    big = pd.concat(parts, ignore_index=True)
    print(f"\npooled name-days: {len(big):,}  ({big['date'].nunique()} days, {big['ticker'].nunique()} names)")
    d, o = big["drive"].to_numpy(), big["outcome"].to_numpy()
    m = np.isfinite(d) & np.isfinite(o)
    rho, p = stats.spearmanr(d[m], o[m])
    print(f"\nrank-IC(drive -> rest-of-day) = {rho:+.4f}  (p={p:.1e}, n={m.sum():,})")
    print("  >0 = CONTINUATION (drive keeps going), <0 = FADE (mean-reverts)\n")
    big["dec"] = pd.qcut(big["drive"], 10, labels=False, duplicates="drop")
    print("by opening-drive decile:  mean rest-of-day outcome (the tradeable move)")
    tab = big.groupby("dec").agg(drive=("drive", "mean"), outcome=("outcome", "mean"),
                                 win=("outcome", lambda x: (x > 0).mean()), n=("outcome", "size"))
    for dec, r in tab.iterrows():
        print(f"  D{int(dec):>2}  drive={r['drive']:+.2%}  -> rest-of-day {r['outcome']:+.3%}  win={r['win']:.0%}  n={int(r['n'])}")
    print("\nEXPLORATORY (dev slice, no fills/holdout yet). Monotonic decile pattern = the hallmark of a real effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
