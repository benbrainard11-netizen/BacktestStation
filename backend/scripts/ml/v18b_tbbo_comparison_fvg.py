"""V18b — TBBO comparison on FVG trades (v15's no_slippage scenario)."""

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
TRADES_CSV = ROOT / "experiments" / "backtests" / "2026-05-17_v15_fvg_zone_reaction_slippage" / "trades_all_slippage.csv"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-17_v18b_tbbo_fvg"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TBBO_COVERAGE_START = pd.Timestamp("2025-05-01", tz="UTC")
TBBO_COVERAGE_END = pd.Timestamp("2026-05-05 23:59:59", tz="UTC")


def main() -> int:
    print("=== V18b — TBBO comparison on FVG (v15) ===")
    t0 = time_mod.time()

    df = pd.read_csv(TRADES_CSV)
    # Pick no_slippage scenario for fair comparison to TBBO
    df = df[df["slippage"] == "no_slippage"].copy()
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True, errors="coerce")
    df["fire_ts"] = pd.to_datetime(df["fire_ts"], utc=True, errors="coerce")
    df = df[df["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    print(f"v15 FVG no_slippage trades: {len(df):,}")

    mask = (df["entry_ts"] >= TBBO_COVERAGE_START) & (df["entry_ts"] <= TBBO_COVERAGE_END)
    df_overlap = df[mask].copy()
    print(f"In TBBO coverage window: {len(df_overlap):,}")

    tbbo = TbboCache()
    results = []
    for i, row in enumerate(df_overlap.itertuples(index=False), 1):
        trade = row._asdict()
        if i % 500 == 0:
            print(f"  [{i}/{len(df_overlap)}]")
        resolved = resolve_trade(trade, tbbo)
        results.append({**trade, **resolved})

    out = pd.DataFrame(results)
    out.to_csv(OUT_DIR / "trades_paired.csv", index=False, float_format="%.4f")

    n_skipped = (out["exit_reason_tbbo"] == "skip").sum()
    valid = out[out["exit_reason_tbbo"] != "skip"].copy()
    cum_1m = valid["pnl_r"].sum()
    cum_tbbo = valid["pnl_r_tbbo"].sum()

    print(f"\nSkipped: {n_skipped}  Resolved: {len(valid)}")
    print(f"\n=== Cum_R comparison ===")
    print(f"  1m simulator:  {cum_1m:+8.1f}")
    print(f"  TBBO resolver: {cum_tbbo:+8.1f}")
    if cum_1m != 0:
        print(f"  Discount factor: {cum_tbbo/cum_1m:.3f}")

    valid["agree_reason"] = valid["exit_reason"] == valid["exit_reason_tbbo"]
    print(f"\nAgreement: {valid['agree_reason'].mean():.3f}")
    print("\n=== Exit reason cross-tab ===")
    print(valid.groupby(["exit_reason", "exit_reason_tbbo"]).size().to_string())

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
