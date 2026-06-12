"""Feasibility probe — detectable "defender" events in CME MBO (counts only, rule C21).

Two signatures of a smart-money player defending one precise price:
  NATIVE ICEBERG: one order_id whose cumulative filled volume exceeds its displayed
  size by 2x+ across 3+ fills (CME native icebergs keep their id while reloading).
  ABSORPTION LEVEL: one (price, side) absorbing an outsized volume of aggressor fills
  within a bounded time window (any mix of ids — catches synthetic/ATM icebergs too).

NO reaction outcomes here — this is the power table for the defended-level family
(PLAN rule: counts before outcomes). ts_define discipline (rule A4) applies at the
event-emission stage later; this probe just answers "do these exist, how many per day,
and how big".

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/iceberg_scan.py [SYM] [N_DAYS]
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import REPO  # noqa: E402

sys.path.insert(0, str(REPO / "backend"))
from app.data.reader import read_mbo_trading_day  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ICE_MIN_FILLS = 3
ICE_RELOAD_X = 2.0  # total filled >= 2x max displayed
ABS_WINDOW = pd.Timedelta("10min")


def scan_day(sym: str, day: dt.date) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = read_mbo_trading_day(
        symbol=sym,
        trading_day=day,
        columns=["ts_event", "action", "side", "price", "size", "order_id"],
    )
    ts = pd.DatetimeIndex(pd.to_datetime(df["ts_event"], utc=True)).tz_localize(None)
    df = df.assign(ts=ts)

    # --- native icebergs: per order_id, filled total vs max displayed ---
    disp = (
        df[df["action"].isin(["A", "M"])]
        .groupby("order_id")["size"]
        .max()
        .rename("displayed")
    )
    f = df[df["action"] == "F"]
    per_oid = (
        f.groupby("order_id")
        .agg(
            filled=("size", "sum"),
            n_fills=("size", "count"),
            price=("price", "first"),
            side=("side", "first"),
            t_first=("ts", "min"),
            t_last=("ts", "max"),
        )
        .join(disp, how="inner")
    )
    ice = per_oid[
        (per_oid["n_fills"] >= ICE_MIN_FILLS)
        & (per_oid["filled"] >= ICE_RELOAD_X * per_oid["displayed"])
        & (per_oid["displayed"] > 0)
    ].reset_index()

    # --- absorption levels: (price, side) fill volume inside a bounded window ---
    g = (
        f.groupby([f["price"], f["side"]])
        .agg(
            filled=("size", "sum"),
            n_fills=("size", "count"),
            t_first=("ts", "min"),
            t_last=("ts", "max"),
            n_oids=("order_id", "nunique"),
        )
        .reset_index()
    )
    g["span"] = g["t_last"] - g["t_first"]
    big = g[g["span"] <= ABS_WINDOW].nlargest(10, "filled")
    return ice, big


def main() -> int:
    sym = sys.argv[1] if len(sys.argv) > 1 else "ES.c.0"
    n_days = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    # probe inside the CONFIRMATION window (already opened for this module)
    days = pd.bdate_range("2026-02-02", periods=n_days).date
    all_ice = []
    for d in days:
        try:
            ice, big = scan_day(sym, d)
        except Exception as e:  # noqa: BLE001
            print(f"{d}: ERROR {type(e).__name__}: {e}")
            continue
        all_ice.append(ice.assign(day=d))
        print(f"\n{sym} {d}: native icebergs={len(ice)}")
        if len(ice):
            q = ice["filled"].quantile([0.5, 0.9]).astype(int).tolist()
            life = (ice["t_last"] - ice["t_first"]).dt.total_seconds()
            print(
                f"  filled med/p90={q} contracts; reload x med="
                f"{(ice['filled'] / ice['displayed']).median():.1f}; "
                f"life med={life.median():.0f}s; "
                f"sides B/A={int((ice['side'] == 'B').sum())}/{int((ice['side'] == 'A').sum())}"
            )
            top = ice.nlargest(3, "filled")[
                ["price", "side", "filled", "displayed", "n_fills"]
            ]
            print(top.to_string(index=False))
        print(
            f"  top absorption (10min window): "
            f"{big[['price', 'side', 'filled', 'n_oids']].head(3).to_string(index=False)}"
        )
    if all_ice:
        a = pd.concat(all_ice)
        print(
            f"\n=== {sym}: {len(a)} native icebergs over {len(days)} days "
            f"({len(a) / max(len(days), 1):.0f}/day) ==="
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
