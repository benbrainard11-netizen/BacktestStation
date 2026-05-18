"""V20 — Locked walk-forward execution per lockfile.

Reads experiments/locked_walkforward_2026_05_17/lockfile.yaml and runs the
frozen v13-v19 deploy candidate against the two locked-holdout windows
(2018-2019 + 2026 YTD).

Per the lockfile, this is NOT a research script. It runs ONCE per window per
fill-model scenario. No retries unless documented bug exception. Results are
written to experiments/locked_walkforward_2026_05_17/results/.

Direction logic:
  - FVG strict, OB strict: side_aware natural
  - Swing reversed, Sweep reversed: side_aware REVERSED
  - Sweep additionally drops entry hours in {22, 23, 0, 1, 2, 3, 4, 5, 6}

For each of {2018-2019, 2026 YTD} x {4 families} x {3 fill models}:
  - simulate
  - record per-trade output
  - aggregate metrics
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import numpy as np
from scripts.ml.rigorous_backtest_v1 import BarsCache, Signal, SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP
from scripts.ml.v10_raw_ob_slippage import Slippage, simulate_v7_slip, resolve_dir


def all_events_picks_any_year(sig: Signal) -> pd.DataFrame:
    """Mirror of v9_ob_leak_audit.all_events_picks but WITHOUT the TEST_YEARS
    [2020-2025] hardcoded filter. Returns ALL events across all years.

    The locked walk-forward needs 2018-2019 + 2026 events; the upstream helper
    silently filters those out, which is the right default for the v13 audit
    but wrong for our explicit-window protocol.

    Year filtering happens downstream in filter_picks_to_window().
    """
    from scripts.ml.gpu_train_pipeline import filter_matrix
    from scripts.ml.gpu_train_schema_safe import load_schema, coerce_binary_label

    matrix_path = sig.anchors_dir / (sig.matrix_file + ".parquet")
    df = pd.read_parquet(matrix_path)
    df = filter_matrix(df, snapshot=sig.snapshot, side=sig.side, event_type="all")
    if sig.label not in df.columns:
        return pd.DataFrame()
    y_series = coerce_binary_label(df[sig.label])
    df = df.loc[y_series.notna()].copy()
    time_col = next((c for c in TIME_COL_CANDIDATES if c in df.columns), None)
    if time_col is None:
        return pd.DataFrame()
    df["fire_ts"] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
    df["symbol"] = df[SYMBOL_COL]
    df["anchor_side"] = df.get(SIDE_COL, "?")
    df["year"] = df["fire_ts"].dt.year
    # !! NO TEST_YEARS FILTER !! That's the whole point of this helper.
    # Dedup by (symbol, fire_ts, side) per the May 16 dedup correction.
    df = df.drop_duplicates(subset=["symbol", "fire_ts", "anchor_side"], keep="first")
    df["test_year"] = df["year"]
    df["signal_name"] = sig.name
    df["direction_rule"] = sig.direction_rule
    df["p_test"] = 0.5
    df["y_true"] = y_series.loc[df.index].astype(int).to_numpy()
    return df[["test_year", "signal_name", "fire_ts", "symbol", "anchor_side",
               "p_test", "y_true", "direction_rule"]].reset_index(drop=True)

ROOT = Path(r"C:\Users\benbr\BacktestStation")
LOCKFILE_PATH = ROOT / "experiments" / "locked_walkforward_2026_05_17" / "lockfile.yaml"
OUT_DIR = ROOT / "experiments" / "locked_walkforward_2026_05_17" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOWS = {
    "locked_holdout_1": (pd.Timestamp("2018-01-01", tz="UTC"),
                          pd.Timestamp("2019-12-31 19:55:00", tz="UTC")),  # purged 305-min boundary
    "locked_holdout_2": (pd.Timestamp("2026-01-01", tz="UTC"),
                          pd.Timestamp("2026-05-15 23:59:59", tz="UTC")),
}

SLIPPAGES = [
    Slippage("primary_2tick", entry_ticks=2.0, stop_ticks=2.0, time_exit_ticks=2.0),
    Slippage("stress_1tick", entry_ticks=1.0, stop_ticks=1.0, time_exit_ticks=1.0),
    Slippage("no_slippage"),
]

# Sweep hour filter (per lockfile)
SWEEP_DROP_HOURS = {22, 23, 0, 1, 2, 3, 4, 5, 6}


def build_signals_from_lockfile(lockfile: dict) -> list[dict]:
    """Convert lockfile family specs into our Signal + reverse_direction + hour_filter tuples."""
    out = []
    for fam in lockfile["candidate"]["families"]:
        anchors_path = Path(lockfile["data"]["anchor_matrices"][_family_key(fam["family"])])
        sig = Signal(
            name=fam["family"],
            anchors_dir=anchors_path.parent,
            matrix_file=anchors_path.stem,
            snapshot=fam["snapshot"],
            side=fam["side"],
            label=fam["label"],
            direction_rule=fam["direction_rule"],
        )
        out.append({
            "name": fam["family"],
            "signal": sig,
            "reverse": fam.get("direction_reversed", False),
            "hour_filter": fam.get("hour_filter"),
            "expected_avg_r_exploratory": fam.get("expected_avg_r_2020_2025"),
        })
    return out


def _family_key(family_name: str) -> str:
    return {
        "FVG strict": "fvg_strict",
        "OB strict": "ob_strict",
        "Swing reversed": "swing",
        "Sweep reversed (filtered)": "sweep",
    }[family_name]


def filter_picks_to_window(picks: pd.DataFrame, win_start: pd.Timestamp, win_end: pd.Timestamp) -> pd.DataFrame:
    if picks.empty:
        return picks
    p = picks.copy()
    p["fire_ts"] = pd.to_datetime(p["fire_ts"], utc=True, errors="coerce")
    mask = (p["fire_ts"] >= win_start) & (p["fire_ts"] <= win_end)
    return p[mask].copy()


def simulate_picks_with_hour_filter(
    picks: pd.DataFrame, bars: BarsCache, variant, slip, reverse: bool, hour_filter: dict | None,
) -> pd.DataFrame:
    picks = picks[picks["symbol"].isin(["NQ.c.0", "ES.c.0"])].copy()
    # Direction: side_aware, possibly reversed
    picks["natural_dir"] = picks["anchor_side"].apply(resolve_dir)
    if reverse:
        picks["direction"] = picks["natural_dir"].apply(lambda d: "long" if d == "short" else "short")
    else:
        picks["direction"] = picks["natural_dir"]

    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7_slip(bars, row["symbol"], row["fire_ts"], row["direction"], variant, slip)
        trades.append({
            "slippage": slip.name,
            "test_year": int(row["fire_ts"].year) if hasattr(row["fire_ts"], "year") else None,
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            **sim,
        })
    td = pd.DataFrame(trades)
    if td.empty:
        return td
    # Apply hour filter AFTER simulation (uses entry_ts which is post-confirmation)
    if hour_filter and hour_filter.get("type") == "drop_utc_hours":
        drop_hours = set(hour_filter["hours"])
        td["entry_hour_utc"] = pd.to_datetime(td["entry_ts"], utc=True, errors="coerce").dt.hour
        before = len(td)
        td = td[~td["entry_hour_utc"].isin(drop_hours)].copy()
        print(f"      hour-filter dropped {before-len(td)} of {before} trades")
    return td


def compute_stats(td: pd.DataFrame) -> dict:
    ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
    n = len(ex)
    if n == 0:
        return {"n": 0, "cum_r": 0.0, "avg_r": 0.0, "win_rate": 0.0,
                "max_dd_r": 0.0, "yrs_pos": 0, "per_year_cum_r": {},
                "per_symbol_cum_r": {}}
    cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum()
    per_year = ex.groupby("test_year")["pnl_r"].sum().to_dict()
    per_sym = ex.groupby("symbol")["pnl_r"].sum().to_dict()
    return {
        "n": n,
        "cum_r": float(ex["pnl_r"].sum()),
        "avg_r": float(ex["pnl_r"].mean()),
        "win_rate": float((ex["pnl_r"] > 0).mean()),
        "max_dd_r": float((cumr.cummax() - cumr).max()),
        "yrs_pos": int(sum(1 for v in per_year.values() if v > 0)),
        "per_year_cum_r": {int(k): float(v) for k, v in per_year.items()},
        "per_symbol_cum_r": {k: float(v) for k, v in per_sym.items()},
    }


def main() -> int:
    t0 = time_mod.time()
    print("=== V20 — Locked walk-forward execution ===")
    print(f"Lockfile: {LOCKFILE_PATH}")

    with open(LOCKFILE_PATH) as f:
        lockfile = yaml.safe_load(f)
    print(f"Protocol ID: {lockfile['protocol_id']}")
    print(f"Lock status: {lockfile['lock_status']}")
    if lockfile["lock_status"] != "active":
        print("ERROR: lock_status is not 'active'. Aborting.")
        return 1

    families = build_signals_from_lockfile(lockfile)
    print(f"\nLocked candidate: {len(families)} families")
    for fam in families:
        print(f"  - {fam['name']:<28}  reverse={fam['reverse']}  hour_filter={fam['hour_filter'] is not None}")

    bars = BarsCache()
    all_results = []

    for win_name, (win_start, win_end) in WINDOWS.items():
        print(f"\n{'='*70}")
        print(f"=== WINDOW: {win_name}  [{win_start} -> {win_end}] ===")
        print(f"{'='*70}")

        for fam in families:
            print(f"\n--- Family: {fam['name']} ---")
            # Get ALL events for this family (no window filter yet)
            all_picks = all_events_picks_any_year(fam["signal"])
            if all_picks.empty:
                print(f"  no events for {fam['name']}; skipping")
                continue
            # Filter to the locked window
            window_picks = filter_picks_to_window(all_picks, win_start, win_end)
            print(f"  events in window: {len(window_picks):,} (of {len(all_picks):,} total)")
            if window_picks.empty:
                print(f"  no events in window; skipping")
                continue

            for slip in SLIPPAGES:
                print(f"    [{slip.name}]", end=" ", flush=True)
                td = simulate_picks_with_hour_filter(
                    window_picks, bars, V8A_STOP, slip,
                    reverse=fam["reverse"], hour_filter=fam["hour_filter"],
                )
                stats = compute_stats(td)
                result = {
                    "window": win_name,
                    "family": fam["name"],
                    "slippage": slip.name,
                    "reverse": fam["reverse"],
                    "hour_filter": fam["hour_filter"] is not None,
                    **stats,
                    "expected_avg_r_exploratory": fam["expected_avg_r_exploratory"],
                }
                all_results.append(result)
                # Save per-family trades
                trades_path = OUT_DIR / f"trades_{win_name}_{fam['name'].replace(' ', '_').replace('(', '').replace(')', '')}_{slip.name}.csv"
                td.to_csv(trades_path, index=False, float_format="%.4f")
                print(f"n={stats['n']:5d}  cum_R={stats['cum_r']:+8.1f}  avg_R={stats['avg_r']:+5.3f}  win={stats['win_rate']:.3f}  DD={stats['max_dd_r']:5.1f}")

            # Save the rollup after each family (resumability)
            pd.DataFrame(all_results).to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")

    rollup = pd.DataFrame(all_results)
    rollup.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")

    elapsed = (time_mod.time() - t0) / 60
    summary = {
        "protocol_id": lockfile["protocol_id"],
        "code_commit_sha": lockfile["code"]["repo_commit_sha"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_min": round(elapsed, 1),
        "windows_run": list(WINDOWS.keys()),
        "n_families": len(families),
        "n_results": len(all_results),
    }
    (OUT_DIR / "execution_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Combined cum_R per window x slippage
    print(f"\n{'='*70}")
    print(f"=== HEADLINE: Combined cum_R per window x slippage ===")
    print(f"{'='*70}")
    pivot = rollup.pivot_table(
        index=["window", "slippage"],
        values="cum_r", aggfunc="sum",
    )
    print(pivot.to_string())

    print(f"\n=== DONE in {elapsed:.1f} min ===")
    print(f"  results: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
