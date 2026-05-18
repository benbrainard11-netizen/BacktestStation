"""V28 — Walk-forward against the SLIM anchor matrices.

Uses the same simulator + same trade rule as v20/v27, but against slim
anchor matrices built by `backend/scripts/build_slim_anchors_2015_2017.py`
(label recomputed from raw bars, v19-style).

Two purposes:
  1. VALIDATION: run on 2018-2019 slim anchors and compare to v20's
     actual result. If cum_R and avg_R are in the same ballpark, the
     slim-anchor methodology is credible.
  2. FRESH HOLDOUT: run on 2015-2017 slim anchors. If positive, this
     is genuinely new evidence that the strategy generalizes.

USAGE:
  # Validation pass against 2018-2019:
  python backend/scripts/ml/v28_slim_anchor_walkforward.py \
      --anchor-base D:/BacktestStationData/slim_anchors_2018_2019_validation/data/ml/anchors \
      --window-start 2018-01-01 --window-end 2019-12-31

  # Fresh holdout 2015-2017:
  python backend/scripts/ml/v28_slim_anchor_walkforward.py \
      --anchor-base D:/BacktestStationData/expanded_holdout_2015_2017/data/ml/anchors \
      --window-start 2015-01-01 --window-end 2017-12-31
"""

from __future__ import annotations

import argparse
import json
import sys
import time as time_mod
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ml.rigorous_backtest_v1 import (  # noqa: E402
    BarsCache,
    Signal,
)
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP  # noqa: E402
from scripts.ml.v10_raw_ob_slippage import (  # noqa: E402
    Slippage,
    simulate_v7_slip,
    resolve_dir,
)
from scripts.ml.v20_locked_walkforward import (  # noqa: E402
    all_events_picks_any_year,
    filter_picks_to_window,
    compute_stats,
)


ROOT = Path(r"C:\Users\benbr\BacktestStation")

PRIMARY_SLIPPAGE = Slippage(
    "primary_2tick", entry_ticks=2.0, stop_ticks=2.0, time_exit_ticks=2.0
)

SWEEP_DROP_HOURS = {22, 23, 0, 1, 2, 3, 4, 5, 6}


# Two families against the slim anchors.
FAMILIES = [
    {
        "name": "OB strict (slim)",
        "matrix_file": "ob_snapshots_xctx_strict_slim",
        "snapshot": "at_fire",
        "side": "all",
        "label": "label.strict.next_60m.ob_broken_through_continuation",
        "direction_rule": "side_aware",
        "reverse": False,
        "hour_filter": None,
    },
    {
        "name": "Sweep reversed filtered (slim)",
        "matrix_file": "sweep_snapshots_xctx_fvggeom_slim",
        "snapshot": "at_fire",
        "side": "all",
        "label": "label.ob_confirmation.did_confirm",
        "direction_rule": "side_aware",
        "reverse": True,  # per v20 lockfile
        "hour_filter": {
            "type": "drop_utc_hours",
            "hours": [22, 23, 0, 1, 2, 3, 4, 5, 6],
        },
    },
]


SYMBOLS = {"NQ.c.0", "ES.c.0", "YM.c.0"}


