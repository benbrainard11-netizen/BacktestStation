"""V19 — Re-implement label.strict.next_60m.ob_broken_through_continuation
from raw 1m bars and compare to 247's column.

For each OB event:
  - Pull 1m bars from anchor.bar_end_utc to bar_end_utc + 60 min
  - For BULLISH OB: did any 1m bar's CLOSE go below range_far (= range_bottom)?
    (= "OB broken through to the downside" = bullish OB failed)
  - For BEARISH OB: did any 1m bar's CLOSE go above range_far (= range_top)?

Compare to 247's `label.strict.next_60m.ob_broken_through_continuation`.
Report agreement rate.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import BarsCache

ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_16_strict_order_block") / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-17_v19_strict_label_recompute"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_N = 500  # random sample to keep runtime small
TRADE_SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]


def recompute_one(row, bars: BarsCache) -> int | None:
    """Return 1 if OB broken through within 60m, 0 if not, None if can't compute."""
    sym = row["anchor.primary_symbol"]
    if sym not in TRADE_SYMBOLS:
        return None  # only have bars for these
    side = row["anchor.side"]
    bar_end = pd.to_datetime(row["anchor.bar_end_utc"], utc=True)
    range_far = float(row["label.ob_levels.range_far"])

    window_end = bar_end + pd.Timedelta(minutes=60)
    # Use bars strictly AFTER bar_end (next 60 min)
    bars_window = bars.get_window(sym, bar_end, window_end)
    if bars_window.empty:
        return None
    # Look at closes strictly after bar_end
    bars_window = bars_window.loc[bars_window.index > bar_end]
    if bars_window.empty:
        return None

    if side == "bullish":
        # Bullish OB: range_far is below body. Broken through = some close < range_far
        return int((bars_window["close"] < range_far).any())
    elif side == "bearish":
        # Bearish OB: range_far is above body. Broken through = some close > range_far
        return int((bars_window["close"] > range_far).any())
    return None


def main() -> int:
    print("=== V19 — strict label recompute ===")
    p = ANCHORS / "ob_snapshots_xctx_strict.parquet"
    df = pd.read_parquet(p)
    print(f"Total OB events: {len(df):,}")

    # Filter to trade symbols + non-null target label
    df = df[df["anchor.primary_symbol"].isin(TRADE_SYMBOLS)].copy()
    df = df[df["label.strict.next_60m.ob_broken_through_continuation"].notna()].copy()
    df["anchor.bar_end_utc"] = pd.to_datetime(df["anchor.bar_end_utc"], utc=True)
    print(f"After filter (NQ/ES/YM only): {len(df):,}")

    # Random sample
    sample = df.sample(n=min(SAMPLE_N, len(df)), random_state=42).copy()
    print(f"Sampling {len(sample)} events for recompute")

    bars = BarsCache()
    results = []
    for i, (_, row) in enumerate(sample.iterrows(), 1):
        row_dict = row.to_dict()
        my_label = recompute_one(row_dict, bars)
        their_label = int(row_dict["label.strict.next_60m.ob_broken_through_continuation"])
        results.append({
            "fire_ts": row_dict["anchor.bar_end_utc"],
            "symbol": row_dict["anchor.primary_symbol"],
            "side": row_dict["anchor.side"],
            "range_far": float(row_dict["label.ob_levels.range_far"]),
            "their_label": their_label,
            "my_label": my_label,
            "agree": (my_label == their_label) if my_label is not None else None,
        })
        if i % 100 == 0:
            print(f"  {i}/{len(sample)}")

    out = pd.DataFrame(results)
    out.to_csv(OUT_DIR / "comparison.csv", index=False)

    n_resolved = out["my_label"].notna().sum()
    n_agree = out["agree"].sum() if n_resolved else 0
    print(f"\n=== Comparison results ===")
    print(f"  Sample size: {len(sample)}")
    print(f"  Resolved (had bar data): {n_resolved}")
    print(f"  Agreement: {n_agree}/{n_resolved} = {100*n_agree/n_resolved:.1f}%" if n_resolved else "no data")
    print()
    print("=== Confusion matrix (my vs theirs) ===")
    resolved = out.dropna(subset=["my_label"])
    if not resolved.empty:
        ct = pd.crosstab(resolved["my_label"], resolved["their_label"], margins=True)
        print(ct)
        # Disagreement examples
        print("\n=== Disagreement examples ===")
        disagrees = resolved[resolved["agree"] == False]
        print(f"Total disagreements: {len(disagrees)}")
        if not disagrees.empty:
            print("\nMy=0 but theirs=1 (I missed a True):")
            mn = disagrees[(disagrees["my_label"] == 0) & (disagrees["their_label"] == 1)]
            print(mn.head(5).to_string(index=False))
            print(f"\nMy=1 but theirs=0 (I called True but they said False):")
            mp = disagrees[(disagrees["my_label"] == 1) & (disagrees["their_label"] == 0)]
            print(mp.head(5).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
