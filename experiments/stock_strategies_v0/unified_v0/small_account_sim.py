"""Small-account portfolio sim: realistic retail version of the ML breakout strategy. Start $10k,
hold at most K concurrent positions, and each day take the HIGHEST ML-pred setups (pred>0) up to the
free slots -- i.e. when there are more signals than slots (almost always), the model picks the best.
Risk a fixed % of current equity per trade; exit on the backtest's realized hold. Walk-forward OOS
preds (each year scored by a prior-years-only model), R capped at +/-10 (honest tail). Runs the ACTUAL
2019-2026 sequence -> realized equity, CAGR, max drawdown (incl the 2022 stretch), by-year, win rate.
Implied leverage = K * risk / stop is reported (Reg-T cap = 2x). Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\benbr\BacktestStation")
from data_io import load_polygon_daily  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
START = 10_000.0


def main():
    ADV_FRAC = 0.01  # max position = 1% of the name's daily $ volume (capacity ceiling)
    SLIP = 0.25  # extra slippage/missed-fill haircut in R (live degradation on gapping top-picks)
    wf = pd.read_parquet(OUT / "wf_ml_predictions.parquet")[["tkr", "date", "R", "pred"]]
    full = pd.read_parquet(OUT / "intraday_entry_results_full.parquet")[["tkr", "date", "days"]]
    S = pd.read_parquet(OUT / "setups.parquet")
    S = S[S["is_breakout"] == 1][["ticker", "date", "atr_pct", "log_dvol"]]
    m = (
        wf.merge(full, on=["tkr", "date"], how="left")
        .merge(S, left_on=["tkr", "date"], right_on=["ticker", "date"], how="left")
        .dropna(subset=["days", "atr_pct", "log_dvol"])
    )
    m["dvol"] = np.exp(m["log_dvol"])
    cal = sorted(pd.unique(load_polygon_daily("SPY")["date"]))
    cpos = {d: i for i, d in enumerate(cal)}
    m["ei"] = m["date"].map(cpos)
    m = m.dropna(subset=["ei"])
    m["ei"] = m["ei"].astype(int)
    m["xi"] = (m["ei"] + m["days"].clip(lower=1).astype(int)).clip(upper=len(cal) - 1)
    m["Rc"] = m["R"].clip(-10, 10)
    stop_med = float(m["atr_pct"].median())

    byday = {}
    for ei, g in m.sort_values("pred", ascending=False).groupby("ei"):
        byday[ei] = list(zip(g["pred"], g["xi"], g["Rc"], g["atr_pct"], g["dvol"]))  # pred-desc

    def sim(K, risk):
        eq = START
        openp = []  # (xi, risk_dollars, R)
        eoy = {}
        curve = []
        peak = eq
        mdd = 0.0
        for idx in range(len(cal)):
            openp2 = []
            for xi, rd, r in openp:
                if xi <= idx:
                    eq += (r - SLIP) * rd  # realize, minus slippage haircut
                else:
                    openp2.append((xi, rd, r))
            openp = openp2
            peak = max(peak, eq)
            mdd = min(mdd, eq / peak - 1)
            free = K - len(openp)
            for pred, xi, r, atrp, dvol in byday.get(idx, []):
                if free <= 0 or pred <= 0:
                    break
                want_pos = (risk * eq) / atrp  # $ position to risk `risk` of equity at a 1-ATR stop
                pos = min(want_pos, ADV_FRAC * dvol)  # capacity cap: <=1% of daily volume
                rd = pos * atrp  # actual $ risked (capped)
                openp.append((int(xi), rd, r))
                free -= 1
            curve.append(eq)
            eoy[cal[idx] // 10000] = eq
        return curve, eq, mdd, eoy

    print(f"stop(1 ATR) median {stop_med*100:.1f}%  ->  position = risk/{stop_med*100:.1f}%\n")
    print(f"{'config':28s} {'final':>10} {'CAGR':>7} {'maxDD':>7} {'~lev':>6}")
    cfgs = [
        ("max3 / 0.5% risk", 3, 0.005),
        ("max5 / 1% risk", 5, 0.01),
        ("max5 / 2% risk", 5, 0.02),
        ("max8 / 1% risk", 8, 0.01),
    ]
    saved = None
    for name, K, rk in cfgs:
        curve, final, mdd, eoy = sim(K, rk)
        yrs = len(cal) / 252
        cagr = (final / START) ** (1 / yrs) - 1
        lev = K * rk / stop_med
        print(f"  {name:26s} ${final:>9,.0f} {cagr*100:+6.0f}% {mdd*100:6.0f}% {lev:5.1f}x")
        if name == "max5 / 1% risk":
            saved = (curve, eoy)
    curve, eoy = saved
    print("\n=== max5 / 1% risk — by year (realized $) ===")
    yk = sorted(eoy)
    prev = START
    for y in yk:
        print(f"  {y}: ${eoy[y]:>10,.0f}   ({(eoy[y]/prev-1)*100:+.0f}%)")
        prev = eoy[y]
    # downsampled curve for charting
    step = max(1, len(curve) // 120)
    import json

    json.dump(
        {
            "curve": [round(curve[i]) for i in range(0, len(curve), step)],
            "dates": [int(cal[i]) for i in range(0, len(curve), step)],
        },
        open(OUT / "small_account_curve.json", "w"),
    )
    print(f"\ncurve -> {OUT/'small_account_curve.json'}")


if __name__ == "__main__":
    main()