def simulate_picks(picks: pd.DataFrame, bars: BarsCache, *, reverse: bool,
                   hour_filter: dict | None, symbols: set[str]) -> pd.DataFrame:
    picks = picks[picks["symbol"].isin(symbols)].copy()
    if picks.empty:
        return pd.DataFrame()

    picks["natural_dir"] = picks["anchor_side"].apply(resolve_dir)
    if reverse:
        picks["direction"] = picks["natural_dir"].apply(
            lambda d: "long" if d == "short" else "short"
        )
    else:
        picks["direction"] = picks["natural_dir"]

    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7_slip(
            bars, row["symbol"], row["fire_ts"], row["direction"],
            V8A_STOP, PRIMARY_SLIPPAGE,
        )
        trades.append({
            "slippage": PRIMARY_SLIPPAGE.name,
            "test_year": int(row["fire_ts"].year),
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            **sim,
        })
    td = pd.DataFrame(trades)
    if td.empty:
        return td

    if hour_filter and hour_filter.get("type") == "drop_utc_hours":
        drop_hours = set(hour_filter["hours"])
        td["entry_hour_utc"] = pd.to_datetime(
            td["entry_ts"], utc=True, errors="coerce"
        ).dt.hour
        before = len(td)
        td = td[~td["entry_hour_utc"].isin(drop_hours)].copy()
        print(f"      hour-filter dropped {before - len(td)} of {before} trades")
    return td


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor-base", required=True,
                        help="Directory containing the slim anchor parquets.")
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end", required=True)
    parser.add_argument("--out-dir", default=None,
                        help="Default: derived from anchor-base parent.")
    parser.add_argument("--label", default="auto",
                        help="auto | filter to label==1 only | none (simulate all)")
    args = parser.parse_args()

    anchor_base = Path(args.anchor_base)
    if not anchor_base.exists():
        print(f"ERROR: anchor-base not found: {anchor_base}")
        return 1

    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else (anchor_base.parents[2] / "v28_simulation_results")
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    win_start = pd.Timestamp(args.window_start, tz="UTC")
    win_end = pd.Timestamp(args.window_end, tz="UTC")
    if win_end.hour == 0:
        win_end = win_end + pd.Timedelta(hours=23, minutes=59, seconds=59)

    print(f"=== V28 — Slim-anchor walk-forward ===")
    print(f"Anchor base: {anchor_base}")
    print(f"Window:      {win_start} → {win_end}")
    print(f"Symbols:     {sorted(SYMBOLS)}")
    print(f"Out dir:     {out_dir}")
    print()

    bars = BarsCache()
    t0 = time_mod.time()
    rollup = []

    for fam in FAMILIES:
        print(f"--- Family: {fam['name']} ---")
        sig = Signal(
            name=fam["name"],
            anchors_dir=anchor_base,
            matrix_file=fam["matrix_file"],
            snapshot=fam["snapshot"],
            side=fam["side"],
            label=fam["label"],
            direction_rule=fam["direction_rule"],
        )
        all_picks = all_events_picks_any_year(sig)
        print(f"  events with label: {len(all_picks):,}")
        if all_picks.empty:
            print(f"  no events; skipping")
            continue

        window_picks = filter_picks_to_window(all_picks, win_start, win_end)
        print(f"  events in window: {len(window_picks):,}")
        if window_picks.empty:
            continue

        td = simulate_picks(
            window_picks, bars,
            reverse=fam["reverse"], hour_filter=fam["hour_filter"], symbols=SYMBOLS,
        )
        if td.empty:
            print(f"  no trades; skipping")
            continue

        stats = compute_stats(td)
        print(f"  stats: n={stats['n']:,} cum_R={stats['cum_r']:.2f} "
              f"avg_R={stats['avg_r']:.4f} win_rate={stats['win_rate']*100:.1f}%")
        print(f"  per_symbol: {stats['per_symbol_cum_r']}")
        print()

        # Write trades + rollup
        slug = (
            fam["name"]
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
        )
        td.to_csv(out_dir / f"trades_{slug}.csv", index=False)
        rollup.append({"family": fam["name"], **stats})

    rdf = pd.DataFrame(rollup)
    rdf.to_csv(out_dir / "rollup.csv", index=False)
    print(f"Total time: {(time_mod.time() - t0)/60:.1f} min")
    print(f"Rollup: {out_dir / 'rollup.csv'}")

    # Print one-liner summary
    print()
    print("=" * 70)
    for r in rollup:
        print(f"  {r['family']:<35}  n={r['n']:>5}  cum_R={r['cum_r']:>9.2f}  "
              f"avg_R={r['avg_r']:>+.4f}  win={r['win_rate']*100:>4.1f}%")
    print("=" * 70)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
