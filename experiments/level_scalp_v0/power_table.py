"""Phase 0 step 1 — the POWER TABLE: touch counts per cell, published BEFORE any
reaction stat is unblinded (PLAN rule C21). No outcomes are computed here.

Counts touches of every tier-1 + round-number level instance on MBP-1 mid over the
SELECTION window, then reports per (family x symbol) and per tod_bucket whether the
min-n gate (n >= 200 touches AND >= 60 distinct days) is met.

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/power_table.py [SYM ...]
  [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--pilot N]  (pilot = first N days only)
Artifacts: out/touches_p0_{SYM}.parquet, out/power_table.parquet (+ .manifest.json)
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
    guard_window,
    roll_poison_days,
    write_manifest,
)  # noqa: E402
from level_specs import build_instances  # noqa: E402
from touches import detect_touches, load_day_quotes  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

MIN_N, MIN_DAYS = 200, 60  # PLAN rule C21 gate


def run_symbol(
    sym: str, start: str, end: str, poison, pilot: int | None
) -> pd.DataFrame:
    inst = build_instances(sym, start, end, poison)
    if inst.empty:
        raise RuntimeError(f"{sym}: 0 level instances built — refusing to continue")
    days = sorted(inst["trading_day"].unique())
    days = [d for d in days if d not in poison]
    if pilot:
        days = days[:pilot]
    print(
        f"{sym}: {len(inst)} instances over {len(days)} non-roll days {days[0]}..{days[-1]}"
    )
    rows: list[dict] = []
    t_start, skipped = time.time(), 0
    for i, d in enumerate(days):
        quotes = load_day_quotes(sym, d)
        if quotes is None:
            skipped += 1
            continue
        rows += detect_touches(sym, d, inst[inst["trading_day"] == d], quotes)
        if (i + 1) % 20 == 0:
            el = time.time() - t_start
            print(f"  ..{i + 1}/{len(days)} days, {len(rows)} touches, {el:.0f}s")
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(
            f"{sym}: 0 touches detected — refusing to write (0-row guard)"
        )
    df.to_parquet(OUT / f"touches_p0_{sym}.parquet")
    print(f"{sym}: {len(df)} touches, {skipped} empty days skipped")
    return df


def power_report(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["symbol", "family"], observed=True)
    tab = g.agg(
        n_touches=("t0", "size"),
        n_days=("trading_day", "nunique"),
        n_levels=("level_key", "nunique"),
        first_touch_share=("touch_n", lambda s: float((s == 1).mean())),
        med_spread_ticks=("spread_ticks", "median"),
    ).reset_index()
    tab["gate"] = (tab["n_touches"] >= MIN_N) & (tab["n_days"] >= MIN_DAYS)
    bucket = (
        df.groupby(["symbol", "family", "tod_bucket"], observed=True)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    return tab.merge(bucket, on=["symbol", "family"], how="left")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*", default=None)
    ap.add_argument("--start", default=SELECTION[0])
    ap.add_argument("--end", default=SELECTION[1])
    ap.add_argument("--pilot", type=int, default=None)
    a = ap.parse_args()
    guard_window(a.start, a.end)
    syms = a.symbols or SYMBOLS
    OUT.mkdir(exist_ok=True)
    poison = roll_poison_days(a.start, a.end)
    frames = [run_symbol(s, a.start, a.end, poison, a.pilot) for s in syms]
    allt = pd.concat(frames, ignore_index=True)
    tab = power_report(allt)
    tab.to_parquet(OUT / "power_table.parquet")
    write_manifest(
        OUT / "power_table.manifest.json",
        {
            "start": a.start,
            "end": a.end,
            "symbols": syms,
            "pilot": a.pilot,
            "min_n": MIN_N,
            "min_days": MIN_DAYS,
            "n_roll_poison_days": len(poison),
        },
        n_rows=len(tab),
    )
    pd.set_option("display.width", 200)
    print(
        "\nPOWER TABLE (gate = n>=200 & days>=60; counts only — no outcomes unblinded)"
    )
    print(
        tab.sort_values(["symbol", "n_touches"], ascending=[True, False]).to_string(
            index=False
        )
    )
    print(f"\ngated-in cells: {int(tab['gate'].sum())}/{len(tab)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
