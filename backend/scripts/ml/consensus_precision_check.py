"""Consensus-trade precision analysis.

Reads the portfolio_with_sweep predictions from 2025 and computes:
- precision of picks where EXACTLY 1 signal fired (single-signal trades)
- precision of picks where 2+ signals fired (consensus trades)
- per-pair consensus precision (which signal pairs produce the cleanest picks)

The hypothesis: consensus picks (2+ signals agreeing on same date+symbol)
should have higher precision than single-signal picks. If true, we have
a "consensus filter" knob to trade off precision vs trade frequency.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
IN_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_portfolio_with_sweep"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_consensus_precision"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    preds_path = IN_DIR / "all_signal_predictions_2025.csv"
    print(f"loading: {preds_path.name}")
    df = pd.read_csv(preds_path)
    print(f"  total rows: {len(df):,}")
    print(f"  signals: {df['signal_name'].unique()}")

    # Top-10% picks only.
    top = df[df["top_10pct"] == True].copy()
    print(f"  top-10% rows: {len(top):,}")
    if len(top) == 0:
        print("  no top-10% rows — bailing.")
        return 1

    # Build pivot: rows = (date, symbol), cols = signal_name, values = whether that signal had a top-10% pick.
    top["fire_key"] = top["fire_date"].astype(str) + " | " + top["symbol"].astype(str)
    pivot = top.pivot_table(index="fire_key", columns="signal_name",
                             values="top_10pct", aggfunc=lambda s: True, fill_value=False)
    pivot_y = top.pivot_table(index="fire_key", columns="signal_name",
                               values="y_true", aggfunc="max", fill_value=np.nan)
    pivot["n_signals"] = pivot.sum(axis=1)

    # Per consensus tier: pool the trades and compute aggregate precision.
    print("\n=== Precision by consensus tier (date+symbol opportunities) ===")
    print(f"{'n signals firing':<20} {'n unique combos':>18} {'avg precision':>14} {'trades-if-each-fires':>22}")
    print("-" * 80)
    rows = []
    for n_sigs, grp in pivot.groupby("n_signals"):
        n_combos = len(grp)
        # For each combo, get the precision across the signals that fired.
        # A combo with 2 signals firing has 2 underlying trades; each is a hit or miss separately.
        precisions = []
        trades_count = 0
        hits_count = 0
        for fire_key, row in grp.iterrows():
            for sig in pivot.columns:
                if sig == "n_signals":
                    continue
                if row[sig]:
                    trades_count += 1
                    # Look up y_true for this signal+fire_key from pivot_y.
                    if sig in pivot_y.columns and fire_key in pivot_y.index:
                        y = pivot_y.loc[fire_key, sig]
                        if pd.notna(y):
                            hits_count += int(y)
                            precisions.append(int(y))
        avg_prec = float(np.mean(precisions)) if precisions else float("nan")
        print(f"{int(n_sigs):<20} {n_combos:>18} {avg_prec:>14.3f} {trades_count:>22}")
        rows.append({
            "n_signals_firing": int(n_sigs),
            "n_unique_combos": n_combos,
            "n_underlying_trades": trades_count,
            "n_hits": hits_count,
            "avg_precision": avg_prec,
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_DIR / "precision_by_consensus_tier.csv", index=False, float_format="%.4f")

    # Pair-wise consensus precision: which 2-signal pairs produce the cleanest picks?
    print("\n=== Pair-wise consensus precision (when EXACTLY 2 signals fire on same date+symbol) ===")
    sigs = [c for c in pivot.columns if c != "n_signals"]
    pair_rows = []
    for i, a in enumerate(sigs):
        for j, b in enumerate(sigs):
            if i >= j:
                continue
            # Combos where exactly a AND b fire (regardless of others).
            mask = pivot[a] & pivot[b]
            # Of those, restrict to combos where exactly TWO signals total fired (clean pair).
            clean_pair = mask & (pivot["n_signals"] == 2)
            n_pair = int(clean_pair.sum())
            if n_pair == 0:
                continue
            # Compute hit rate: of the 2*n_pair underlying trades, how many were hits?
            pair_combos = pivot.loc[clean_pair].index
            hits = 0
            total = 0
            for fire_key in pair_combos:
                for sig in (a, b):
                    y = pivot_y.loc[fire_key, sig] if sig in pivot_y.columns else np.nan
                    if pd.notna(y):
                        hits += int(y)
                        total += 1
            prec = hits / total if total > 0 else float("nan")
            pair_rows.append({
                "signal_a": a, "signal_b": b,
                "n_pair_combos": n_pair,
                "n_trades": total, "n_hits": hits,
                "pair_precision": prec,
            })
    pair_df = pd.DataFrame(pair_rows).sort_values("n_pair_combos", ascending=False)
    pair_df.to_csv(OUT_DIR / "pair_consensus_precision.csv", index=False, float_format="%.4f")
    print(pair_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Single-signal precision per signal name (for comparison).
    print("\n=== Precision by signal for SINGLE-signal-only picks (n_signals == 1) ===")
    single_combos = pivot[pivot["n_signals"] == 1]
    single_rows = []
    for sig in sigs:
        mask = single_combos[sig]
        n_combo = int(mask.sum())
        if n_combo == 0:
            continue
        hits = 0
        total = 0
        for fire_key in single_combos.loc[mask].index:
            y = pivot_y.loc[fire_key, sig] if sig in pivot_y.columns else np.nan
            if pd.notna(y):
                hits += int(y)
                total += 1
        prec = hits / total if total > 0 else float("nan")
        single_rows.append({
            "signal": sig, "n_solo_combos": n_combo,
            "n_trades": total, "n_hits": hits,
            "solo_precision": prec,
        })
    single_df = pd.DataFrame(single_rows).sort_values("solo_precision", ascending=False)
    single_df.to_csv(OUT_DIR / "single_signal_precision.csv", index=False, float_format="%.4f")
    print(single_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    out = {
        "test_year": 2025,
        "per_tier": {int(r["n_signals_firing"]): {"n_combos": r["n_unique_combos"], "avg_precision": r["avg_precision"]} for r in rows},
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
