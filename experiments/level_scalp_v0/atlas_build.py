"""Phase 0 step 2 — build the touch ATLAS: per-touch context + reaction outcomes.

THIS RUN TRIGGERS THE SPEC FREEZE (PLAN: touch constants, primary cells, fill rules lock
at the first atlas run). It writes per-touch rows only; aggregation/unblinding of cell
statistics happens in atlas_report.py.

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/atlas_build.py [SYM ...]
Artifacts: out/atlas_touches_{SYM}.parquet (+ .manifest.json)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import (
    OUT,
    SELECTION,
    SYMBOLS,
    TICK,
    guard_window,
    roll_poison_days,
    write_manifest,
)  # noqa: E402
from level_specs import build_instances  # noqa: E402
from touches import detect_touches, load_day_quotes  # noqa: E402
from outcomes import touch_outcomes  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def run_symbol(sym: str, start: str, end: str, poison) -> int:
    inst = build_instances(sym, start, end, poison)
    if inst.empty:
        raise RuntimeError(f"{sym}: 0 level instances — refusing to continue")
    days = sorted(d for d in inst["trading_day"].unique() if d not in poison)
    print(f"{sym}: {len(inst)} instances, {len(days)} days {days[0]}..{days[-1]}")
    tick = TICK[sym]
    rows: list[dict] = []
    t_start = time.time()
    for i, d in enumerate(days):
        quotes = load_day_quotes(sym, d)
        if quotes is None:
            continue
        ts, bid, ask, mid, _, _ = quotes
        for r in detect_touches(sym, d, inst[inst["trading_day"] == d], quotes):
            o = touch_outcomes(
                ts,
                bid,
                ask,
                mid,
                r["i0"],
                r["i_hi"],
                level=r["price"],
                from_below=(r["side"] == "below"),
                tick=tick,
            )
            if o is None:
                continue
            r.pop("i0"), r.pop("i_hi")
            rows.append({**r, **o})
        if (i + 1) % 25 == 0:
            print(
                f"  ..{i + 1}/{len(days)} days, {len(rows)} touches, {time.time() - t_start:.0f}s"
            )
    if not rows:
        raise RuntimeError(f"{sym}: 0 atlas rows — refusing to write (0-row guard)")
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / f"atlas_touches_{sym}.parquet")
    write_manifest(
        OUT / f"atlas_touches_{sym}.manifest.json",
        {"start": start, "end": end, "symbol": sym, "stage": "atlas_v0"},
        n_rows=len(df),
    )
    print(f"{sym}: {len(df)} atlas rows written")
    return len(df)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*", default=None)
    a = ap.parse_args()
    start, end = SELECTION
    guard_window(start, end)
    OUT.mkdir(exist_ok=True)
    poison = roll_poison_days(start, end)
    total = sum(run_symbol(s, start, end, poison) for s in (a.symbols or SYMBOLS))
    print(f"\natlas build complete: {total} touch rows. Aggregate via atlas_report.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
