"""Phase 1 Mode A — maker fills on the 4 surviving cells, CONFIRMATION window (2026 Q1).

Per phase1_manifest.json (pinned + committed BEFORE this runs; the script refuses to
start while committed_sha is null). Per placement this simulates the full order life:
proximity-triggered limit at the level (rule B14), three fill rules in a bracket
(behind-you headline / trade-through lower bound / visible-queue upper bound — B11),
exits per B15/B16 (stop-wins-ties, observed-quote stop fills + stress ladder), and the
adverse-selection split E[reaction | filled] vs E[reaction | touched] (fill-conditioned
PnL is the only number that counts).

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/mode_a_sim.py [CELL ...]
Artifacts: out/phase1_mode_a_{CELL}.parquet (+ manifest)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import (
    MODULE,
    OUT,
    REPO,
    TICK,
    guard_window,
    roll_poison_days,
    write_manifest,
)  # noqa: E402
from level_specs import build_instances  # noqa: E402
from outcomes import touch_outcomes  # noqa: E402

sys.path.insert(0, str(REPO / "backend"))
from app.data.reader import read_mbo_trading_day, read_mbp1_trading_day  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ET = ZoneInfo("America/New_York")
MANIFEST = json.loads((MODULE / "phase1_manifest.json").read_text(encoding="utf-8"))
STOP_STRESS = [1, 2, 4]


def load_mbp1_day(sym: str, d: dt.date):
    t = read_mbp1_trading_day(
        symbol=sym,
        trading_day=d,
        columns=[
            "ts_event",
            "action",
            "side",
            "price",
            "size",
            "bid_px",
            "ask_px",
            "bid_sz",
            "ask_sz",
        ],
    )
    if len(t) < 100:
        return None
    ts = pd.DatetimeIndex(pd.to_datetime(t["ts_event"], utc=True)).tz_localize(None)
    f = {
        c: np.asarray(t[c], dtype=float)
        for c in ["price", "size", "bid_px", "ask_px", "bid_sz", "ask_sz"]
    }
    ok = (
        np.isfinite(f["bid_px"])
        & np.isfinite(f["ask_px"])
        & (f["bid_px"] > 0)
        & (f["ask_px"] > 0)
    )
    act = t["action"].to_numpy()
    return (ts[ok], act[ok], {k: v[ok] for k, v in f.items()})


def session_bounds(d: dt.date, sess: list[str]) -> tuple[pd.Timestamp, pd.Timestamp]:
    h0, m0 = map(int, sess[0].split(":"))
    h1, m1 = map(int, sess[1].split(":"))
    t1 = pd.Timestamp(dt.datetime(d.year, d.month, d.day, h1, m1), tz=ET)
    d0 = (
        d - dt.timedelta(days=1) if h0 >= 17 else d
    )  # overnight session starts prior day
    t0 = pd.Timestamp(dt.datetime(d0.year, d0.month, d0.day, h0, m0), tz=ET)
    return t0.tz_convert("UTC").tz_localize(None), t1.tz_convert("UTC").tz_localize(
        None
    )


def behind_you_fill(at: pd.DataFrame, placed: pd.Timestamp):
    """First F on an order_id ADDED at (level, side) after `placed`. None if never.

    `at` = MBO events pre-filtered to this price+side. Robust to invisible GTC depth
    and iceberg reserve ahead: FIFO means anyone who joined after me fills after me.
    M (modify) is excluded from the behind-set — a size-down modify keeps priority.
    """
    if at.empty:
        return None
    adds = at[(at["action"] == "A") & (at["ts"] > placed)]
    if adds.empty:
        return None
    behind = set(adds["order_id"].to_numpy())
    fills = at[
        (at["action"] == "F") & (at["ts"] > placed) & at["order_id"].isin(behind)
    ]
    return None if fills.empty else fills["ts"].iloc[0]


def visible_queue_fill(at: pd.DataFrame, placed: pd.Timestamp):
    """Optimistic bound: displayed queue ahead at placement consumed by later fills."""
    if at.empty:
        return None
    before, after = at[at["ts"] <= placed], at[at["ts"] > placed]
    rest: dict = {}
    for a, oid, sz in zip(before["action"], before["order_id"], before["size"]):
        if a in ("A", "M"):
            rest[oid] = float(sz)
        elif a == "C":
            rest.pop(oid, None)
        elif a == "F":
            rest[oid] = rest.get(oid, float(sz)) - float(sz)
    q0 = sum(v for v in rest.values() if v > 0)
    f = after[after["action"] == "F"]
    if f.empty:
        return None
    consumed = f["size"].to_numpy(float).cumsum()
    idx = int(np.searchsorted(consumed, q0 + 1.0))
    return f["ts"].iloc[idx] if idx < len(f) else None


def trade_through_fill(
    ts, act, f, level: float, buy: bool, i_from: int, i_to: int, tick: float
):
    """Lower bound on MBP-1: trade strictly through level OR opposite quote crosses."""
    sl = slice(i_from, i_to)
    trade = (act[sl] == "T") & (
        f["price"][sl] <= level - tick if buy else f["price"][sl] >= level + tick
    )
    cross = (f["ask_px"][sl] <= level) if buy else (f["bid_px"][sl] >= level)
    hits = np.flatnonzero(trade | cross)
    return None if len(hits) == 0 else ts[i_from + int(hits[0])]


def exit_trade(
    ts, f, buy: bool, fill_i: int, i_to: int, level: float, tick: float, cfg: dict
):
    """Exit per manifest rules from entry at `level`. Returns dict of EV ticks per stress."""
    tgt = (
        level + cfg["target_ticks"] * tick
        if buy
        else level - cfg["target_ticks"] * tick
    )
    stp = level - cfg["stop_ticks"] * tick if buy else level + cfg["stop_ticks"] * tick
    i_h = min(
        int(ts.searchsorted(ts[fill_i] + pd.Timedelta(minutes=cfg["time_stop_min"]))),
        i_to,
    )
    ex = f["bid_px"][fill_i:i_h] if buy else f["ask_px"][fill_i:i_h]  # exit-side quote
    if len(ex) < 2:
        return None
    win = np.flatnonzero(ex >= tgt) if buy else np.flatnonzero(ex <= tgt)
    loss = np.flatnonzero(ex <= stp) if buy else np.flatnonzero(ex >= stp)
    iw = int(win[0]) if len(win) else 10**12
    il = int(loss[0]) if len(loss) else 10**12
    out = {}
    for s in STOP_STRESS:
        if il <= iw and il < 10**12:  # stop first (ties -> stop)
            px = float(ex[il]) - (
                s * tick if buy else -s * tick
            )  # observed quote + stress slip
            out[f"ev_s{s}"] = (px - level) / tick if buy else (level - px) / tick
            out["exit"] = "stop"
        elif iw < 10**12:
            out[f"ev_s{s}"] = float(cfg["target_ticks"])
            out["exit"] = "target"
        else:
            px = float(ex[-1])
            out[f"ev_s{s}"] = (px - level) / tick if buy else (level - px) / tick
            out["exit"] = "time"
    return out


def run_cell(cfg: dict, poison, max_days: int | None = None) -> pd.DataFrame:
    sym, tick = cfg["symbol"], TICK[cfg["symbol"]]
    start, end = MANIFEST["window"]
    inst_all = build_instances(sym, start, end, poison)
    inst_all = inst_all[inst_all["family"].isin(cfg["families"])]
    days = sorted(d for d in inst_all["trading_day"].unique() if d not in poison)
    if max_days:
        days = days[:max_days]  # pilot only — full runs pass None
    rows: list[dict] = []
    t0w = time.time()
    for i, d in enumerate(days):
        mb = load_mbp1_day(sym, d)
        if mb is None:
            continue
        ts, act, f = mb
        mid = (f["bid_px"] + f["ask_px"]) / 2.0
        mbo = read_mbo_trading_day(
            symbol=sym,
            trading_day=d,
            columns=["ts_event", "action", "side", "price", "size", "order_id"],
        )
        mbo = mbo.rename(columns={"ts_event": "ts"})
        mbo["ts"] = pd.DatetimeIndex(pd.to_datetime(mbo["ts"], utc=True)).tz_localize(
            None
        )
        mbo["pt"] = np.round(mbo["price"].to_numpy(float) / tick).astype(np.int64)
        s0, s1 = session_bounds(d, cfg["session_et"])
        for inst in inst_all[inst_all["trading_day"] == d].itertuples(index=False):
            lo = max(int(ts.searchsorted(max(pd.Timestamp(inst.valid_from), s0))), 1)
            hi = int(ts.searchsorted(min(pd.Timestamp(inst.valid_to), s1)))
            if hi - lo < 2:
                continue
            near = np.flatnonzero(
                np.abs(mid[lo:hi] - inst.price) <= cfg["proximity_ticks"] * tick
            )
            if len(near) == 0:
                continue
            pi = lo + int(near[0])  # placement index (proximity trigger, rule B14)
            placed = ts[pi]
            buy = (
                mid[pi] > inst.price
            )  # approaching from above -> level = support -> buy limit
            side = "B" if buy else "A"
            at = mbo[
                (mbo["pt"].to_numpy() == int(round(inst.price / tick)))
                & (mbo["side"] == side)
            ]
            t_by = behind_you_fill(at, placed)
            t_tt = trade_through_fill(ts, act, f, inst.price, buy, pi, hi, tick)
            t_vq = visible_queue_fill(at, placed)
            # touch + reaction (adverse-selection denominator, atlas definition)
            tch = np.flatnonzero(np.abs(mid[pi:hi] - inst.price) <= 2 * tick)
            touch_i = pi + int(tch[0]) if len(tch) else None
            r = {
                "cell": cfg["id"],
                "symbol": sym,
                "trading_day": d,
                "family": inst.family,
                "level_key": inst.level_key,
                "price": inst.price,
                "placed": placed,
                "buy": buy,
                "touched": touch_i is not None,
                "t_behind": t_by,
                "t_through": t_tt,
                "t_visq": t_vq,
            }
            if touch_i is not None:
                o = touch_outcomes(
                    ts,
                    f["bid_px"],
                    f["ask_px"],
                    mid,
                    touch_i,
                    hi,
                    inst.price,
                    from_below=not buy,
                    tick=tick,
                )
                if o is not None:
                    tw, tl = (
                        o[f"t_win_{cfg['target_ticks']}"],
                        o[f"t_loss_{cfg['stop_ticks']}"],
                    )
                    r["touch_ev88"] = (
                        cfg["target_ticks"]
                        if (not np.isnan(tw) and (np.isnan(tl) or tw < tl))
                        else (-cfg["stop_ticks"] if not np.isnan(tl) else o["g_end"])
                    )
                dsz = f["ask_sz"][touch_i] if not buy else f["bid_sz"][touch_i]
                r["defend_sz_norm"] = float(dsz) / max(
                    float(np.median(f["ask_sz" if not buy else "bid_sz"])), 1.0
                )
            t_fill = min(
                (x for x in (t_by, t_tt) if x is not None), default=None
            )  # headline∪LB evidence
            if t_fill is not None:
                fi = int(ts.searchsorted(t_fill))
                ex = exit_trade(ts, f, buy, fi, hi, inst.price, tick, cfg)
                if ex is not None:
                    r.update(
                        filled=True,
                        fill_rule="behind" if t_fill == t_by else "through",
                        **ex,
                    )
            r.setdefault("filled", False)
            rows.append(r)
        if (i + 1) % 10 == 0:
            print(
                f"  {cfg['id']} ..{i + 1}/{len(days)} days, {len(rows)} placements, {time.time() - t0w:.0f}s"
            )
    return pd.DataFrame(rows)


def main() -> int:
    if MANIFEST.get("committed_sha") in (None, ""):
        raise RuntimeError(
            "phase1_manifest.json not committed (committed_sha null) — pin it first."
        )
    ap = argparse.ArgumentParser()
    ap.add_argument("cells", nargs="*", default=None)
    ap.add_argument("--days", type=int, default=None, help="pilot: first N days only")
    a = ap.parse_args()
    start, end = MANIFEST["window"]
    guard_window(start, end, allow_confirmation=True)
    poison = roll_poison_days(start, end)
    OUT.mkdir(exist_ok=True)
    for cfg in MANIFEST["cells"]:
        if a.cells and cfg["id"] not in a.cells:
            continue
        df = run_cell(cfg, poison, max_days=a.days)
        if df.empty:
            raise RuntimeError(f"{cfg['id']}: 0 placements — refusing to write")
        if a.days:
            print(f"{cfg['id']} PILOT: {len(df)} placements (not written)")
            continue
        df.to_parquet(OUT / f"phase1_mode_a_{cfg['id']}.parquet")
        write_manifest(
            OUT / f"phase1_mode_a_{cfg['id']}.manifest.json",
            {"cell": cfg, "window": [start, end]},
            n_rows=len(df),
        )
        print(f"{cfg['id']}: {len(df)} placements written")
    print("Mode A simulation complete. Aggregate via phase1_report.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
