"""Densify the gamma-test events: ES-only (no peers -> ~4x faster), DENSE over the 2025 window where we own
daily GEX. We previously only *sampled* ~57 of those days; running them all ~triples the negative-gamma days,
which is exactly the slice the gamma conditioning test was starved for. Writes a separate cache so the main
cross-index cache is untouched.

Run: backend/.venv/Scripts/python.exe market_state/intraday/gamma_densify.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zone_events as ze  # noqa: E402

ze.PEERS = []  # ES-only: gamma test doesn't use peer features, so skip the 4x peer load
OUT = Path("market_state/out/zone_events_ES_2025.parquet")


def main() -> int:
    levels = ze.precompute_levels()
    days = [d for d in ze.available_days() if d < "2026-01-01"]  # 2025 window = GEX coverage
    print(f"densifying {len(days)} ES-only days ({days[0]}..{days[-1]})")
    ev = []
    for i, day in enumerate(days):
        lv = levels.get(dt.date.fromisoformat(day))
        if not lv:
            continue
        try:
            ev += ze.process_day(day, lv["pdh"], lv["pdl"])
        except Exception as e:  # noqa: BLE001
            print(f"  {day}: ERROR {type(e).__name__}: {e}")
        if (i + 1) % 30 == 0:
            print(f"  ..{i + 1}/{len(days)} days, {len(ev)} events")
    df = pd.DataFrame(ev).set_index("ts").sort_index()
    df.to_parquet(OUT)
    print(f"\nwrote {len(df)} events ({df.index.min().date()}..{df.index.max().date()}) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
