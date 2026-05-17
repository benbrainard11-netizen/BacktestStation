"""V18 — Compare 1m simulator output to TBBO-resolved output on overlapping year.

Reads v16's trades.csv (Sweep reversed), filters to TBBO-covered period
(2025-05-01 onward), resolves each trade using the TBBO tape, writes paired
output with discount factor.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.tbbo_resolver import TbboCache, resolve_trade

ROOT = Path(r"C:\Users\benbr\BacktestStation")
TRADES_CSV = ROOT / "experiments" / "backtests" / "2026-05-17_v16_sweep_reversed_verify" / "trades.csv"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-17_v18_tbbo_comparison"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TBBO_COVERAGE_START = pd.Timestamp("2025-05-01", tz="UTC")
TBBO_COVERAGE_END = pd.Timestamp("2026-05-05 23:59:59", tz="UTC")


def main() -> int:
    print("=== V18 — 1m vs TBBO trade comparison ===")
    t0 = time_mod.time()

    df = pd.read_csv(TRADES_CSV)
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True, errors="coerce")
    df["fire_ts"] = pd.to_datetime(df["fire_ts"], utc=True, errors="coerce")
    df = df[df["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    print(f"Total v16 trades (after exit_reason filter): {len(df):,}")

    # Filter to TBBO window
    mask = (df["entry_ts"] >= TBBO_COVERAGE_START) & (df["entry_ts"] <= TBBO_COVERAGE_END)
    df_overlap = df[mask].copy()
    print(f"In TBBO coverage window: {len(df_overlap):,}")

    tbbo = TbboCache()
    results = []
    for i, row in enumerate(df_overlap.itertuples(index=False), 1):
        trade = row._asdict()
        if i % 200 == 0 or i <= 5:
            print(f"  [{i}/{len(df_overlap)}] {trade['symbol']} {trade['direction']} fire={trade['fire_ts']}")
        resolved = resolve_trade(trade, tbbo)
        results.append({**trade, **resolved})

    out = pd.DataFrame(results)
    out.to_csv(OUT_DIR / "trades_paired.csv", index=False, float_format="%.4f")

    # Analysis
    print()
    n_skipped = (out["exit_reason_tbbo"] == "skip").sum()
    valid = out[out["exit_reason_tbbo"] != "skip"].copy()
    print(f"Skipped (no TBBO data / missing fields): {n_skipped}")
    print(f"Resolved: {len(valid)}")
    print()

    # Cum_R comparison
    cum_1m = valid["pnl_r"].sum()
    cum_tbbo = valid["pnl_r_tbbo"].sum()
    print(f"=== Cum_R comparison (overlap window) ===")
    print(f"  1m simulator:  {cum_1m:+8.1f}")
    print(f"  TBBO resolver: {cum_tbbo:+8.1f}")
    if cum_1m != 0:
        discount = cum_tbbo / cum_1m
        print(f"  Discount factor: {discount:.3f}  ({100*discount:.1f}% of 1m cum_R)")

    # Exit reason agreement
    valid["agree_reason"] = valid["exit_reason"] == valid["exit_reason_tbbo"]
    print(f"\n=== Exit reason agreement ===")
    print(valid.groupby(["exit_reason", "exit_reason_tbbo"]).size().to_string())

    # Average pnl_r delta per exit reason
    valid["pnl_r_delta"] = valid["pnl_r_tbbo"] - valid["pnl_r"]
    print(f"\n=== Per-original-exit-reason: avg pnl_r delta (TBBO - 1m) ===")
    print(valid.groupby("exit_reason")["pnl_r_delta"].agg(["count", "mean", "median"]).to_string())

    # Entry price slippage
    valid["entry_slip"] = valid["entry_price_tbbo"] - valid["entry_price"]
    print(f"\n=== Entry price slippage (TBBO entry - 1m entry, positive = paid more for longs) ===")
    print(valid.groupby("direction")["entry_slip"].agg(["count", "mean", "median", "std"]).to_string())

    summary = {
        "n_overlap": int(len(df_overlap)),
        "n_resolved": int(len(valid)),
        "n_skipped": int(n_skipped),
        "cum_r_1m": float(cum_1m),
        "cum_r_tbbo": float(cum_tbbo),
        "discount_factor": float(cum_tbbo / cum_1m) if cum_1m != 0 else None,
        "agree_rate": float(valid["agree_reason"].mean()),
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
