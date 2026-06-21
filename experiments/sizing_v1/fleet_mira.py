"""Fleet sim driven by MIRA's REAL trade-level R-distribution (909 2025 OOS entries, trail_2R, stressed costs).

Bootstraps each trade's R from Mira's actual realized-R array (not a synthetic profile), x $/R sizing, fed
through the Account state machine across a staggered fleet. Runs TWO cases:
  REAL (MBO-free, mean -0.11R)  -> the version measurable at scale; expected to LOSE/blow (negative edge).
  +0.38R (shifted, "if the with-MBO edge holds") -> the same shape lifted to the live-MBO number; the milk upside.
The gap between them IS the question: the milk only works if Mira's with-MBO edge (one tiny slice) is real.

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/fleet_mira.py
"""
from __future__ import annotations

import datetime as dt
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from account import Account, Trade               # noqa: E402
from profile_per_firm import build_firms, business_days  # noqa: E402

HORIZON, N_ACCT, N_FLEETS, IDIO, TPD = 100, 40, 300, 0.05, 5
OOS = HERE / "out" / "mira_oos_mbofree" / "oos_exits.parquet"


def run_fleet(firm, R, risk_per_R, max_stagger, rng, days):
    L, n = max_stagger + HORIZON, len(R)
    master = [[R[rng.randrange(n)] for _ in range(TPD)] for _ in range(L)]
    sym, pays, blown = firm.allowed_symbols[0], [], 0
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
                r = R[rng.randrange(n)] if rng.random() < IDIO else master[s + ld][k]
                pnl = r * risk_per_R
                ts = dt.datetime.combine(d, dt.time(9 + k, 0))
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
    d = pd.read_parquet(OOS)
    R_real = d["r_trail_2R"].dropna().to_numpy()
    R_edge = R_real - R_real.mean() + 0.38            # same shape, lifted to the hoped +0.38R
    firm = build_firms()["Apex"]
    fee = firm.eval_fee_usd + firm.monthly_subscription_usd * (HORIZON / 21.0)
    days = business_days(dt.date(2025, 1, 6), HORIZON)
    print(f"Mira fleet: Apex, {N_ACCT} acct staggered, {N_FLEETS} fleets, {TPD} trades/day, {HORIZON}d")
    print(f"  REAL MBO-free dist: mean {R_real.mean():+.3f}R win {np.mean(R_real>0):.0%} (n={len(R_real)})")
    print(f"  +0.38R 'if edge holds' dist: mean {R_edge.mean():+.3f}R\n")
    print(f"{'case':14} {'$/R':>5} | {'mean fleet$':>12} {'5%tile$':>11} {'mean blown':>11}")
    for name, R in (("REAL(mbofree)", R_real), ("+0.38R(ifedge)", R_edge)):
        for rpr in (75, 150, 300):
            rng = random.Random(7)
            tot, bl = [], []
            for _ in range(N_FLEETS):
                t, b = run_fleet(firm, R, rpr, HORIZON, rng, days)
                tot.append(t - fee * N_ACCT)
                bl.append(b)
            tot = np.array(tot)
            print(f"{name:14} {rpr:>5} | {tot.mean():>12,.0f} {np.percentile(tot, 5):>11,.0f} {np.mean(bl):>11.0%}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
