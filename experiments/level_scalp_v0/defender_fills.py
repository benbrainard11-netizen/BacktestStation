"""Defender family — HONEST FILLS on the atlas survivors (NQ, RTY), pinned config.

The atlas (12,4)@60m screen passed pre-registration on NQ (+3.06, p5 +1.69) and RTY
(+2.32, p5 +1.34); ES was null, YM unpowered. This run replays the surviving cells
through the Phase-1 fill standard: virtual limit placed at the defended price AT
ts_define (decision time), proof-grade fills only (behind-you MBO rule OR
trade-through), realized exits (target on exit-side quote-cross; stop at the OBSERVED
opposite quote at first crossing + {1,2,4} tick stress; 60-min time stop; stop wins
ties). Fill expectation here is structurally better than Phase 1's first-touch study:
the detection evidence IS continuous trading at the level.

Pinned config (committed before this runs): symbols NQ/RTY, k=12, j=4, time-stop 60m,
placement at ts_define, one order per event, cancel at event valid_to + 60m.

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/defender_fills.py
Artifacts: out/defender_fills_{SYM}.parquet, report/defender_fills.md
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

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
from atlas_report import block_boot, comm_ticks  # noqa: E402
from defender_events import detect_day  # noqa: E402
from mode_a_sim import (
    behind_you_fill,
    exit_trade,
    load_mbp1_day,
    trade_through_fill,
)  # noqa: E402

sys.path.insert(0, str(REPO / "backend"))
from app.data.reader import read_mbo_trading_day  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

WINDOW = ("2026-01-02", "2026-03-31")
SYMS = ["NQ.c.0", "RTY.c.0"]
CFG = {"target_ticks": 12, "stop_ticks": 4, "time_stop_min": 60}


def run_symbol(sym: str, poison) -> pd.DataFrame:
    tick = TICK[sym]
    days = [d.date() for d in pd.bdate_range(*WINDOW) if d.date() not in poison]
    rows: list[dict] = []
    t0w = time.time()
    for i, d in enumerate(days):
        try:
            events = detect_day(sym, d)
        except Exception as e:  # noqa: BLE001
            print(f"  {sym} {d}: ERROR {type(e).__name__}: {e}")
            continue
        if not events:
            continue
        mb = load_mbp1_day(sym, d)
        if mb is None:
            continue
        ts, act, f = mb
        mbo = read_mbo_trading_day(
            symbol=sym,
            trading_day=d,
            columns=["ts_event", "action", "side", "price", "size", "order_id"],
        ).rename(columns={"ts_event": "ts"})
        mbo["ts"] = pd.DatetimeIndex(pd.to_datetime(mbo["ts"], utc=True)).tz_localize(
            None
        )
        mbo["pt"] = np.round(mbo["price"].to_numpy(float) / tick).astype(np.int64)
        for e in events:
            placed = pd.Timestamp(e["ts_define"])
            pi = int(ts.searchsorted(placed))
            hi = min(
                int(
                    ts.searchsorted(placed + pd.Timedelta(minutes=CFG["time_stop_min"]))
                )
                + 1,
                len(ts),
            )
            if hi - pi < 2:
                continue
            buy = e["side"] == "B"  # join the defender: defending bid -> buy at P
            at = mbo[
                (mbo["pt"].to_numpy() == int(round(e["price"] / tick)))
                & (mbo["side"] == e["side"])
            ]
            t_by = behind_you_fill(at, placed)
            t_tt = trade_through_fill(ts, act, f, e["price"], buy, pi, hi, tick)
            r = {
                "symbol": sym,
                "trading_day": d,
                "price": e["price"],
                "side": e["side"],
                "placed": placed,
                "end_reason": e["end_reason"],
                "filled": False,
            }
            t_fill = min((x for x in (t_by, t_tt) if x is not None), default=None)
            if t_fill is not None:
                fi = int(ts.searchsorted(t_fill))
                ex = exit_trade(ts, f, buy, fi, len(ts), e["price"], tick, CFG)
                if ex is not None:
                    r.update(
                        filled=True,
                        fill_rule="behind" if t_fill == t_by else "through",
                        fill_latency_s=float((t_fill - placed).total_seconds()),
                        **ex,
                    )
            rows.append(r)
        if (i + 1) % 10 == 0:
            print(
                f"  {sym} ..{i + 1}/{len(days)} days, {len(rows)} placements, {time.time() - t0w:.0f}s"
            )
    return pd.DataFrame(rows)


def main() -> int:
    guard_window(*WINDOW, allow_confirmation=True)
    poison = roll_poison_days(*WINDOW)
    OUT.mkdir(exist_ok=True)
    lines = ["# Defender family — honest fills (pinned (12,4)@60m, NQ/RTY)", ""]
    pooled = []
    for sym in SYMS:
        df = run_symbol(sym, poison)
        if df.empty:
            print(f"{sym}: 0 placements")
            continue
        df.to_parquet(OUT / f"defender_fills_{sym}.parquet")
        write_manifest(
            OUT / f"defender_fills_{sym}.manifest.json",
            {"window": WINDOW, "cfg": CFG, "symbol": sym},
            n_rows=len(df),
        )
        ct = comm_ticks(sym)
        fills = df[df["filled"] == True].copy()  # noqa: E712
        r = {
            "symbol": sym,
            "placements": len(df),
            "fills": len(fills),
            "fill_rate": round(len(fills) / len(df), 2),
        }
        if len(fills):
            for s in (1, 2, 4):
                r[f"net_s{s}"] = round(float(fills[f"ev_s{s}"].mean() - ct), 2)
            daysb = fills["trading_day"].astype(str).to_numpy()
            net1 = (fills["ev_s1"].to_numpy(float) - ct)[:, None]
            means, _ = block_boot(net1, daysb)
            r["p5_s1"] = round(float(np.percentile(means, 5)), 2)
            r["exit_mix"] = fills["exit"].value_counts().to_dict()
            r["med_fill_latency_s"] = round(float(fills["fill_latency_s"].median()), 1)
            fills["net"] = net1[:, 0]
            pooled.append(fills[["trading_day", "net"]])
        lines += [f"## {sym}", "", str(r), ""]
        print(r)
    if pooled:
        pool = pd.concat(pooled, ignore_index=True)
        means, _ = block_boot(
            pool["net"].to_numpy(float)[:, None],
            pool["trading_day"].astype(str).to_numpy(),
        )
        lines += [
            f"**POOLED: n={len(pool)} fills, mean net {float(pool['net'].mean()):+.2f} "
            f"ticks, joint day-block p5 {float(np.percentile(means, 5)):+.2f}**",
            "",
        ]
        print(lines[-2])
    (MODULE / "report" / "defender_fills.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
