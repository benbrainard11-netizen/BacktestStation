"""Autonomous PAPER trading bot for the ML breakout strategy. One daily cycle (run pre-open via the
scheduler):

  1. refresh daily data (pull yesterday's Polygon grouped-daily, append)
  2. rebuild setups (subprocess build_setups.py)
  3. reconcile open positions vs IBKR
  4. EXIT MANAGER: ratchet each open position's chandelier stop (run_high - 3*ATR), close max-hold (40d)
  5. ENTRIES: score today's setups, place stop-buy brackets for the top pred>0 up to the free slots
  6. persist state (positions.json) + log

PAPER ONLY. Default is DRY-RUN (no IBKR -- prints what it would do, testable now). --live connects to
IBKR PAPER (port 7497 TWS / 4002 Gateway) via ib_async. The exit manager is the piece the backtest
needs: it trails the stop so winners run (the edge). Run via the daily scheduler (see SCHEDULE.md).
Run with backend\\.venv\\Scripts\\python.exe -u auto_paper.py [--live] [--equity 10000]
"""

from __future__ import annotations

import argparse
import datetime as _dt  # noqa: F401  (only for typing; no Date.now in logic paths)
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
POLY = Path(r"D:\data\processed\stocks\polygon")
STATE = OUT / "paper_state.json"
LOG = OUT / "auto_paper.log"
sys.path.insert(0, r"C:\Users\benbr\BacktestStation")
from data_io import load_polygon_daily  # noqa: E402
from paper_harness import build_takelist  # noqa: E402

CHAND = 3.0
MAX_HOLD = 40
PORT_TWS = 7497


def log(msg: str):
    line = f"{msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_state(equity_default: float) -> dict:
    if STATE.exists():
        return json.load(open(STATE))
    return {"equity": equity_default, "positions": []}


def save_state(s: dict):
    json.dump(s, open(STATE, "w"), indent=2)


def refresh_daily():
    """Append any missing recent trading days to daily_<yr>.parquet from Polygon grouped-daily."""
    key = os.environ.get("POLYGON_API_KEY")
    if not key:
        log("  [refresh] no POLYGON_API_KEY -> skipping data refresh (using existing daily)")
        return
    import requests

    dl = load_polygon_daily(year=2026)
    last = int(dl["date"].max())
    today = int(pd.Timestamp.utcnow().strftime("%Y%m%d"))  # harness clock; no Date.now in trade logic
    days = [
        d
        for d in pd.bdate_range(
            pd.Timestamp(str(last)) + pd.Timedelta(days=1), pd.Timestamp(str(today)) - pd.Timedelta(days=1)
        )
    ]
    if not days:
        log(f"  [refresh] daily already current through {last}")
        return
    rows = []
    for d in days:
        ds = d.strftime("%Y-%m-%d")
        r = requests.get(
            f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{ds}",
            params={"adjusted": "true", "apiKey": key},
            timeout=30,
        ).json()
        for it in r.get("results", []) or []:
            rows.append(
                (
                    it["T"],
                    int(d.strftime("%Y%m%d")),
                    it.get("o"),
                    it.get("h"),
                    it.get("l"),
                    it.get("c"),
                    it.get("v"),
                )
            )
    if rows:
        new = pd.DataFrame(rows, columns=["ticker", "date", "open", "high", "low", "close", "volume"])
        f = POLY / "daily_2026.parquet"
        pd.concat([pd.read_parquet(f), new], ignore_index=True).drop_duplicates(
            ["ticker", "date"]
        ).to_parquet(f)
        log(f"  [refresh] appended {new['date'].nunique()} day(s), {len(new):,} rows")


def manage_exits(state: dict, ib, dry: bool):
    """Chandelier-trail each open position; close max-hold. Updates the IBKR stop orders (live)."""
    if not state["positions"]:
        log("  [exits] no open positions")
        return
    cal = sorted(pd.unique(load_polygon_daily("SPY")["date"]))
    cpos = {d: i for i, d in enumerate(cal)}
    last_idx = len(cal) - 1
    for p in state["positions"]:
        d = load_polygon_daily(p["ticker"]).sort_values("date")
        since = d[d["date"] >= p["entry_date"]]
        if not len(since):
            continue
        run_high = max(p["run_high"], float(since["high"].max()))
        new_stop = max(p["stop"], run_high - CHAND * p["entry_atr"])
        held = last_idx - cpos.get(p["entry_date"], last_idx)
        if held >= MAX_HOLD:
            log(f"  [exits] {p['ticker']}: max-hold {held}d -> CLOSE at market")
            if not dry and ib is not None:
                _ib_close(ib, p)
            p["status"] = "to_close"
        elif new_stop > p["stop"]:
            log(
                f"  [exits] {p['ticker']}: trail stop {p['stop']:.2f} -> {new_stop:.2f} (run_high {run_high:.2f})"
            )
            p["stop"], p["run_high"] = new_stop, run_high
            if not dry and ib is not None:
                _ib_modify_stop(ib, p)
        else:
            p["run_high"] = run_high
    state["positions"] = [p for p in state["positions"] if p.get("status") != "to_close"]


