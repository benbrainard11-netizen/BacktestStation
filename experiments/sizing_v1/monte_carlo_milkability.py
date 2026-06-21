"""Block-bootstrap Monte Carlo — FUNDED phase, corrected Topstep $50k rules.

Rules (user 2026-05-28):
  - EOD trailing drawdown of $2k. Floor = EOD_high_water - 2000, UNTIL EOD
    balance hits $52k, then floor LOCKS at $50k permanently. (firm_rules.py)
  - NO daily loss limit on Topstep funded. (disabled below)
  - Payout: 5 winning days (>=$200) + >=$3k profit -> take half profits, cap $5k.

Why MC: with a trailing DD, survival is order-dependent (an early loss streak
before the floor locks blows you; a late one doesn't). We resample WHOLE TRADING
DAYS in consecutive blocks (block bootstrap) so loss-clustering is preserved —
iid shuffling would smooth away the streaks that actually kill accounts.

Each trade is hard-stopped at ~1R, so balance can't swing >~1R between trade
closes; close-based floor checking is therefore honest, and the unbounded
quote-path mae_R is moot under EOD trailing.

MC quantifies sequence/sizing risk GIVEN these trades. It does NOT validate the
edge — forward data still does. Read-only on the export.
"""
from __future__ import annotations

import datetime as dt
import glob
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPERIMENT_DIR))
from account import Account, Trade
from firm_rules import load_firm_config

TRADE_GLOB = r"C:/Users/benbr/bs-mira-v15/**/mira_v15_model_reclaim_2r_trade_list_stressed.parquet"
FIRM_CFG = EXPERIMENT_DIR / "config" / "firms" / "topstep_50k.yaml"

R_GRID = [50, 75, 100, 150, 200, 300]
N_PATHS = 3000
BLOCK_DAYS = 5
FUNDED_DAYS = 60          # ~3 trading months per funded path
BASE = dt.date(2026, 1, 5)


def days_for(fdf: pd.DataFrame) -> list[list[float]]:
    """Group a filter's trades into per-trading-day lists of realized R."""
    fdf = fdf.sort_values("entry_ts")
    return [[float(r.realized_R_net) for r in g.itertuples()]
            for _, g in fdf.groupby(fdf["entry_ts"].dt.date, sort=True)]


def bootstrap(days: list, n_days: int, rng: np.random.Generator) -> list:
    out, nd = [], len(days)
    while len(out) < n_days:
        s = int(rng.integers(0, nd))
        out.extend(days[(s + k) % nd] for k in range(BLOCK_DAYS))
    return out[:n_days]


def run_path(day_blocks, firm, r_dollars) -> dict:
    acc = Account(account_id="mc", firm=firm, sim_start_date=BASE)
    banked = False
    for i, day_R in enumerate(day_blocks):
        if acc.status != "active":
            break
        d = BASE + dt.timedelta(days=i)
        ts = dt.datetime.combine(d, dt.time(15, 0))
        for R in day_R:
            if acc.status != "active":
                break
            tr = Trade(trade_id="t", entry_ts=ts, exit_ts=ts, symbol="X", direction=1,
                       contracts=1, entry_price=0.0, exit_price=0.0,
                       pnl_usd=R * r_dollars, pnl_reason="r")
            acc.on_trade_close(tr)
        acc.on_eod(d)
        if acc.payouts:
            banked = True
    acc.finalize(BASE + dt.timedelta(days=max(0, len(day_blocks) - 1)))
    blew = acc.status in ("blown_daily", "blown_dd")
    return {
        "blew": blew,
        "blew_before_payout": blew and not banked,
        "locked": acc.eod_balance_high_water >= firm.trailing_dd_lock_threshold,
        "payout": len(acc.payouts) > 0,
        "n_payouts": len(acc.payouts),
        "collected": acc.total_pnl_collected,
    }


def main() -> int:
    path = glob.glob(TRADE_GLOB, recursive=True)[0]
    df = pd.read_parquet(path)
    firm = load_firm_config(FIRM_CFG)
    firm = replace(firm, daily_loss_limit=1e12)  # Topstep funded: NO daily loss limit
    filters = {"all": df, "no_ym": df[df.no_ym]}
    rng = np.random.default_rng(7)

    print(f"FUNDED MC | {N_PATHS} paths x {FUNDED_DAYS} trading days | block={BLOCK_DAYS}d | "
          f"Topstep $50k: EOD-trail ${firm.trailing_drawdown:.0f}, lock@${firm.trailing_dd_lock_threshold:.0f}, "
          f"NO daily limit, target ${firm.payout_profit_threshold:.0f}\n")
    print(f"{'filter':7s} {'$/R':>4s} | {'survive%':>8s} {'lock%':>6s} {'payout%':>7s} "
          f"{'blowB4pay%':>10s} {'meanPayouts':>11s} | {'med$':>7s} {'p5$':>7s} {'p95$':>8s}")
    for fname, fdf in filters.items():
        days = days_for(fdf)
        for rd in R_GRID:
            res = pd.DataFrame(run_path(bootstrap(days, FUNDED_DAYS, rng), firm, rd) for _ in range(N_PATHS))
            c = res.collected
            print(f"{fname:7s} {rd:>4d} | {100*(~res.blew).mean():>7.1f}% {100*res.locked.mean():>5.1f}% "
                  f"{100*res.payout.mean():>6.1f}% {100*res.blew_before_payout.mean():>9.1f}% "
                  f"{res.n_payouts.mean():>11.2f} | {c.median():>7.0f} {c.quantile(.05):>7.0f} {c.quantile(.95):>8.0f}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
