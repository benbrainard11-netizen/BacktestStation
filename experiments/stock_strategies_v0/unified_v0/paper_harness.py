"""Paper-trading harness for the ML breakout strategy. Scores the day's breakout setups with the
FROZEN model, selects the top pred>0 up to max_positions, sizes them pred-scaled (fractional-Kelly),
and prints/saves the take-list (entry stop-buy level, ATR stop, shares, risk$). With --execute it
places IBKR bracket orders (stop-buy entry + stop-loss) on the PAPER account via ib_async.

LIVE DAILY FLOW:
  1. pull fresh Polygon grouped-daily for today  ->  append to D:\\data\\...\\polygon\\daily_<yr>.parquet
  2. re-run build_setups.py  (recomputes features incl today)   3. (monthly) re-run train_frozen_model.py
  4. python paper_harness.py [--asof YYYYMMDD] [--equity 10000] [--execute]
  5. before the OPEN, the take-list's stop-buys arm; they fill intraday if price breaks the 20d-high.

This scaffold scores off setups.parquet (so it's testable now on the latest date). Live, step 2
refreshes that file. IBKR: run TWS/Gateway PAPER (port 7497 TWS / 4002 Gateway), `pip install ib_async`.
Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\benbr\BacktestStation")
from data_io import load_polygon_daily  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
POLY = Path(r"D:\data\processed\stocks\polygon")
MAX_LEV = 2.0  # Reg-T overnight cap


def build_takelist(asof: int, equity: float):
    import lightgbm as lgb

    meta = json.load(open(OUT / "frozen_meta.json"))
    feats, sectors, sz = meta["features"], meta["sectors"], meta["sizing"]
    booster = lgb.Booster(model_file=str(OUT / "frozen_model.txt"))

    S = pd.read_parquet(OUT / "setups.parquet")
    S = S[(S["is_breakout"] == 1) & (S["date"] == asof)].copy()
    if not len(S):
        print(f"no breakout setups on {asof}")
        return None
    sec = pd.read_parquet(POLY / "_xregime_with_sector.parquet")[["tkr", "date", "sector"]]
    S = S.merge(sec, left_on=["ticker", "date"], right_on=["tkr", "date"], how="left")
    S["sector"] = pd.Categorical(S["sector"].fillna("Unknown"), categories=sectors)
    S = S.dropna(subset=meta["features"][:-1])  # numeric features present
    S["pred"] = booster.predict(S[feats])
    sel = S[S["pred"] > 0].sort_values("pred", ascending=False).head(sz["max_positions"]).copy()
    if not len(sel):
        print(f"{asof}: setups present but none scored pred>0 -> no trades")
        return None

    # entry level (trailing 20d high) + ATR from the daily
    dl = load_polygon_daily().sort_values(["ticker", "date"])
    dl = dl[dl["ticker"].isin(sel["ticker"])]
    dl["hi20"] = dl.groupby("ticker")["high"].transform(lambda s: s.rolling(20).max().shift(1))
    pc = dl.groupby("ticker")["close"].shift(1)
    tr = np.maximum(dl["high"] - dl["low"], np.maximum((dl["high"] - pc).abs(), (dl["low"] - pc).abs()))
    dl["atr14"] = tr.groupby(dl["ticker"]).transform(lambda s: s.rolling(14).mean())
    day = dl[dl["date"] == asof].set_index("ticker")
    sel = sel.join(day[["hi20", "atr14", "close"]], on="ticker")

    med_pred = sel["pred"].median()
    rows = []
    for _, r in sel.iterrows():
        if pd.isna(r["hi20"]) or pd.isna(r["atr14"]) or r["atr14"] <= 0:
            continue
        entry = r["hi20"] * (1 + sz["buf_entry"])
        stop = entry - sz["k_atr"] * r["atr14"]
        risk_ps = entry - stop
        mult = float(np.clip(r["pred"] / med_pred, 0.5, sz["pred_mult_cap"]))
        risk_d = sz["base_risk"] * mult * equity
        shares = risk_d / risk_ps
        dvol = np.exp(r["log_dvol"])
        shares = min(shares, sz["adv_frac"] * dvol / entry, (equity * MAX_LEV / sz["max_positions"]) / entry)
        shares = int(shares)
        if shares < 1:
            continue
        rows.append(
            dict(
                ticker=r["ticker"],
                sector=str(r["sector"]),
                pred=round(r["pred"], 3),
                entry=round(entry, 2),
                stop=round(stop, 2),
                shares=shares,
                risk=round(shares * risk_ps),
                position=round(shares * entry),
                pct_equity=round(100 * shares * entry / equity, 1),
            )
        )
    tl = pd.DataFrame(rows)
    return tl


def execute_ibkr(tl: pd.DataFrame, port: int = 7497):
    from ib_async import IB, Order, Stock  # noqa: F401

    ib = IB()
    ib.connect("127.0.0.1", port, clientId=17)
    for _, r in tl.iterrows():
        c = Stock(r["ticker"], "SMART", "USD")
        ib.qualifyContracts(c)
        parent = Order(
            action="BUY", orderType="STP", auxPrice=r["entry"], totalQuantity=r["shares"], transmit=False
        )
        child = Order(
            action="SELL",
            orderType="STP",
            auxPrice=r["stop"],
            totalQuantity=r["shares"],
            parentId=None,
            transmit=True,
        )
        t = ib.placeOrder(c, parent)
        child.parentId = t.order.orderId
        ib.placeOrder(c, child)
        print(f"  armed {r['ticker']}: BUY-stop {r['entry']} x{r['shares']}, stop {r['stop']}")
    ib.sleep(1)
    ib.disconnect()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", type=int, default=0)
    ap.add_argument("--equity", type=float, default=10000.0)
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    asof = a.asof or int(pd.read_parquet(OUT / "setups.parquet").query("is_breakout==1")["date"].max())
    tl = build_takelist(asof, a.equity)
    if tl is None or not len(tl):
        return
    print(f"\n=== TAKE-LIST {asof}  (${a.equity:,.0f} account, max {len(tl)} positions) ===")
    print(tl.to_string(index=False))
    print(
        f"\n  total deployed ${tl['position'].sum():,.0f} ({tl['position'].sum()/a.equity:.1f}x)  "
        f"total risk ${tl['risk'].sum():,.0f} ({100*tl['risk'].sum()/a.equity:.1f}% heat)"
    )
    tl.to_csv(OUT / f"takelist_{asof}.csv", index=False)
    print(f"  saved -> takelist_{asof}.csv")
    if a.execute:
        print("\nplacing IBKR paper bracket orders...")
        execute_ibkr(tl)


if __name__ == "__main__":
    main()
