"""Which strategy RETURN-DISTRIBUTION PROFILE milks each prop firm hardest? (the per-firm objective engine)

Reuses the sizing_v1 Account state machine (real trailing-DD, daily-loss, payout, consistency-rule logic) + the
6 firm YAML configs. Feeds each firm synthetic trade streams from a family of strategy profiles that span the
distribution axis the user named -- from SMOOTH/high-win-rate (singles) to FAT-TAIL/low-win-rate (home runs) --
all at ~MATCHED per-trade edge (E~0.40R), so we isolate the effect of DISTRIBUTION SHAPE, not edge size.

Monte-Carlo N accounts x HORIZON days per (firm x profile). Metric = net $ POCKETED per account (payouts net of
fees), plus blow-up rate. The consistency rule + payout cap are exactly what should punish fat-tail at some firms
and reward it at others -- the whole "different strategies for different prop rules" thesis, quantified.

Rule numbers come from the existing config/firms/*.yaml (flagged earlier as partly placeholder -- user to
confirm exact numbers; the ENGINE is the deliverable, swap real numbers in and re-run).

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/profile_per_firm.py
"""
from __future__ import annotations

import datetime as dt
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from account import Account, Trade          # noqa: E402
from firm_rules import FirmConfig            # noqa: E402

HORIZON, N_ACC, TPD, RISK = 100, 1500, 3, 150.0   # trading days, accounts/cell, trades/day, $ risked/trade

# strategy profiles: (win_rate, win_R), loss = -1R, all at ~E=+0.40R/trade -> same edge, different shape
PROFILES = {
    "smooth   p70 / 1.0R": (0.70, 1.00),
    "balanced p58 / 1.4R": (0.583, 1.40),
    "asym     p50 / 1.8R": (0.50, 1.80),
    "fat-tail p45 / 2.1R": (0.45, 2.111),
    "homerun  p35 / 2.9R": (0.35, 2.857),
    "moonshot p30 / 3.7R": (0.30, 3.667),
}


def mk(name, dd, daily, consist, cap, min_win, fee=150.0, sub=0.0, acct=50000.0):
    """Representative funded-phase config (PLACEHOLDER numbers -- swap in real ones)."""
    return FirmConfig(
        firm_name=name, account_size=acct, evaluation_type="funded",
        trailing_drawdown=dd, trailing_dd_uses_eod=True,
        trailing_dd_lock_threshold=acct + dd, trailing_dd_locked_value=acct,
        daily_loss_limit=daily, daily_loss_intraday=True,
        payout_min_winning_days=min_win, payout_winning_day_threshold_usd=200.0,
        payout_profit_threshold=0.0, payout_amount_method="half_of_profits",
        payout_cap_usd=cap, payout_balance_after="keep_remainder", payout_resets_winning_day_counter=True,
        consistency_rule_pct=consist, consistency_rule_applies_at="funded",
        allowed_symbols=("NQ.c.0", "ES.c.0"), max_position_size=10, max_total_position=10,
        news_blackout_minutes_before=0, news_blackout_minutes_after=0, events_blocked=(),
        sim_max_days=365, monthly_subscription_usd=sub, eval_fee_usd=fee, funded_account_value_usd=None,
        notes="placeholder",
    )


def build_firms() -> dict[str, FirmConfig]:
    # spectrum from no-consistency/uncapped (rewards fat tail) to strict-consistency/capped (rewards smooth)
    return {f.firm_name: f for f in [
        # reality (user): MOST firms have NO daily-loss limit; the few that do set it ~$1k. -> trailing DD is
        # the universal ceiling. daily=99999 means "no daily loss limit".
        mk("TPT",      dd=2500, daily=99999, consist=0,  cap=100000, min_win=3, fee=150, sub=0),   # uncapped, no consistency
        mk("Apex",     dd=2500, daily=99999, consist=30, cap=25000, min_win=8, fee=0,  sub=85),
        mk("MFFU",     dd=2000, daily=99999, consist=40, cap=6000,  min_win=5, fee=0,  sub=80),
        mk("Tradeify", dd=2000, daily=99999, consist=20, cap=2500,  min_win=5, fee=150, sub=0),
        mk("Topstep",  dd=2000, daily=1000, consist=50, cap=3000,  min_win=5, fee=0,  sub=149),    # HAS daily loss ~$1k
        mk("Lucid",    dd=2000, daily=1000, consist=30, cap=2000,  min_win=7, fee=150, sub=0),     # HAS daily loss ~$1k
    ]}


