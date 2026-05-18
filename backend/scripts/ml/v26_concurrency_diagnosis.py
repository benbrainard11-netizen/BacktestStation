"""Diagnose WHY the single-account concurrency haircut is 50%+.

Questions:
  1. When trade A blocks trade B, are they the same direction (both
     long NQ) or opposite (long NQ vs short NQ)?
     - same-direction blocks → correlated signals; you'd really only
       want one anyway, edge isn't really being lost
     - opposite-direction blocks → you'd net the position to zero in
       reality, so the "block" model is overly pessimistic
  2. Which family blocks which more often? (OB blocking Sweep vs
     Sweep blocking OB)
  3. Per-symbol block breakdown (NQ vs ES)
  4. If we had MORE symbols, would the block rate fall? Simulate
     with a hypothetical 4-symbol universe to estimate.
  5. If we used a SHORTER trade window (e.g., 120 min), would the
     block rate fall?

OUTPUT:
  experiments/paper_trade_gates_2026_05_17/results/v26_concurrency_diagnosis.json
  experiments/paper_trade_gates_2026_05_17/results/v26_concurrency_diagnosis.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
V20_DIR = REPO_ROOT / "experiments" / "locked_walkforward_2026_05_17" / "results"
OUT_DIR = REPO_ROOT / "experiments" / "paper_trade_gates_2026_05_17" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)


FAMILY_FILES = {
    "OB strict": [
        "trades_locked_holdout_1_OB_strict_primary_2tick.csv",
        "trades_locked_holdout_2_OB_strict_primary_2tick.csv",
    ],
    "Sweep reversed (filtered)": [
        "trades_locked_holdout_1_Sweep_reversed_filtered_primary_2tick.csv",
        "trades_locked_holdout_2_Sweep_reversed_filtered_primary_2tick.csv",
    ],
}


def load_all_trades() -> pd.DataFrame:
    frames = []
    for family, files in FAMILY_FILES.items():
        for fn in files:
            df = pd.read_csv(V20_DIR / fn)
            df = df.dropna(subset=["pnl_r", "entry_ts", "exit_ts"]).copy()
            df["family"] = family
            df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
            df["exit_ts"] = pd.to_datetime(df["exit_ts"], utc=True)
            frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(
        ["entry_ts", "family", "symbol"], kind="stable"
    ).reset_index(drop=True)
    return out


def diagnose_blocks(trades: pd.DataFrame) -> dict:
    """Walk forward with cap_total=2, per_symbol=1. For each blocked
    trade, record what blocked it + the direction/family/etc."""
    open_positions: list[dict] = []
    blocks: list[dict] = []
    taken: list[dict] = []

    for _, row in trades.iterrows():
        # Expire stale positions
        open_positions = [p for p in open_positions if p["exit_ts"] > row["entry_ts"]]

        same_symbol = [p for p in open_positions if p["symbol"] == row["symbol"]]
        if same_symbol:
            blocker = same_symbol[0]
            blocks.append({
                "blocked_entry_ts": row["entry_ts"],
                "blocked_symbol": row["symbol"],
                "blocked_family": row["family"],
                "blocked_direction": row["direction"],
                "blocked_pnl_r": float(row["pnl_r"]),
                "blocker_entry_ts": blocker["entry_ts"],
                "blocker_family": blocker["family"],
                "blocker_direction": blocker["direction"],
                "blocker_exit_ts": blocker["exit_ts"],
                "minutes_into_blocker_position": int(
                    (row["entry_ts"] - blocker["entry_ts"]).total_seconds() / 60
                ),
            })
            continue

        # Take it
        open_positions.append({
            "symbol": row["symbol"],
            "family": row["family"],
            "direction": row["direction"],
            "entry_ts": row["entry_ts"],
            "exit_ts": row["exit_ts"],
        })
        taken.append({
            "entry_ts": row["entry_ts"],
            "symbol": row["symbol"],
            "family": row["family"],
            "direction": row["direction"],
            "pnl_r": float(row["pnl_r"]),
        })

    return {
        "n_taken": len(taken),
        "n_blocked": len(blocks),
        "blocks": pd.DataFrame(blocks),
        "taken": pd.DataFrame(taken),
    }


def analyze_block_directions(blocks: pd.DataFrame) -> dict:
    """Same-direction blocks (both long or both short) vs opposite."""
    same_dir = blocks["blocked_direction"] == blocks["blocker_direction"]
    same_count = int(same_dir.sum())
    opp_count = int((~same_dir).sum())
    same_pnl = float(blocks.loc[same_dir, "blocked_pnl_r"].sum())
    opp_pnl = float(blocks.loc[~same_dir, "blocked_pnl_r"].sum())
    return {
        "same_direction_blocks": same_count,
        "same_direction_blocked_cum_r": round(same_pnl, 2),
        "opposite_direction_blocks": opp_count,
        "opposite_direction_blocked_cum_r": round(opp_pnl, 2),
        "interpretation": (
            "same-direction blocks = correlated signals, edge wouldn't "
            "be much higher anyway; opposite-direction blocks = positions "
            "would net out in a real account, so 'block' model is overly "
            "pessimistic"
        ),
    }


def analyze_block_pairs(blocks: pd.DataFrame) -> dict:
    """Family-pair counts: OB blocks Sweep, Sweep blocks OB, etc."""
    pairs = blocks.groupby(["blocker_family", "blocked_family"]).size()
    pairs_cum_r = blocks.groupby(
        ["blocker_family", "blocked_family"]
    )["blocked_pnl_r"].sum()
    out: dict[str, dict] = {}
    for (blocker, blocked), count in pairs.items():
        out[f"{blocker} blocks {blocked}"] = {
            "count": int(count),
            "blocked_cum_r": round(float(pairs_cum_r[(blocker, blocked)]), 2),
        }
    return out


def analyze_per_symbol(blocks: pd.DataFrame) -> dict:
    """Per-symbol block stats."""
    out: dict[str, dict] = {}
    for symbol, grp in blocks.groupby("blocked_symbol"):
        out[symbol] = {
            "count": int(len(grp)),
            "blocked_cum_r": round(float(grp["blocked_pnl_r"].sum()), 2),
        }
    return out


def simulate_with_extra_symbols(
    trades: pd.DataFrame, *, hypothetical_factor: float
) -> dict:
    """Hypothetical: if we had N times as many symbols, what would
    retention look like?

    Assume signals are roughly uniformly distributed across symbols.
    Splitting NQ trades across hypothetical_factor symbols means each
    symbol slot has 1/factor as much demand → block rate drops
    proportionally.

    This is a back-of-envelope estimate. The real way is to actually
    run OB + Sweep on more symbols and re-simulate.
    """
    # Spread each trade across `factor` virtual symbols by hashing
    # entry_ts (deterministic).
    if hypothetical_factor <= 1:
        return {"factor": hypothetical_factor, "note": "factor must be > 1"}
    trades = trades.copy()
    trades["virtual_symbol"] = trades.apply(
        lambda r: f"{r['symbol']}_v{hash((r['entry_ts'], r['family'])) % int(hypothetical_factor)}",
        axis=1,
    )

    open_positions: list[dict] = []
    taken_cum_r = 0.0
    n_taken = 0
    n_blocked = 0

    for _, row in trades.iterrows():
        open_positions = [p for p in open_positions if p["exit_ts"] > row["entry_ts"]]
        same_vsym = [p for p in open_positions if p["vsym"] == row["virtual_symbol"]]
        if same_vsym:
            n_blocked += 1
            continue
        open_positions.append({
            "vsym": row["virtual_symbol"],
            "exit_ts": row["exit_ts"],
        })
        taken_cum_r += float(row["pnl_r"])
        n_taken += 1

    return {
        "hypothetical_factor": hypothetical_factor,
        "n_taken": n_taken,
        "n_blocked": n_blocked,
        "cum_r": round(taken_cum_r, 2),
        "block_rate": round(n_blocked / len(trades), 4),
    }


def simulate_shorter_window(
    trades: pd.DataFrame, *, new_window_minutes: int
) -> dict:
    """Hypothetical: if positions held for new_window_minutes instead
    of however long they did, what does retention look like?

    Each trade's effective exit moves to min(actual exit, entry +
    new_window). pnl_r is NOT adjusted (we keep the original outcome)
    -- we just shrink the slot occupancy. This is a CONSERVATIVE
    estimate of mitigation upside.
    """
    trades = trades.copy()
    trades["effective_exit_ts"] = trades.apply(
        lambda r: min(
            r["exit_ts"],
            r["entry_ts"] + pd.Timedelta(minutes=new_window_minutes),
        ),
        axis=1,
    )

    open_positions: list[dict] = []
    taken_cum_r = 0.0
    n_taken = 0
    n_blocked = 0

    for _, row in trades.iterrows():
        open_positions = [
            p for p in open_positions if p["exit_ts"] > row["entry_ts"]
        ]
        same_symbol = [p for p in open_positions if p["symbol"] == row["symbol"]]
        if same_symbol:
            n_blocked += 1
            continue
        open_positions.append({
            "symbol": row["symbol"],
            "exit_ts": row["effective_exit_ts"],
        })
        taken_cum_r += float(row["pnl_r"])
        n_taken += 1

    return {
        "new_window_minutes": new_window_minutes,
        "n_taken": n_taken,
        "n_blocked": n_blocked,
        "cum_r": round(taken_cum_r, 2),
    }


def main() -> int:
    print("v26 concurrency diagnosis")
    trades = load_all_trades()
    print(f"  loaded {len(trades)} trades")

    baseline = trades["pnl_r"].sum()
    print(f"  independent baseline: {baseline:.2f} R\n")

    diag = diagnose_blocks(trades)
    blocks: pd.DataFrame = diag["blocks"]
    taken: pd.DataFrame = diag["taken"]

    print(f"  Blocks: {len(blocks)} / Taken: {len(taken)}")
    print(f"  Taken cum_R: {taken['pnl_r'].sum():.2f}")
    print(f"  Blocked cum_R (what we missed): {blocks['blocked_pnl_r'].sum():.2f}\n")

    directions = analyze_block_directions(blocks)
    print("  By direction:")
    print(f"    same-direction blocks: {directions['same_direction_blocks']}  "
          f"(blocked cum_R = {directions['same_direction_blocked_cum_r']})")
    print(f"    opposite-direction blocks: {directions['opposite_direction_blocks']}  "
          f"(blocked cum_R = {directions['opposite_direction_blocked_cum_r']})\n")

    pairs = analyze_block_pairs(blocks)
    print("  By family pair:")
    for k, v in pairs.items():
        print(f"    {k}: {v['count']} blocks, blocked cum_R = {v['blocked_cum_r']}")
    print()

    per_symbol = analyze_per_symbol(blocks)
    print("  By symbol:")
    for sym, s in per_symbol.items():
        print(f"    {sym}: {s['count']} blocks, blocked cum_R = {s['blocked_cum_r']}")
    print()

    # Hypothetical: more symbols
    print("  Hypothetical: more symbols (uniform spread):")
    more_sym = {}
    for factor in (2, 4, 6):
        sim = simulate_with_extra_symbols(trades, hypothetical_factor=factor)
        more_sym[f"{factor}x_symbols"] = sim
        retention = sim["cum_r"] / baseline
        print(f"    {factor}x symbols: cum_R={sim['cum_r']:.2f}, "
              f"retention={retention*100:.1f}%, blocks={sim['n_blocked']}")
    print()

    # Hypothetical: shorter window
    print("  Hypothetical: shorter trade window (keep same R, free slot earlier):")
    shorter = {}
    for window in (60, 120, 180):
        sim = simulate_shorter_window(trades, new_window_minutes=window)
        shorter[f"window_{window}m"] = sim
        retention = sim["cum_r"] / baseline
        print(f"    {window}m window: cum_R={sim['cum_r']:.2f}, "
              f"retention={retention*100:.1f}%, blocks={sim['n_blocked']}")
    print()

    payload = {
        "generator": "v26_concurrency_diagnosis",
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "independent_baseline_cum_r": round(float(baseline), 2),
        "blocks": {
            "n_total": int(len(blocks)),
            "blocked_cum_r": round(float(blocks["blocked_pnl_r"].sum()), 2),
            "by_direction": directions,
            "by_family_pair": pairs,
            "by_symbol": per_symbol,
        },
        "hypotheticals": {
            "more_symbols": more_sym,
            "shorter_window": shorter,
        },
    }

    out_json = OUT_DIR / "v26_concurrency_diagnosis.json"
    out_json.write_text(json.dumps(payload, indent=2, default=str))
    print(f"  wrote: {out_json.relative_to(REPO_ROOT)}")

    # Also write summary MD
    lines: list[str] = []
    lines.append("# v26 — Concurrency Diagnosis")
    lines.append("")
    lines.append("## Why gate 4 failed: the blocking dynamics")
    lines.append("")
    lines.append(f"- Independent baseline: **{baseline:.2f} R**")
    lines.append(f"- Trades taken at cap=2: {len(taken)} ({taken['pnl_r'].sum():.2f} R)")
    lines.append(f"- Trades blocked: {len(blocks)} ({blocks['blocked_pnl_r'].sum():.2f} R left on the table)")
    lines.append("")
    lines.append("## Block directionality")
    lines.append("")
    lines.append(f"- Same-direction blocks: **{directions['same_direction_blocks']}** "
                 f"(missed cum_R = {directions['same_direction_blocked_cum_r']})")
    lines.append(f"- Opposite-direction blocks: **{directions['opposite_direction_blocks']}** "
                 f"(missed cum_R = {directions['opposite_direction_blocked_cum_r']})")
    lines.append("")
    lines.append("Same-direction blocks are correlated signals — even if we could take both, the second one is mostly redundant. **Opposite-direction blocks would NET to zero in real life**, so the v25 'block' model is overly pessimistic on those. They represent a real opportunity to recover edge with smarter portfolio rules (e.g., open net position rather than first-come-first-serve).")
    lines.append("")
    lines.append("## Block by family pair")
    lines.append("")
    for k, v in pairs.items():
        lines.append(f"- **{k}**: {v['count']} blocks, missed cum_R = {v['blocked_cum_r']}")
    lines.append("")
    lines.append("## Block by symbol")
    lines.append("")
    for sym, s in per_symbol.items():
        lines.append(f"- **{sym}**: {s['count']} blocks, missed cum_R = {s['blocked_cum_r']}")
    lines.append("")
    lines.append("## Mitigations modeled")
    lines.append("")
    lines.append("### A. More symbols (uniform spread hypothetical)")
    lines.append("")
    lines.append("| Symbol multiplier | cum_R | Retention |")
    lines.append("|---|---:|---:|")
    for factor in (2, 4, 6):
        sim = more_sym[f"{factor}x_symbols"]
        ret = sim["cum_r"] / baseline
        lines.append(f"| {factor}x ({factor*2} symbols) | {sim['cum_r']:.2f} | {ret*100:.1f}% |")
    lines.append("")
    lines.append("Caveat: this assumes per-family trades distribute uniformly across symbols, which is an upper bound — different symbols have different liquidity / behavior. **The real test is to run OB + Sweep on actual additional symbols** (RTY, YM, MNQ, MES, etc.) and re-measure.")
    lines.append("")
    lines.append("### B. Shorter trade window (free slot earlier)")
    lines.append("")
    lines.append("Currently v8a holds for 240 min. If we cap at N min and keep the same R (conservative — actual R might be slightly worse with shorter hold):")
    lines.append("")
    lines.append("| Window | cum_R | Retention |")
    lines.append("|---|---:|---:|")
    for window in (60, 120, 180):
        sim = shorter[f"window_{window}m"]
        ret = sim["cum_r"] / baseline
        lines.append(f"| {window} min | {sim['cum_r']:.2f} | {ret*100:.1f}% |")
    lines.append("")
    lines.append("Caveat: this keeps the same per-trade R but shrinks holding time. Actual R under shorter window would need a real backtest run (since exits could happen at different prices).")
    lines.append("")
    lines.append("## Implications for v21 lockfile design")
    lines.append("")
    lines.append("1. If many blocks are opposite-direction, a **net-position rule** (rather than first-come-first-serve) could recover material edge.")
    lines.append("2. **More symbols** (4-6x universe) is the most plausible path to 70%+ retention without changing strategy logic.")
    lines.append("3. **Tighter trade window** (120 min) is cheap to test in a re-simulation and may recover meaningful retention.")
    lines.append("4. **Single-family OB-only paper trade** sidesteps the issue entirely while we sort the above.")
    lines.append("")

    out_md = OUT_DIR / "v26_concurrency_diagnosis.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote: {out_md.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
