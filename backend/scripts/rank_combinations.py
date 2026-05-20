"""Layer 2: combination scan.

For top detector modes from Layer 1, compute per-event R-multiples
keyed by timestamp. Then find combos: "when detector A fires AND
detector B fires within W minutes, what's the joint R?"

Strategy: re-run fill sim BUT this time save (ts, mode, r) per event.
Then in-memory join: for each (mode_a event, mode_b event) within
window, mark as joint-event. Aggregate.

Caveats:
  - Joint events require BOTH detectors to fire, so sample size shrinks
    quickly. Threshold at n>=30 joint events.
  - "A fires within W min of B" is direction-agnostic for now (A could
    fire before or after B). v0 takes the LATER event's R-multiple as
    the joint outcome.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
BARS_ROOT = Path(r"D:/data/processed/bars/timeframe=1m")
RESEARCH_PARQUET = Path(r"C:/Users/benbr/BacktestStation/data/research_events")
SYMBOL = "NQ.c.0"

# Reuse the fill sim code from rank_detectors_by_edge.py by importing it
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rank_detectors_by_edge import (  # noqa: E402
    SUPPORTED_DETECTORS, load_bars_for_dates, compute_atr, simulate_fill,
    ATR_TIMEFRAME_MIN, ATR_FLOOR_MIN, ATR_PERIOD,
)


def collect_per_event_r() -> pd.DataFrame:
    print("Loading NQ 1m bars (heavy step)...")
    all_dates = sorted([
        dt.date.fromisoformat(p.name.replace("date=", ""))
        for p in (BARS_ROOT / f"symbol={SYMBOL}").iterdir()
        if p.name.startswith("date=")
    ])
    bars_1m = load_bars_for_dates(SYMBOL, set(all_dates))
    print(f"  {len(bars_1m):,} 1m bars loaded")
    print("Computing ATRs...")
    atr_5m = compute_atr(bars_1m, ATR_TIMEFRAME_MIN, ATR_PERIOD)
    atr_30m = compute_atr(bars_1m, ATR_FLOOR_MIN, ATR_PERIOD)
    print()

    con = duckdb.connect()
    rows = []
    for feat in SUPPORTED_DETECTORS:
        sql = f"""
            SELECT bar_end_utc, event_type, side, outcomes
            FROM read_parquet('{RESEARCH_PARQUET.as_posix()}/feature_name={feat}/event_year=*/*.parquet')
            WHERE primary_symbol = '{SYMBOL}'
            AND json_extract(outcomes, '$.thesis_direction') IS NOT NULL
            AND json_extract(outcomes, '$.reference_close') IS NOT NULL
        """
        events = con.execute(sql).fetchall()
        print(f"{feat}: {len(events):,} candidate events")
        for bar_end_utc, event_type, side, outcomes_json in events:
            try:
                out = json.loads(outcomes_json)
                thesis = out.get("thesis_direction")
                ref = out.get("reference_close")
                if thesis not in ("up", "down") or ref is None:
                    continue
                ts = pd.Timestamp(bar_end_utc, tz="UTC") if isinstance(bar_end_utc, str) \
                    else (pd.Timestamp(bar_end_utc).tz_localize("UTC") if bar_end_utc.tzinfo is None
                          else pd.Timestamp(bar_end_utc))
                fill = simulate_fill(
                    ts, float(ref), thesis, bars_1m, atr_5m, atr_30m,
                )
                if fill is None:
                    continue
                rows.append({
                    "ts": ts, "feature": feat, "event_type": event_type,
                    "side": side, "thesis": thesis,
                    "r_multiple": fill["r_multiple"],
                    "exit_reason": fill["exit_reason"],
                })
            except Exception:
                continue
    df = pd.DataFrame(rows)
    return df


def main():
    print("=== Layer 2: combination scan ===")
    print(f"Symbol: {SYMBOL}")
    print()
    per_event = collect_per_event_r()
    print(f"Total per-event r records: {len(per_event):,}")
    per_event_path = REPO_ROOT / "STRATEGY_DISCOVERY_layer2_per_event.parquet"
    per_event.to_parquet(per_event_path, index=False)
    print(f"Saved {per_event_path}")
    print()

    # Build mode_key = feature/event_type/side string for grouping
    per_event["mode_key"] = (
        per_event["feature"] + "/"
        + per_event["event_type"] + "/" + per_event["side"]
    )

    # Top modes from Layer 1 (sample-size > 1000 AND positive sum_R)
    summary = per_event.groupby("mode_key").agg(
        n=("r_multiple", "size"),
        sum_R=("r_multiple", "sum"),
        avg_R=("r_multiple", "mean"),
        win_rate=("r_multiple", lambda x: (x > 0).mean()),
    ).sort_values("sum_R", ascending=False)
    print("Top 10 mode_key (Layer 1 confirmation):")
    print(summary.head(10).to_string())
    print()

    # Anchors = profitable modes with big sample (these are the "edge" candidates)
    anchors = summary[(summary["n"] >= 1000) & (summary["sum_R"] > 0)].index.tolist()
    print(f"Anchor modes (n>=1000 AND sum_R>0): {len(anchors)}")
    for a in anchors:
        print(f"  {a}")
    print()

    # For each anchor: find OTHER mode events that fire within W minutes
    # of an anchor event. Compute joint outcomes.
    WINDOW_MIN = 60  # +/- 60 min around anchor event
    delta = pd.Timedelta(minutes=WINDOW_MIN)
    # All non-anchor events
    other_events = per_event[~per_event["mode_key"].isin(anchors)]
    other_by_key = {k: g.sort_values("ts").reset_index(drop=True) for k, g in
                    other_events.groupby("mode_key")}
    print(f"Non-anchor modes to scan: {len(other_by_key)}")
    print()
    print(f"Scanning combinations (anchor +/-{WINDOW_MIN}min)...")
    combo_rows = []
    for anchor_key in anchors:
        anchor_df = per_event[per_event["mode_key"] == anchor_key].sort_values("ts").reset_index(drop=True)
        for other_key, other_df in other_by_key.items():
            # Use merge_asof to find each anchor's nearest other-event within window
            merged = pd.merge_asof(
                anchor_df.sort_values("ts"),
                other_df[["ts", "r_multiple"]].rename(
                    columns={"ts": "other_ts", "r_multiple": "other_r"}
                ).sort_values("other_ts"),
                left_on="ts", right_on="other_ts",
                direction="nearest",
                tolerance=delta,
            )
            joint = merged.dropna(subset=["other_r"])
            if len(joint) < 30:
                continue
            # Joint outcome: take the anchor's r (the strategy fires on anchor;
            # the other event is a CONDITIONAL FILTER -- when it co-occurs)
            n_joint = len(joint)
            joint_avg_r = joint["r_multiple"].mean()
            joint_sum_r = joint["r_multiple"].sum()
            joint_win = (joint["r_multiple"] > 0).mean()
            # Baseline (anchor alone, all events)
            anchor_avg_r = anchor_df["r_multiple"].mean()
            anchor_win = (anchor_df["r_multiple"] > 0).mean()
            combo_rows.append({
                "anchor": anchor_key,
                "filter": other_key,
                "n_joint": n_joint,
                "anchor_total_n": len(anchor_df),
                "joint_win": joint_win,
                "anchor_win_baseline": anchor_win,
                "joint_avg_R": joint_avg_r,
                "anchor_avg_R_baseline": anchor_avg_r,
                "delta_avg_R": joint_avg_r - anchor_avg_r,
                "joint_sum_R": joint_sum_r,
            })

    combos = pd.DataFrame(combo_rows)
    combos = combos.sort_values("delta_avg_R", ascending=False)
    combos_path = REPO_ROOT / "STRATEGY_DISCOVERY_layer2_combos.csv"
    combos.to_csv(combos_path, index=False)
    print(f"Wrote {combos_path}")
    print()
    print("=" * 130)
    print("TOP 20 combinations (sorted by delta_avg_R = how much joint condition IMPROVES the anchor's avg R):")
    print(f"  {'anchor':<42s} {'filter':<42s} {'n':>5s} {'jwin%':>6s} {'awin%':>6s} {'jR':>8s} {'aR':>8s} {'dR':>8s}")
    for _, r in combos.head(20).iterrows():
        print(f"  {r['anchor']:<42s} {r['filter']:<42s} "
              f"{int(r['n_joint']):>5,} {r['joint_win']*100:>5.1f}% {r['anchor_win_baseline']*100:>5.1f}% "
              f"{r['joint_avg_R']:>+8.3f} {r['anchor_avg_R_baseline']:>+8.3f} {r['delta_avg_R']:>+8.3f}")
    print()
    print("BOTTOM 10 combinations (filter HURTS the anchor):")
    for _, r in combos.tail(10).iterrows():
        print(f"  {r['anchor']:<42s} {r['filter']:<42s} "
              f"{int(r['n_joint']):>5,} {r['joint_win']*100:>5.1f}% {r['anchor_win_baseline']*100:>5.1f}% "
              f"{r['joint_avg_R']:>+8.3f} {r['anchor_avg_R_baseline']:>+8.3f} {r['delta_avg_R']:>+8.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
