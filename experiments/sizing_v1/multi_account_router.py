"""Multi-account funded-phase simulation with staggered start dates.

Spawns N accounts, each starting at a different point in the 5-year signal
window and running `sim_max_days` forward. This answers the real question:

  "If you started a funded account at any random time in the last 5 years,
   how would it do over the next year?"

Each account sees a different slice of history → genuine distribution of
outcomes (some blow early, some survive, some pay out repeatedly).

Output:
  out/accounts/{firm}/account_{i}.json   per-account final state
  out/pass_rates.parquet                 aggregated per-firm metrics
  prints a quick summary

See PLAN.md §8.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
sys.path.insert(0, str(EXPERIMENT_DIR))

from account import Account
from firm_rules import load_firm_config
from simulator import Signal, load_signals, simulate_account


def staggered_start_dates(signal_dates: list[dt.date], sim_max_days: int, n_accounts: int) -> list[dt.date]:
    """Evenly spaced start dates across the window, leaving sim_max_days of runway."""
    first = min(signal_dates)
    last = max(signal_dates)
    last_valid_start = last - dt.timedelta(days=sim_max_days)
    if last_valid_start <= first:
        # Not enough history for full runway; just start everyone at first
        return [first] * n_accounts
    span_days = (last_valid_start - first).days
    starts = []
    for i in range(n_accounts):
        offset = int(round(span_days * i / max(1, n_accounts - 1)))
        starts.append(first + dt.timedelta(days=offset))
    return starts


def slice_signals(signals: list[Signal], start: dt.date, sim_max_days: int) -> list[Signal]:
    end = start + dt.timedelta(days=sim_max_days)
    return [s for s in signals if start <= s.ts_decision.date() < end]


def run_firm(firm_name: str, strategy_cfg: dict, signals: list[Signal], n_accounts: int, out_dir: Path) -> list[dict]:
    firm_path = EXPERIMENT_DIR / "config" / "firms" / f"{firm_name}_50k.yaml"
    firm = load_firm_config(firm_path)
    sim_max_days = firm.sim_max_days

    signal_dates = [s.ts_decision.date() for s in signals]
    starts = staggered_start_dates(signal_dates, sim_max_days, n_accounts)

    acct_out = out_dir / "accounts" / firm_name
    acct_out.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    t0 = time.time()
    for i, start in enumerate(starts):
        sub = slice_signals(signals, start, sim_max_days)
        if not sub:
            continue
        account = Account(account_id=f"{firm_name}_50k_{i:03d}", firm=firm, sim_start_date=start)
        simulate_account(account=account, signals=sub, firm=firm, strategy_cfg=strategy_cfg, jitter_seed=1000 + i)

        rec = {
            "account_id": account.account_id,
            "firm": firm_name,
            "start_date": start.isoformat(),
            "status": account.status,
            "blown_reason": account.blown_reason,
            "final_balance": round(account.balance, 2),
            "profit_above_starting": round(account.profit_above_starting, 2),
            "total_payouts": round(account.total_payouts_received, 2),
            "n_payouts": len(account.payouts),
            "total_collected": round(account.total_pnl_collected, 2),
            "n_trades": len(account.trades),
            "n_trade_days": len(account.trade_days),
            "eod_high_water": round(account.eod_balance_high_water, 2),
            "n_signals_in_window": len(sub),
        }
        results.append(rec)
        (acct_out / f"{account.account_id}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

    print(f"  {firm_name}: {len(results)} accounts simulated in {time.time()-t0:.1f}s")
    return results


def summarize(firm_name: str, results: list[dict]) -> dict:
    if not results:
        return {"firm": firm_name, "n_accounts": 0}
    df = pd.DataFrame(results)
    n = len(df)
    n_with_payout = int((df["n_payouts"] > 0).sum())
    n_blown_daily = int((df["status"] == "blown_daily").sum())
    n_blown_dd = int((df["status"] == "blown_dd").sum())
    n_alive = int((df["status"] == "completed").sum())

    return {
        "firm": firm_name,
        "n_accounts": n,
        "n_alive_at_end": n_alive,
        "n_blown_daily": n_blown_daily,
        "n_blown_dd": n_blown_dd,
        "pct_blown": round(100 * (n_blown_daily + n_blown_dd) / n, 1),
        "n_with_at_least_one_payout": n_with_payout,
        "pct_with_payout": round(100 * n_with_payout / n, 1),
        "mean_total_collected": round(float(df["total_collected"].mean()), 0),
        "median_total_collected": round(float(df["total_collected"].median()), 0),
        "p25_total_collected": round(float(df["total_collected"].quantile(0.25)), 0),
        "p75_total_collected": round(float(df["total_collected"].quantile(0.75)), 0),
        "worst_total_collected": round(float(df["total_collected"].min()), 0),
        "best_total_collected": round(float(df["total_collected"].max()), 0),
        "mean_payouts_per_account": round(float(df["n_payouts"].mean()), 2),
        "mean_payout_dollars": round(float(df["total_payouts"].mean()), 0),
        "mean_trades": round(float(df["n_trades"].mean()), 1),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--firms", nargs="+", default=["topstep"])
    p.add_argument("--all-firms", action="store_true")
    p.add_argument("--n-accounts", type=int, default=100)
    p.add_argument("--strategy", default=str(EXPERIMENT_DIR / "config" / "strategy_v0.yaml"))
    p.add_argument("--out-dir", default=str(EXPERIMENT_DIR / "out"))
    args = p.parse_args(argv)

    strategy_cfg = yaml.safe_load(Path(args.strategy).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    preds_dir = (EXPERIMENT_DIR / strategy_cfg["model_predictions_dir"]).resolve()
    print(f"Loading signals from {preds_dir} ...")
    signals = load_signals(strategy_cfg, preds_dir)
    print(f"  {len(signals):,} signals loaded")

    firms = args.firms
    if args.all_firms:
        firms = [p.stem.replace("_50k", "") for p in sorted((EXPERIMENT_DIR / "config" / "firms").glob("*_50k.yaml"))]

    all_summaries = []
    for firm_name in firms:
        results = run_firm(firm_name, strategy_cfg, signals, args.n_accounts, out_dir)
        summary = summarize(firm_name, results)
        all_summaries.append(summary)

    summary_df = pd.DataFrame(all_summaries)
    summary_df.to_parquet(out_dir / "pass_rates.parquet", index=False)

    print("\n=== Per-firm summary ===")
    for s in all_summaries:
        print(f"\n{s['firm'].upper()} ({s['n_accounts']} accounts):")
        print(f"  alive at end:        {s['n_alive_at_end']}  ({100 - s['pct_blown']:.0f}% survived)")
        print(f"  blown daily:         {s['n_blown_daily']}")
        print(f"  blown trailing DD:   {s['n_blown_dd']}")
        print(f"  >= 1 payout:         {s['n_with_at_least_one_payout']}  ({s['pct_with_payout']:.0f}%)")
        print(f"  mean total collected: ${s['mean_total_collected']:,.0f}")
        print(f"  median collected:     ${s['median_total_collected']:,.0f}")
        print(f"  range [p25, p75]:     [${s['p25_total_collected']:,.0f}, ${s['p75_total_collected']:,.0f}]")
        print(f"  worst / best:         ${s['worst_total_collected']:,.0f} / ${s['best_total_collected']:,.0f}")
        print(f"  mean payouts/account: {s['mean_payouts_per_account']:.2f}")
        print(f"  mean $ paid out:      ${s['mean_payout_dollars']:,.0f}")
        print(f"  mean trades/account:  {s['mean_trades']:.0f}")

    print(f"\nWrote {(out_dir / 'pass_rates.parquet')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
