"""UNBIASED modeled estimate of the convex-call expression — all 27 up-gap events, no option-coverage bias.

The real-fill backtest can only see ~half the events (monthlies-only drops the fat-tail winners). So model
the call instead: entry premium = Black-Scholes ATM/OTM (r=0) using each name's ACTUAL entry IV (from the
flow files' atm_iv), payoff = HOLD-TO-EXPIRY intrinsic on the ACTUAL realized stock move (Polygon daily).
Conservative (no time value recovered on early sale = max theta paid). Answers: does the fat tail pay for
the premium drag across the FULL event set? Clean enough to decide if the broad pull + Sharadar is worth it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from data_io import load_polygon_daily  # noqa: E402

NINE = ["SOFI", "AFRM", "RIOT", "ROKU", "DKNG", "PLTR", "MARA", "MSTR"]
FEAT = ROOT / "experiments" / "stock_strategies_v0" / "earnings_gap_v0" / "out" / "features.parquet"
FLOW = HERE / "out"
HOLD_TD = 20            # trading-day hold (the PEAD drift horizon)
DTE_CAL = 30           # option life modeled (calendar days) for the entry premium


def bs_call(S, K, T, iv):
    if T <= 0 or iv <= 0:
        return max(S - K, 0.0)
    d1 = (np.log(S / K) + 0.5 * iv * iv * T) / (iv * np.sqrt(T))
    d2 = d1 - iv * np.sqrt(T)
    return S * norm.cdf(d1) - K * norm.cdf(d2)


def main():
    ev = pd.read_parquet(FEAT)
    ev = ev[ev["ticker"].isin(NINE)].copy()
    ev["ei"] = pd.to_datetime(ev["entry_dt"]).dt.strftime("%Y%m%d").astype(int)
    ev = ev[(ev["ei"] >= 20230101) & (ev["ei"] <= 20260301)].reset_index(drop=True)

    rows = []
    for t in NINE:
        d = load_polygon_daily(t)
        if d is None or d.empty:
            continue
        d = d.sort_values("date").reset_index(drop=True)
        dates = d["date"].to_numpy()
        close = d["close"].to_numpy(float)
        fl = pd.read_parquet(FLOW / f"flow_{t.lower()}.parquet") if (FLOW / f"flow_{t.lower()}.parquet").exists() else None
        ivmap = dict(zip(fl["date"].astype(int), fl["atm_iv"])) if fl is not None else {}
        for _, e in ev[ev["ticker"] == t].iterrows():
            cand = np.where(dates >= e["ei"])[0]
            if not len(cand):
                continue
            i = int(cand[0])
            if i + HOLD_TD >= len(close):
                continue
            S0 = close[i]
            move = close[i + HOLD_TD] / S0 - 1.0                    # ACTUAL raw stock move over the hold
            iv = ivmap.get(int(dates[i]), np.nan)
            if not np.isfinite(iv) or iv <= 0:
                iv = np.nanmedian([v for v in ivmap.values()]) if ivmap else 0.7
            T = DTE_CAL / 365.0
            for tag, K in (("ATM", S0), ("OTM5", S0 * 1.05)):
                prem = bs_call(S0, K, T, iv)
                payoff = max(S0 * (1 + move) - K, 0.0)              # hold-to-expiry intrinsic
                rows.append({"ticker": t, "ei": int(e["ei"]), "tag": tag, "iv": iv,
                             "move": move, "call_ret": (payoff - prem) / prem if prem > 0 else np.nan})
    df = pd.DataFrame(rows)

    def stat(label, r):
        r = np.asarray(r, float); r = r[np.isfinite(r)]
        return (f"  {label:14} n={len(r):>2}  mean={r.mean():+.2f}  median={np.median(r):+.2f}  "
                f"win={np.mean(r>0):.0%}  max={r.max():+.1f}  >+2R={np.mean(r>2).mean():.0%}  total={r.sum():+.1f}")

    print(f"UNBIASED modeled convex-call estimate — ALL {df['ei'].nunique()} up-gap events, 8 names, "
          f"{HOLD_TD}td hold, hold-to-expiry, entry IV from flow files:\n")
    for tag in ("ATM", "OTM5"):
        sub = df[df["tag"] == tag]
        print(stat(f"{tag} call", sub["call_ret"]))
    print(f"\n  median entry IV used: {df['iv'].median():.0%}  | median stock move over hold: {df[df.tag=='ATM']['move'].median():+.1%}")
    print(f"  BS breakeven up-move for an ATM call (median IV, {DTE_CAL}d): "
          f"~{bs_call(1, 1, DTE_CAL/365, df['iv'].median())*100:.1f}% needed vs the +1.5%/20d avg drift")
    # show the fat-tail events
    big = df[(df.tag == 'ATM')].nlargest(5, 'call_ret')[['ticker', 'ei', 'move', 'iv', 'call_ret']]
    print("\n  top-5 ATM call outcomes (the fat tail that has to carry it):")
    print(big.to_string(index=False))


if __name__ == "__main__":
    main()
