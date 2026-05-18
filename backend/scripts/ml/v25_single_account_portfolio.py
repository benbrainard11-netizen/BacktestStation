"""Paper-trade Gate 4 — single-account portfolio simulator.

QUESTION: when OB strict + Sweep reversed run on ONE account (with
concurrency caps), how much edge survives vs running them in
independent silos?

CONTEXT: v20 ran each family independently. That overstates real-world
returns because in a single account:
  - capital is shared, so you can't be in unlimited concurrent positions
  - a trade already on (symbol, side) blocks a new signal on the same
    (symbol, side)
  - correlations between OB + Sweep signals amplify drawdowns when
    they both fire together

METHOD:
  - Merge OB strict + Sweep reversed (filtered) trades from both
    holdouts into one chronological event stream.
  - Walk forward by entry_ts. For each candidate trade:
      * skip if (symbol) already held
      * skip if (total contracts held >= cap_total)
      * else: enter, record, hold until exit_ts
  - Two cap configurations tested:
      * cap_total = 1  (only 1 contract concurrent across the account)
      * cap_total = 2  (one per symbol, NQ + ES = 2 max concurrent)
  - For each, report:
      * cum_R surviving
      * % of candidate trades taken vs blocked
      * which family lost more to blocks
      * worst-day drawdown
      * concurrency histogram (% time at 0/1/2 contracts)

PASS THRESHOLD (pre-registered):
  - At cap_total=2 (one per symbol): retain >= 70% of summed
    independent cum_R
  - At cap_total=2: cum_R remains positive across both holdouts
  - At cap_total=1 (account-wide): retain >= 40% (sharper haircut
    expected since trades fight for the slot)
  - At cap_total=1: cum_R remains positive across both holdouts

OUTPUT:
  experiments/paper_trade_gates_2026_05_17/results/v25_single_account_portfolio.json
  experiments/paper_trade_gates_2026_05_17/results/v25_single_account_portfolio.md
  + trades_taken.csv (forensic)
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

CAP_CONFIGS = [
    {"name": "cap_total_1", "cap_total": 1, "per_symbol_cap": 1},
    {"name": "cap_total_2", "cap_total": 2, "per_symbol_cap": 1},
]


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
    # Sort by entry_ts; tiebreak by family (OB then Sweep) for determinism.
    out = out.sort_values(
        ["entry_ts", "family", "symbol"], kind="stable"
    ).reset_index(drop=True)
    return out


def run_portfolio_sim(
    trades: pd.DataFrame, *, cap_total: int, per_symbol_cap: int
) -> dict:
    """Walk forward; greedily accept trades subject to concurrency caps.

    Maintains a list of open positions (symbol, exit_ts). At each
    candidate entry_ts, expires any open positions where exit_ts <=
    entry_ts (so they're no longer holding the slot).
    """
    open_positions: list[dict] = []  # {symbol, exit_ts}
    taken_rows = []
    blocked_count = {"per_symbol": 0, "total_cap": 0}
    daily_pnl: dict[pd.Timestamp, float] = {}
    concurrency_seconds: dict[int, float] = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}

    # We'll sample concurrency at each candidate entry_ts. Approximate
    # the time-at-N-contracts by accumulating durations between
    # consecutive entry_ts of the candidate stream.
    prev_ts = trades["entry_ts"].iloc[0] if not trades.empty else None

    for _, row in trades.iterrows():
        # Expire any positions whose exit_ts has passed.
        open_positions = [p for p in open_positions if p["exit_ts"] > row["entry_ts"]]

        # Concurrency accounting between prev_ts and row.entry_ts
        if prev_ts is not None and row["entry_ts"] > prev_ts:
            delta = (row["entry_ts"] - prev_ts).total_seconds()
            level = min(len(open_positions), 3)
            concurrency_seconds[level] = concurrency_seconds.get(level, 0.0) + delta
        prev_ts = row["entry_ts"]

        # Cap checks
        same_symbol_held = sum(1 for p in open_positions if p["symbol"] == row["symbol"])
        if same_symbol_held >= per_symbol_cap:
            blocked_count["per_symbol"] += 1
            continue
        if len(open_positions) >= cap_total:
            blocked_count["total_cap"] += 1
            continue

        # Accept the trade
        open_positions.append(
            {"symbol": row["symbol"], "exit_ts": row["exit_ts"]}
        )
        taken_rows.append(row)
        d = row["exit_ts"].floor("D")
        daily_pnl[d] = daily_pnl.get(d, 0.0) + float(row["pnl_r"])

    taken = pd.DataFrame(taken_rows)
    cum_r = float(taken["pnl_r"].sum()) if not taken.empty else 0.0

    # Per-family + per-holdout breakdowns
    breakdown_family: dict[str, dict] = {}
    breakdown_holdout: dict[str, dict] = {}
    if not taken.empty:
        for fam, grp in taken.groupby("family"):
            breakdown_family[fam] = {
                "trades_taken": int(len(grp)),
                "cum_r": round(float(grp["pnl_r"].sum()), 2),
            }
        # Approximate holdout split by entry year (holdout1 = 2018-2019, holdout2 = 2026)
        for year_label, grp in taken.groupby(
            taken["entry_ts"].dt.year.map(
                lambda y: "holdout_1_2018_2019" if y in (2018, 2019) else "holdout_2_2026"
            )
        ):
            breakdown_holdout[year_label] = {
                "trades_taken": int(len(grp)),
                "cum_r": round(float(grp["pnl_r"].sum()), 2),
            }

    # Daily P&L drawdown
    daily_series = pd.Series(daily_pnl).sort_index()
    cum_series = daily_series.cumsum()
    running_max = cum_series.cummax()
    drawdown = (cum_series - running_max).min() if not cum_series.empty else 0.0
    worst_day = daily_series.min() if not daily_series.empty else 0.0

    return {
        "cap_total": cap_total,
        "per_symbol_cap": per_symbol_cap,
        "n_trades_candidate": int(len(trades)),
        "n_trades_taken": int(len(taken)),
        "n_trades_blocked_by_per_symbol": blocked_count["per_symbol"],
        "n_trades_blocked_by_total_cap": blocked_count["total_cap"],
        "cum_r": round(cum_r, 2),
        "worst_day_r": round(float(worst_day), 2),
        "max_drawdown_r": round(float(drawdown), 2),
        "breakdown_family": breakdown_family,
        "breakdown_holdout": breakdown_holdout,
        "concurrency_seconds": {k: round(v, 1) for k, v in concurrency_seconds.items()},
        "taken_trades": taken,
    }


def write_md(
    summary_cum_r_independent: float,
    cum_r_per_family: dict[str, float],
    results: dict[str, dict],
) -> str:
    lines: list[str] = []
    lines.append("# v25 — Single-Account Portfolio Simulator (Paper-Trade Gate 4)")
    lines.append("")
    lines.append(f"_Generated {datetime.utcnow().isoformat()}Z_")
    lines.append("")
    lines.append("Tests how much of the v20 independent-family edge survives when "
                 "OB strict + Sweep reversed run on one account with concurrency caps.")
    lines.append("")
    lines.append("## Baseline (independent silos, v20)")
    lines.append("")
    for fam, cr in cum_r_per_family.items():
        lines.append(f"- {fam}: {cr:.2f} R")
    lines.append(f"- **Summed: {summary_cum_r_independent:.2f} R**")
    lines.append("")
    overall_pass = all(r["passed"] for r in results.values())
    lines.append(f"## Verdict: {'PASS' if overall_pass else 'FAIL'}")
    lines.append("")
    for cap_name, r in results.items():
        cfg = r["cfg"]
        sim = r["sim"]
        lines.append(f"### {cap_name} (cap_total={cfg['cap_total']}, per_symbol={cfg['per_symbol_cap']})")
        lines.append("")
        lines.append(f"- Candidate trades: {sim['n_trades_candidate']:,}")
        lines.append(f"- Trades taken: {sim['n_trades_taken']:,}")
        lines.append(f"- Blocked by per-symbol cap: {sim['n_trades_blocked_by_per_symbol']:,}")
        lines.append(f"- Blocked by total cap: {sim['n_trades_blocked_by_total_cap']:,}")
        lines.append(f"- cum_R: **{sim['cum_r']:.2f}** ({r['retention']*100:.1f}% of independent baseline)")
        lines.append(f"- Worst day: {sim['worst_day_r']:.2f} R")
        lines.append(f"- Max drawdown: {sim['max_drawdown_r']:.2f} R")
        lines.append("")
        if sim["breakdown_family"]:
            lines.append("Per-family taken:")
            for fam, b in sim["breakdown_family"].items():
                lines.append(f"  - {fam}: {b['trades_taken']:,} trades / {b['cum_r']:.2f} R")
            lines.append("")
        if sim["breakdown_holdout"]:
            lines.append("Per-holdout taken:")
            for ho, b in sim["breakdown_holdout"].items():
                lines.append(f"  - {ho}: {b['trades_taken']:,} trades / {b['cum_r']:.2f} R")
            lines.append("")
        c = r["checks"]
        lines.append(f"- Retention ≥ threshold: **{c['retention_ok']}** "
                     f"(actual={r['retention']*100:.1f}%, threshold={r['threshold']*100:.0f}%)")
        lines.append(f"- cum_R positive across both holdouts: **{c['both_holdouts_positive']}**")
        lines.append(f"- **{'PASS' if r['passed'] else 'FAIL'}**")
        lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- The independent baseline (~2.5K R combined) is what v20 reported. Real-world cum_R will be lower because of concurrency conflicts.")
    lines.append("- cap_total=2 (one per symbol) is the natural cap for a 2-symbol universe — closely approximates 'run both families against both symbols.'")
    lines.append("- cap_total=1 is the strictest case — only one trade across the whole account at a time. Useful if capital is tight.")
    lines.append("- The split of blocked trades between per-symbol vs total-cap tells you which constraint binds.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    print("v25 single-account portfolio simulator")
    trades = load_all_trades()
    print(f"  loaded {len(trades)} trades across {len(FAMILY_FILES)} families")

    cum_r_per_family = {
        fam: round(float(grp["pnl_r"].sum()), 2)
        for fam, grp in trades.groupby("family")
    }
    summary_independent = sum(cum_r_per_family.values())
    print(f"  baseline (independent silos): {summary_independent:.2f} R "
          f"= {cum_r_per_family}")
    print()

    results: dict[str, dict] = {}
    for cfg in CAP_CONFIGS:
        sim = run_portfolio_sim(
            trades, cap_total=cfg["cap_total"], per_symbol_cap=cfg["per_symbol_cap"]
        )
        retention = sim["cum_r"] / summary_independent if summary_independent != 0 else 0.0
        threshold = 0.70 if cfg["cap_total"] == 2 else 0.40

        both_pos = all(b["cum_r"] > 0 for b in sim["breakdown_holdout"].values()) \
            if sim["breakdown_holdout"] else False
        retention_ok = retention >= threshold
        passed = bool(retention_ok and both_pos)

        # Save trades-taken CSV (forensic)
        taken_csv = OUT_DIR / f"v25_trades_taken_{cfg['name']}.csv"
        sim["taken_trades"].drop(columns=["__source"], errors="ignore").to_csv(
            taken_csv, index=False
        )

        # Strip non-serializable from sim before returning
        sim_for_report = {k: v for k, v in sim.items() if k != "taken_trades"}
        results[cfg["name"]] = {
            "cfg": cfg,
            "sim": sim_for_report,
            "retention": round(retention, 4),
            "threshold": threshold,
            "checks": {
                "retention_ok": bool(retention_ok),
                "both_holdouts_positive": bool(both_pos),
            },
            "passed": passed,
        }
        print(
            f"  {cfg['name']}: taken={sim['n_trades_taken']}, "
            f"cum_R={sim['cum_r']:.2f}, retention={retention*100:.1f}% "
            f"(threshold {threshold*100:.0f}%) "
            f"{'PASS' if passed else 'FAIL'}"
        )
        print(f"    blocked: per_symbol={sim['n_trades_blocked_by_per_symbol']}, "
              f"total_cap={sim['n_trades_blocked_by_total_cap']}, "
              f"max_dd={sim['max_drawdown_r']:.2f}R")

    payload = {
        "generator": "v25_single_account_portfolio",
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "independent_baseline_cum_r": round(summary_independent, 2),
        "cum_r_per_family_independent": cum_r_per_family,
        "configurations": [r for r in results.values()],
        "overall_pass": all(r["passed"] for r in results.values()),
    }
    out_json = OUT_DIR / "v25_single_account_portfolio.json"
    out_md = OUT_DIR / "v25_single_account_portfolio.md"
    out_json.write_text(json.dumps(payload, indent=2, default=str))
    out_md.write_text(write_md(summary_independent, cum_r_per_family, results), encoding="utf-8")

    print()
    print(f"OVERALL: {'PASS' if payload['overall_pass'] else 'FAIL'}")
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