def business_days(start: dt.date, n: int) -> list[dt.date]:
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    return days


def sim_account(firm, p, winR, risk, rng, days) -> Account:
    acc = Account(account_id="x", firm=firm, sim_start_date=days[0])
    sym = firm.allowed_symbols[0] if firm.allowed_symbols else "NQ.c.0"
    for d in days:
        if acc.status != "active":
            break
        for k in range(TPD):
            if acc.status != "active":
                break
            pnl = winR * risk if rng.random() < p else -risk
            ts = dt.datetime.combine(d, dt.time(10 + k, 0))
            acc.on_trade_close(Trade(trade_id=f"{d}{k}", entry_ts=ts, exit_ts=ts + dt.timedelta(minutes=20),
                                     symbol=sym, direction=1, contracts=1, entry_price=100.0,
                                     exit_price=100.0 + pnl, pnl_usd=pnl, pnl_reason="x"))
        if acc.status == "active":
            acc.on_eod(d)
    acc.finalize(days[-1])
    return acc


def main() -> int:
    firms = build_firms()
    days = business_days(dt.date(2025, 1, 6), HORIZON)
    print(f"horizon={HORIZON}d  N={N_ACC}/cell  {TPD} trades/day  risk=${RISK:.0f}  "
          f"profiles all ~E+0.40R/trade (same edge, different shape)\n")
    best = {}
    for fname, firm in firms.items():
        fee = firm.eval_fee_usd + firm.monthly_subscription_usd * (HORIZON / 21.0)
        print(f"=== {fname:9} ${firm.account_size:.0f} | DD ${firm.trailing_drawdown:.0f} dailyLoss ${firm.daily_loss_limit:.0f} "
              f"consist {firm.consistency_rule_pct:.0f}% cap ${firm.payout_cap_usd:.0f} minWinDays {firm.payout_min_winning_days} "
              f"fee ${fee:.0f} ===")
        rows = []
        for pname, (p, winR) in PROFILES.items():
            rng = random.Random(12345)
            accs = [sim_account(firm, p, winR, RISK, rng, days) for _ in range(N_ACC)]
            pay = np.array([a.total_payouts_received for a in accs])
            blow = float(np.mean([a.status.startswith("blown") for a in accs]))
            net = pay - fee
            rows.append((pname, net.mean(), pay.mean(), float(np.mean(pay > 0)), blow))
        rows.sort(key=lambda r: -r[1])
        for i, (pname, netm, paym, prate, blow) in enumerate(rows):
            star = " <-- BEST" if i == 0 else ""
            print(f"  {pname:22} net$/acct={netm:+8.0f}  payout$/acct={paym:8.0f}  got-paid={prate:4.0%}  blow={blow:4.0%}{star}")
        best[fname] = rows[0][0]
        print()
    print("================ BEST PROFILE PER FIRM ================")
    for f, p in best.items():
        print(f"  {f:9} -> {p}")

    print("\n================ RISK-SIZE SWEEP (balanced p58/1.4R) -- net$/acct : blow% ================")
    p, winR = PROFILES["balanced p58 / 1.4R"]
    for fname, firm in firms.items():
        fee = firm.eval_fee_usd + firm.monthly_subscription_usd * (HORIZON / 21.0)
        cells = []
        for risk in (100, 150, 250, 400, 600, 800):
            rng = random.Random(12345)
            accs = [sim_account(firm, p, winR, risk, rng, days) for _ in range(N_ACC)]
            pay = np.array([a.total_payouts_received for a in accs])
            blow = float(np.mean([a.status.startswith("blown") for a in accs]))
            cells.append(f"${risk:>3.0f}:{pay.mean() - fee:>6.0f}/{blow:>3.0%}")
        print(f"  {fname:9} " + "  ".join(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
