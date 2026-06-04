"""Wire upgraded-Mira's new levels into Mira's REAL pipeline -- via monkeypatch, live engine untouched.

Injects gap_levels into Mira v1's `_build_level_specs`, then runs Mira's actual `build()` (sweep ->
MBO-bookproxy confirmation -> honest outcome) on PDH/PDL + daily_gap. SMT/VP/ATLAS attachments OFF for the
first pass (the core edge is sweep+bookproxy+R). Validates that the wiring produces real Mira events with
outcomes -- reproducing PDH/PDL, plus the new gap family flowing through unchanged.

(gamma walls are 2025-only, MBO is 2026 -> no overlap -> gamma x MBO-confirmation is data-blocked; later.)

Run: backend/.venv/Scripts/python.exe experiments/mira_upgraded_v0/run_pipeline.py [START END]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

RT = Path(__file__).resolve().parents[2]
for _p in ["live_engine/vendor/bs_mira/mira_v1", "live_engine/vendor/bs_mira/mira_v0",
           str(Path(__file__).resolve().parent)]:
    sys.path.insert(0, str(RT / _p) if not _p.startswith(str(RT)) else _p)
import build_level_events as ble  # noqa: E402  (Mira v1, read-only)
from level_families import gap_levels  # noqa: E402  (my new family)

# --- monkeypatch: Mira's spec registry ALSO emits my gap levels (no engine file touched) ---
_orig_specs = ble._build_level_specs


def _patched_specs(*, bars, rth, session_date, prior_date, level_families, opening_range_minutes):
    specs = _orig_specs(bars=bars, rth=rth, session_date=session_date, prior_date=prior_date,
                        level_families=level_families, opening_range_minutes=opening_range_minutes)
    if "daily_gap" in level_families:
        cur = rth[rth["session_date"].eq(session_date)].copy()
        pri = rth[rth["session_date"].eq(prior_date)].copy() if prior_date is not None else pd.DataFrame()
        specs += gap_levels(session_date, pri, cur)
    return specs


ble._build_level_specs = _patched_specs


def main(start: str, end: str, out_name: str = "events_upgraded.parquet") -> int:
    args = argparse.Namespace(
        symbols=["ES.c.0"], start=start, end=end, data_root=None,
        level_families=["pdh_pdl", "previous_week", "overnight", "premarket", "opening_range", "daily_gap"],
        opening_range_minutes=30,
        smt_features="", smt_db="", smt_source="db", no_smt_state=True, no_smt_mtf=True,
        volume_profile_db="", no_volume_profile=True, atlas_predictions=None,
        out=str(Path(__file__).parent / "out"), max_events=None,
        break_buffer_ticks=2.0, reject_min_ticks=8.0,
    )
    print(f"running Mira build() on {args.symbols} {start}..{end}  families={args.level_families}")
    events = ble.build(args)
    if events is None or events.empty:
        print("no events produced.")
        return 0
    outp = Path(args.out)
    outp.mkdir(parents=True, exist_ok=True)
    events.to_parquet(outp / out_name)
    print(f"\nEVENTS n={len(events)}  -> {outp / out_name}")
    if "level_family" in events.columns:
        print("by family:\n" + events["level_family"].value_counts().to_string())
    outcome_cols = [c for c in events.columns
                    if any(k in c.lower() for k in ("label", "net_r", "outcome", "_r_", "reclaim", "reject"))]
    print(f"\noutcome/label columns: {outcome_cols[:25]}")
    for c in outcome_cols[:6]:
        try:
            print(f"  {c}: {events[c].value_counts(dropna=False).head(4).to_dict()}")
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    s = sys.argv[1] if len(sys.argv) > 1 else "2026-04-06"
    e = sys.argv[2] if len(sys.argv) > 2 else "2026-04-10"
    out_name = sys.argv[3] if len(sys.argv) > 3 else "events_upgraded.parquet"
    raise SystemExit(main(s, e, out_name))