def place_entries(state: dict, tl: pd.DataFrame, ib, dry: bool):
    held = {p["ticker"] for p in state["positions"]}
    free = 5 - len(state["positions"])
    placed = 0
    for _, r in tl.iterrows():
        if free <= 0:
            break
        if r["ticker"] in held:
            continue
        log(
            f"  [entry] {r['ticker']}: BUY-stop {r['entry']} x{r['shares']}  stop {r['stop']}  (pred {r['pred']})"
        )
        if not dry and ib is not None:
            _ib_bracket(ib, r)
        # entry_atr implied from entry-stop distance (1 ATR)
        state["positions"].append(
            dict(
                ticker=r["ticker"],
                entry_date=int(tl.attrs["asof"]),
                entry_price=float(r["entry"]),
                entry_atr=float(r["entry"] - r["stop"]),
                run_high=float(r["entry"]),
                stop=float(r["stop"]),
                shares=int(r["shares"]),
                status="pending",
            )
        )
        free -= 1
        placed += 1
    log(f"  [entry] placed {placed} new bracket(s); {len(state['positions'])} total positions")


# ---- IBKR (ib_async) — only called in --live ----
def _connect(port):
    from ib_async import IB

    ib = IB()
    ib.connect("127.0.0.1", port, clientId=17)
    return ib


def _ib_bracket(ib, r):
    from ib_async import Order, Stock

    c = Stock(r["ticker"], "SMART", "USD")
    ib.qualifyContracts(c)
    parent = Order(
        action="BUY",
        orderType="STP",
        auxPrice=float(r["entry"]),
        totalQuantity=int(r["shares"]),
        transmit=False,
    )
    t = ib.placeOrder(c, parent)
    child = Order(
        action="SELL",
        orderType="STP",
        auxPrice=float(r["stop"]),
        totalQuantity=int(r["shares"]),
        parentId=t.order.orderId,
        transmit=True,
    )
    ib.placeOrder(c, child)


def _ib_modify_stop(ib, p):
    from ib_async import Order, Stock

    c = Stock(p["ticker"], "SMART", "USD")
    ib.qualifyContracts(c)
    for tr in ib.openTrades():
        if tr.contract.symbol == p["ticker"] and tr.order.action == "SELL":
            tr.order.auxPrice = float(p["stop"])
            ib.placeOrder(c, tr.order)
            return
    ib.placeOrder(
        c,
        Order(
            action="SELL",
            orderType="STP",
            auxPrice=float(p["stop"]),
            totalQuantity=int(p["shares"]),
            transmit=True,
        ),
    )


def _ib_close(ib, p):
    from ib_async import MarketOrder, Stock

    c = Stock(p["ticker"], "SMART", "USD")
    ib.qualifyContracts(c)
    ib.placeOrder(c, MarketOrder("SELL", int(p["shares"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="connect to IBKR PAPER (else dry-run)")
    ap.add_argument("--equity", type=float, default=10000.0)
    ap.add_argument("--no-refresh", action="store_true")
    a = ap.parse_args()
    dry = not a.live
    log(f"\n===== auto_paper cycle ({'LIVE-PAPER' if a.live else 'DRY-RUN'}) =====")
    try:
        if not a.no_refresh:
            refresh_daily()
            log("  [build] rebuilding setups...")
            subprocess.run([sys.executable, str(HERE / "build_setups.py")], check=True, capture_output=True)
        state = load_state(a.equity)
        ib = _connect(PORT_TWS) if a.live else None
        if ib is not None:
            state["equity"] = float(
                [v.value for v in ib.accountValues() if v.tag == "NetLiquidation" and v.currency == "USD"][0]
            )
            log(f"  [ibkr] connected; equity ${state['equity']:,.0f}")
        manage_exits(state, ib, dry)
        asof = int(pd.read_parquet(OUT / "setups.parquet").query("is_breakout==1")["date"].max())
        tl = build_takelist(asof, state["equity"])
        if tl is not None and len(tl):
            tl.attrs["asof"] = asof
            place_entries(state, tl, ib, dry)
        else:
            log("  [entry] no qualifying setups today")
        save_state(state)
        if ib is not None:
            ib.sleep(1)
            ib.disconnect()
        log("===== cycle complete =====")
    except Exception as e:  # noqa: BLE001
        log(f"  [ERROR] cycle failed: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
