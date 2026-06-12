"""Defender-family atlas — PRE-REGISTERED config, then measure (counts first, rule C21).

PRE-REGISTRATION (fixed before this first run; amendable only before it executes):
  Entry anchor: ts_define (the real-time detection moment) — decision time per rule 5.
  Direction: JOIN the defender (defending bid -> long fade-frame; defending ask -> short).
  PRIMARY geometry: target k=12 ticks / stop j=4 ticks (3R), horizon 60 min.
    (Ben's spec: limit entry, >1 min holds, 2-3R, stop as tight as the defender allows —
     the defender at P is the protection; stop 4 ticks behind them.)
  Secondary (reported, no authority): (8,4), (16,4); full grid descriptive with
    selection-aware p5 only.
  Gate: n >= 100 events AND >= 40 days per symbol (tier-3); pooled view uses joint
    calendar-day blocks across symbols (rule C23).
  Costs: maker wall (commission only — resting at P alongside the defender) and taker
    wall (+ median spread + 1 tick) both reported.
  Window: CONFIRMATION 2026-01-02..2026-03-31 (MBO era; opened for this module —
    disclosed). HOLDOUT stays sealed.

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/defender_atlas.py
Artifacts: out/defender_events.parquet, report/defender_atlas.md
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
    SYMBOLS,
    TICK,
    guard_window,
    roll_poison_days,
    write_manifest,
)  # noqa: E402
from atlas_report import block_boot, comm_ticks, ev_matrix, md_table  # noqa: E402
from defender_events import detect_day  # noqa: E402
from outcomes import touch_outcomes  # noqa: E402
from touches import load_day_quotes  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

WINDOW = ("2026-01-02", "2026-03-31")
PRIMARY_KJ = (12, 4)
SECONDARY = [(8, 4), (16, 4)]
HORIZON_S = 3600
MIN_N, MIN_DAYS = 100, 40


def run_symbol(sym: str, poison) -> pd.DataFrame:
    days = [d.date() for d in pd.bdate_range(*WINDOW) if d.date() not in poison]
    tick = TICK[sym]
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
        quotes = load_day_quotes(sym, d)
        if quotes is None:
            continue
        ts, bid, ask, mid, _, _ = quotes
        for e in events:
            i0 = int(ts.searchsorted(pd.Timestamp(e["ts_define"])))
            if i0 >= len(ts) - 2:
                continue
            o = touch_outcomes(
                ts,
                bid,
                ask,
                mid,
                i0,
                len(ts),
                level=e["price"],
                from_below=(e["side"] == "A"),
                tick=tick,
                horizon_s=HORIZON_S,
            )
            if o is None:
                continue
            e["dist_at_define_ticks"] = float((mid[i0] - e["price"]) / tick)
            e["spread_ticks"] = float((ask[i0] - bid[i0]) / tick)
            e["level_key"] = f"{sym}|defender|{d}|{e['price']:.2f}"
            rows.append({**e, **o})
        if (i + 1) % 10 == 0:
            print(
                f"  {sym} ..{i + 1}/{len(days)} days, {len(rows)} events, {time.time() - t0w:.0f}s"
            )
    return pd.DataFrame(rows)


def stats_block(df: pd.DataFrame, sym: str) -> dict:
    ev, pairs = ev_matrix(df)
    ct = comm_ticks(sym)
    days = df["trading_day"].astype(str).to_numpy()
    out = {
        "symbol": sym,
        "n": len(df),
        "days": int(df["trading_day"].nunique()),
        "gate": len(df) >= MIN_N and df["trading_day"].nunique() >= MIN_DAYS,
    }
    for kj in [PRIMARY_KJ, *SECONDARY]:
        col = pairs.index(kj)
        net = ev[:, [col]] - ct
        means, _ = block_boot(net, days)
        tag = "PRIM" if kj == PRIMARY_KJ else "sec"
        out[f"{tag}{kj}_net"] = round(float(net.mean()), 2)
        out[f"{tag}{kj}_p5"] = round(float(np.percentile(means, 5)), 2)
    net_all = ev - ct
    _, best = block_boot(net_all, days)
    out["selaware_best_p5"] = round(float(np.percentile(best, 5)), 2)
    out["taker_extra"] = round(float(df["spread_ticks"].median()) + 1.0, 2)
    return out


def main() -> int:
    guard_window(*WINDOW, allow_confirmation=True)
    poison = roll_poison_days(*WINDOW)
    OUT.mkdir(exist_ok=True)
    frames = []
    for sym in SYMBOLS:
        df = run_symbol(sym, poison)
        print(
            f"{sym}: {len(df)} defender events "
            f"({df['trading_day'].nunique() if len(df) else 0} days)  <- POWER (counts)"
        )
        if len(df):
            frames.append(df)
    alld = pd.concat(frames, ignore_index=True)
    if alld.empty:
        raise RuntimeError("0 defender events — refusing to write")
    alld.to_parquet(OUT / "defender_events.parquet")
    write_manifest(
        OUT / "defender_events.manifest.json",
        {
            "window": WINDOW,
            "primary_kj": PRIMARY_KJ,
            "horizon_s": HORIZON_S,
            "thresholds": "see defender_events.py header",
        },
        n_rows=len(alld),
    )

    lines = [
        "# Defender-family atlas (pre-registered (12,4)@60m; CONFIRMATION window)",
        "",
    ]
    tab = pd.DataFrame(
        [
            stats_block(alld[alld["symbol"] == s], s)
            for s in SYMBOLS
            if (alld["symbol"] == s).sum() >= 20
        ]
    )
    lines += [md_table(tab), ""]
    # end-reason split (does the defense outcome matter? descriptive)
    er = (
        alld.groupby(["symbol", "end_reason"], observed=True)
        .size()
        .unstack(fill_value=0)
    )
    lines += ["End reasons (descriptive):", md_table(er.reset_index()), ""]
    report = "\n".join(lines)
    (MODULE / "report" / "defender_atlas.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
