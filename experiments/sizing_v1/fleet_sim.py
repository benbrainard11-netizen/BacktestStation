"""Correlated multi-account FLEET sim -- the real milk math.

Running the SAME strategy across N prop accounts means their daily P&L is CORRELATED (copy-trading -> same
trades). So a bad stretch doesn't blow ~independent accounts -- it blows a whole BATCH at once. Single-account
expectancy hides this; the fleet's TAIL (a bad-luck run wiping most accounts) is the real risk.

Model: one shared "master" outcome stream per calendar day (the strategy's actual results). Each account trades
it, but (a) gets a random START OFFSET (staggering accounts decorrelates *when* the bad stretch hits its
lifecycle) and (b) a small per-trade idiosyncratic flip (jitter/fills). SYNC (all start same day) = max
correlation; STAGGERED = spread starts. Monte-Carlo over many fleets -> mean fleet $, the 5th-percentile fleet $
(bad-luck tail), and mean/worst fraction-of-fleet blown.

The point: find the risk size + staggering that maximizes EXPECTED fleet payout WITHOUT a tail that wipes you.
Uses Apex (the champion firm) + the balanced profile; plug Mira's real distribution + real firm numbers later.

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/fleet_sim.py
"""
from __future__ import annotations

import datetime as dt
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from account import Account, Trade               # noqa: E402
from profile_per_firm import PROFILES, TPD, build_firms, business_days  # noqa: E402

HORIZON, N_ACCT, N_FLEETS, IDIO = 100, 40, 400, 0.05


def run_fleet(firm, p, winR, risk, max_stagger, rng, days) -> tuple[float, float]:
    L = max_stagger + HORIZON
    master = [[rng.random() < p for _ in range(TPD)] for _ in range(L)]   # shared daily outcomes
    sym = firm.allowed_symbols[0]
    pays, blown = [], 0
    for a in range(N_ACCT):
        s = rng.randint(0, max_stagger)
        acc = Account(account_id=f"a{a}", firm=firm, sim_start_date=days[0])
        for ld in range(HORIZON):
            if acc.status != "active":
                break
            d = days[ld]
            for k in range(TPD):
                if acc.status != "active":
                    break
                win = (rng.random() < p) if rng.random() < IDIO else master[s + ld][k]
                pnl = winR * risk if win else -risk
                ts = dt.datetime.combine(d, dt.time(10 + k, 0))
                acc.on_trade_close(Trade(trade_id=f"{a}-{ld}-{k}", entry_ts=ts, exit_ts=ts + dt.timedelta(minutes=20),
                                         symbol=sym, direction=1, contracts=1, entry_price=100.0,
                                         exit_price=100.0 + pnl, pnl_usd=pnl, pnl_reason="x"))
            if acc.status == "active":
                acc.on_eod(d)
        acc.finalize(days[HORIZON - 1])
        pays.append(acc.total_payouts_received)
        blown += acc.status.startswith("blown")
    return sum(pays), blown / N_ACCT


def main() -> int:
    firm = build_firms()["Apex"]
    p, winR = PROFILES["balanced p58 / 1.4R"]
    fee = firm.eval_fee_usd + firm.monthly_subscription_usd * (HORIZON / 21.0)
    days = business_days(dt.date(2025, 1, 6), HORIZON)
    print(f"FLEET sim: {firm.firm_name}, balanced p58/1.4R, {N_ACCT} accounts, {N_FLEETS} fleets, {HORIZON}d, idio={IDIO}\n")
    print(f"{'risk':>5} {'starts':>10} | {'mean$':>11} {'5%tile$':>11} {'1%tile$':>11} {'mean blown':>10} {'worst blown':>11}")
    for risk in (250, 400, 600, 800, 1000):
        for sname, mstag in (("sync", 0), ("staggered", HORIZON)):
            rng = random.Random(7)
            tot, bl = [], []
            for _ in range(N_FLEETS):
                t, b = run_fleet(firm, p, winR, risk, mstag, rng, days)
                tot.append(t - fee * N_ACCT)
                bl.append(b)
            tot, bl = np.array(tot), np.array(bl)
            print(f"{risk:>5} {sname:>10} | {tot.mean():>11,.0f} {np.percentile(tot, 5):>11,.0f} "
                  f"{np.percentile(tot, 1):>11,.0f} {bl.mean():>10.0%} {bl.max():>11.0%}")
        print()
    print("mean = expected total fleet payout (net of fees) | 5%tile = bad-luck fleet (the tail that matters) |")
    print("blown = fraction of the 40 accounts blown.  SYNC vs STAGGERED shows the correlated-wipe risk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
