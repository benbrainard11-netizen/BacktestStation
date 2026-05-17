"""V14 — Type B audit on the unified all_level_reactions schema.

Supersedes v13 (which audited the legacy label registry). The level-reactions
parquet has one row per level event with a canonical `level.direction`, so we
can sim trades directly without anchor-matrix mapping or label-AUC pre-filter.

For each (level.kind, level.subtype, level.side) slice:
  B_natural   : trade level.direction at level.created_ts_utc, v8a rules
  B_reversed  : trade opposite direction, v8a rules
  D_natural   : random 10% of events, level.direction

NQ+ES only (matches v13 / v8a / May 16 deploy comparability).

Same classifier as v13: type_b if winning_cum_r >= 200, winning_avg_r >= 0.05,
winning_yrs_pos >= 5.

Output: experiments/backtests/2026-05-17_v14_level_reactions_audit/
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import BarsCache, TEST_YEARS
from scripts.ml.rigorous_backtest_v7_stops import StopVariant, simulate_v7
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
LEVELS_PATH = ROOT / "data" / "ml" / "levels" / "all_level_reactions.parquet"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-17_v14_level_reactions_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TRADE_SYMBOLS = ["NQ.c.0", "ES.c.0"]
MIN_TRADES = 100  # skip slices with fewer than this on NQ+ES (test years)
TYPE_B_MIN_CUM_R = 200.0
TYPE_B_MIN_AVG_R = 0.05
TYPE_B_MIN_YRS_POS = 5


def direction_to_trade(level_dir: str, reverse: bool) -> str:
    """Map level.direction to trade direction."""
    natural = "short" if level_dir in ("bearish", "gap_down") else "long"
    if reverse:
        return "long" if natural == "short" else "short"
    return natural


def simulate_slice(slice_df: pd.DataFrame, bars: BarsCache,
                   variant: StopVariant, reverse: bool, label: str) -> pd.DataFrame:
    """Simulate v8a trades for every row in slice_df."""
    trades = []
    for _, row in slice_df.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        direction = direction_to_trade(row["level.direction"], reverse=reverse)
        sim = simulate_v7(bars, row["level.symbol"], row["fire_ts"], direction, variant)
        trades.append({
            "variant": label,
            "test_year": int(row["year"]),
            "symbol": row["level.symbol"],
            "level_direction": row["level.direction"],
            "trade_direction": direction,
            "fire_ts": row["fire_ts"],
            **sim,
        })
    return pd.DataFrame(trades)


def _stats(td: pd.DataFrame) -> dict:
    ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
    n = len(ex)
    if n == 0:
        return {"n": 0, "cum_r": 0.0, "avg_r": 0.0, "win_rate": 0.0,
                "max_dd_r": 0.0, "years_positive": 0}
    cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum()
    return {
        "n": n,
        "cum_r": float(ex["pnl_r"].sum()),
        "avg_r": float(ex["pnl_r"].mean()),
        "win_rate": float((ex["pnl_r"] > 0).mean()),
        "max_dd_r": float((cumr.cummax() - cumr).max()),
        "years_positive": int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()),
    }


def audit_slice(slice_df: pd.DataFrame, bars: BarsCache, variant: StopVariant) -> dict:
    """B_natural + B_reversed + D_natural on one slice."""
    n_events = len(slice_df)
    if n_events == 0:
        return {"n_events": 0, "skip_reason": "no_events"}

    td_nat = simulate_slice(slice_df, bars, variant, reverse=False, label="B_natural")
    td_rev = simulate_slice(slice_df, bars, variant, reverse=True, label="B_reversed")

    rng = np.random.default_rng(42)
    keep_n = max(1, int(round(n_events * 0.10)))
    random_idx = rng.choice(slice_df.index.to_numpy(), size=keep_n, replace=False)
    random_slice = slice_df.loc[random_idx]
    td_d = simulate_slice(random_slice, bars, variant, reverse=False, label="D_natural")

    s_nat = _stats(td_nat); s_rev = _stats(td_rev); s_d = _stats(td_d)
    return {
        "n_events": int(n_events),
        "B_nat_n": s_nat["n"], "B_nat_cum_r": s_nat["cum_r"], "B_nat_avg_r": s_nat["avg_r"],
        "B_nat_win": s_nat["win_rate"], "B_nat_dd": s_nat["max_dd_r"],
        "B_nat_yrs_pos": s_nat["years_positive"],
        "B_rev_n": s_rev["n"], "B_rev_cum_r": s_rev["cum_r"], "B_rev_avg_r": s_rev["avg_r"],
        "B_rev_win": s_rev["win_rate"], "B_rev_dd": s_rev["max_dd_r"],
        "B_rev_yrs_pos": s_rev["years_positive"],
        "D_n": s_d["n"], "D_cum_r": s_d["cum_r"], "D_avg_r": s_d["avg_r"],
    }


def classify(row: dict) -> dict:
    if row.get("skip_reason"):
        return {"winning_dir": None, "winning_cum_r": 0.0, "is_type_b": False}
    nat_cum, rev_cum = row["B_nat_cum_r"], row["B_rev_cum_r"]
    if nat_cum >= rev_cum:
        win_dir = "natural"; win_cum = nat_cum; win_avg = row["B_nat_avg_r"]; win_yrs = row["B_nat_yrs_pos"]
        d_cum = row["D_cum_r"]
    else:
        win_dir = "reversed"; win_cum = rev_cum; win_avg = row["B_rev_avg_r"]; win_yrs = row["B_rev_yrs_pos"]
        d_cum = -row["D_cum_r"]
    is_type_b = (
        win_cum >= TYPE_B_MIN_CUM_R
        and win_avg >= TYPE_B_MIN_AVG_R
        and win_yrs >= TYPE_B_MIN_YRS_POS
    )
    return {
        "winning_dir": win_dir, "winning_cum_r": win_cum, "winning_avg_r": win_avg,
        "winning_yrs_pos": win_yrs, "D_cum_r_aligned": d_cum, "is_type_b": is_type_b,
    }


def main() -> int:
    t0 = time_mod.time()
    print(f"=== V14 level-reactions audit ===")
    print(f"output: {OUT_DIR}")

    df = pd.read_parquet(LEVELS_PATH)
    df = df[df["level.symbol"].isin(TRADE_SYMBOLS)].copy()
    df["fire_ts"] = pd.to_datetime(df["level.created_ts_utc"], utc=True, errors="coerce")
    df["year"] = df["fire_ts"].dt.year
    df = df[df["year"].isin(TEST_YEARS)].copy()
    print(f"  filtered to NQ+ES, test years {TEST_YEARS}: {len(df):,} rows")

    # Slice by (kind, subtype, side)
    slice_keys = df.groupby(["level.kind", "level.subtype", "level.side"]).size().reset_index(name="n")
    slice_keys = slice_keys.sort_values("n", ascending=False).reset_index(drop=True)
    print(f"  {len(slice_keys)} distinct slices; {sum(slice_keys['n'] >= MIN_TRADES)} have n >= {MIN_TRADES}")
    print()

    bars = BarsCache()
    results = []
    for i, sk in slice_keys.iterrows():
        kind, subtype, side, n = sk["level.kind"], sk["level.subtype"], sk["level.side"], int(sk["n"])
        if n < MIN_TRADES:
            results.append({"kind": kind, "subtype": subtype, "side": side,
                            "n_events": n, "skip_reason": f"n<{MIN_TRADES}"})
            continue

        print(f"[{i+1}/{len(slice_keys)}] {kind:<15} {subtype:<20} side={side:<8} n={n:>6}")
        slice_df = df[(df["level.kind"] == kind) & (df["level.subtype"] == subtype)
                      & (df["level.side"] == side)].copy()

        try:
            audit = audit_slice(slice_df, bars, V8A_STOP)
        except Exception as exc:
            print(f"  ERROR {type(exc).__name__}: {exc}")
            results.append({"kind": kind, "subtype": subtype, "side": side,
                            "skip_reason": f"err:{type(exc).__name__}"})
            continue

        cls = classify(audit)
        out = {"kind": kind, "subtype": subtype, "side": side, **audit, **cls}
        results.append(out)
        flag = " *** TYPE B ***" if cls["is_type_b"] else ""
        print(f"  B_nat={audit['B_nat_cum_r']:+8.1f}R ({audit['B_nat_avg_r']:+5.3f}avg)  "
              f"B_rev={audit['B_rev_cum_r']:+8.1f}R  "
              f"D={audit['D_cum_r']:+7.1f}R  dir={cls['winning_dir']}{flag}")

        if (i+1) % 5 == 0:
            pd.DataFrame(results).to_csv(OUT_DIR / "per_slice_rollup.csv", index=False, float_format="%.4f")

    rollup = pd.DataFrame(results)
    rollup.to_csv(OUT_DIR / "per_slice_rollup.csv", index=False, float_format="%.4f")
    type_b = rollup[rollup.get("is_type_b") == True].sort_values("winning_cum_r", ascending=False)
    type_b.to_csv(OUT_DIR / "type_b_slices.csv", index=False, float_format="%.4f")

    elapsed = (time_mod.time() - t0) / 60
    summary = {
        "total_slices": len(slice_keys),
        "audited": int(sum(1 for r in results if not r.get("skip_reason"))),
        "type_b_count": int(len(type_b)),
        "top_type_b": [
            {"kind": r["kind"], "subtype": r["subtype"], "side": r["side"],
             "dir": r["winning_dir"], "cum_r": round(r["winning_cum_r"], 1),
             "avg_r": round(r["winning_avg_r"], 3), "yrs": int(r["winning_yrs_pos"])}
            for _, r in type_b.head(20).iterrows()
        ],
        "elapsed_min": round(elapsed, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {elapsed:.1f} min ===")
    print(f"  Type B slices: {summary['type_b_count']} / {summary['audited']}")
    if not type_b.empty:
        print("\nTop 10:")
        for _, r in type_b.head(10).iterrows():
            print(f"  {r['kind']:<15} {r['subtype']:<20} side={r['side']:<8} dir={r['winning_dir']:<8} "
                  f"cum_R={r['winning_cum_r']:+8.1f}  yrs={int(r['winning_yrs_pos'])}/6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
