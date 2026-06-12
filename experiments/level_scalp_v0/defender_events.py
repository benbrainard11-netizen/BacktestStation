"""Defended-level event family — native icebergs detected with rule-A4 discipline.

A "defender" = one order_id at one (price, side) that keeps reloading: an institution
defending a precise tick. The event is emitted at ts_define = the FIRST moment the
running evidence crosses every threshold — i.e. the moment a real-time watcher would
have flagged it. Everything before ts_define is defining evidence (never counted as
touches/outcomes); everything after is tradeable reaction (rule A4: disjoint windows).

Institutional-class thresholds (probe-calibrated 2026-06-12; the loose 3-fill/2x
signature finds ~1,200/day of noise — this class finds the ~5-10/day real players):
  cumulative filled >= MIN_FILLED[sym], n_fills >= 20, defense alive >= 60s,
  cumulative filled >= 3x the max displayed size seen so far.

valid_to = the order's terminal event (cancel or final disappearance) — also
real-time observable. end_reason recorded (cancelled / consumed-or-eod).
Final-total columns (filled_total_final) are POST-HOC descriptive only — never features.

Importable; no CLI. v1 = native icebergs only (id-persistent); synthetic/ATM
reposting patterns are a later refinement.
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

MIN_FILLED = {"ES.c.0": 100, "NQ.c.0": 50, "YM.c.0": 50, "RTY.c.0": 50}
MIN_FILLS = 20
MIN_LIFE_S = 60.0
RELOAD_X = 3.0


def define_ts_for_order(ev: pd.DataFrame, min_filled: float) -> pd.Timestamp | None:
    """First ts where the RUNNING evidence crosses all thresholds; None if never.

    `ev` = one order_id's events sorted by ts with columns ts/action/size.
    Running state only — a threshold crossed using any later information would be
    look-ahead in the level definition itself (the family's documented failure mode).
    """
    cum_filled = 0.0
    n_fills = 0
    disp_max = 0.0
    t_first_fill: pd.Timestamp | None = None
    for row in ev.itertuples(index=False):
        if row.action in ("A", "M"):
            disp_max = max(disp_max, float(row.size))
        elif row.action == "F":
            cum_filled += float(row.size)
            n_fills += 1
            if t_first_fill is None:
                t_first_fill = row.ts
            if (
                cum_filled >= min_filled
                and n_fills >= MIN_FILLS
                and disp_max > 0
                and cum_filled >= RELOAD_X * disp_max
                and (row.ts - t_first_fill).total_seconds() >= MIN_LIFE_S
            ):
                return row.ts
    return None


def detect_day(sym: str, day: dt.date) -> list[dict]:
    """Defender events for one (symbol, trading day)."""
    df = read_mbo_trading_day(
        symbol=sym,
        trading_day=day,
        columns=["ts_event", "action", "side", "price", "size", "order_id"],
    )
    df = df.assign(
        ts=pd.DatetimeIndex(pd.to_datetime(df["ts_event"], utc=True)).tz_localize(None)
    )
    f = df[(df["action"] == "F") & df["side"].isin(["B", "A"])]
    agg = f.groupby("order_id").agg(
        filled=("size", "sum"),
        n=("size", "count"),
        t0=("ts", "min"),
        t1=("ts", "max"),
    )
    life = (agg["t1"] - agg["t0"]).dt.total_seconds()
    cand = agg[
        (agg["filled"] >= MIN_FILLED[sym])
        & (agg["n"] >= MIN_FILLS)
        & (life >= MIN_LIFE_S)
    ]
    if cand.empty:
        return []
    sub = df[df["order_id"].isin(cand.index)].sort_values("ts")
    out: list[dict] = []
    for oid, ev in sub.groupby("order_id"):
        ts_def = define_ts_for_order(ev, MIN_FILLED[sym])
        if ts_def is None:
            continue
        fills = ev[ev["action"] == "F"]
        last = ev.iloc[-1]
        price = float(fills["price"].iloc[0])
        side = str(fills["side"].iloc[0])
        out.append(
            {
                "symbol": sym,
                "trading_day": day,
                "price": price,
                "side": side,
                "order_id": int(oid),
                "ts_define": ts_def,
                "valid_to": last["ts"],
                "end_reason": (
                    "cancelled" if last["action"] == "C" else "consumed_or_eod"
                ),
                # descriptive post-hoc columns (NEVER features):
                "filled_at_define": float(fills[fills["ts"] <= ts_def]["size"].sum()),
                "filled_total_final": float(fills["size"].sum()),
                "disp_max_final": float(
                    ev[ev["action"].isin(["A", "M"])]["size"].max()
                ),
                "life_s_final": float(
                    (fills["ts"].iloc[-1] - fills["ts"].iloc[0]).total_seconds()
                ),
            }
        )
    # dedup by defended (price, side): keep the earliest detection (rule 22 spirit)
    if out:
        d = pd.DataFrame(out).sort_values("ts_define")
        d = d.drop_duplicates(subset=["price", "side"], keep="first")
        return d.to_dict("records")
    return out
