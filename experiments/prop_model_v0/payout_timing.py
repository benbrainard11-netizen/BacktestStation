"""Operational funnel per firm: how fast to a payout, and how many accounts you burn before one.

Uses the FIXED eval_ev sims. For a given edge: eval pass-rate + days-to-pass, then funded
P(>=1 payout), days-to-first-payout, payouts/acct, blow-before-payout. Combines into the
milk funnel: eval-buys per banked payout, accounts failed before the first payout, calendar days.
risk = $/trade (realistic micro-ish on a ~$2-2.5k funded DD).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_ev import FUNNELS, eval_sim, funded_sim

RISK = 400.0
N_TRADES = 2
FIRMS = ["topstep", "lucid", "apex", "mffu", "tradeify"]
EDGES = [("zero edge (p0.50)", 0.50), ("+0.05R (p0.525)", 0.525)]

for label, p in EDGES:
    print(f"\n================  {label},  win_R=1.0, {N_TRADES} trades/day, ${RISK:.0f}/trade  ================")
    print(f"{'firm':9s} {'evalPass':>8s} {'d2pass':>6s} | {'P(payout)':>9s} {'d2payout':>8s} {'payouts/acct':>12s} {'blow b4 pay':>11s} | {'evalBuys/payout':>15s} {'acctsFailed':>11s}")
    for fm in FIRMS:
        spec = FUNNELS[fm]
        pp, d2p = eval_sim(spec, p, 1.0, N_TRADES, RISK)
        if pp < 0.01:
            print(f"{fm:9s}  eval ~never passes at this shape"); continue
        d = funded_sim(spec, p, 1.0, N_TRADES, RISK, diag=True)
        q = d["p_any_payout"]
        eval_buys_per_payout = (1.0 / q / pp) if q > 0 else float("inf")
        accts_failed = eval_buys_per_payout - 1.0 if q > 0 else float("inf")   # eval fails + funded blows before 1st payout
        d2payout_total = (d2p if d2p == d2p else spec["eval"]["max_days"]) + (d["days_to_first_payout"] if q > 0 else float("nan"))
        print(f"{fm:9s} {pp*100:>7.0f}% {d2p:>6.1f} | {q*100:>8.0f}% {d['days_to_first_payout']:>8.1f} {d['mean_payouts']:>12.2f} {d['blow_no_payout']*100:>10.0f}% | {eval_buys_per_payout:>15.1f} {accts_failed:>11.1f}")
    print("  (d2payout = eval days + funded days to FIRST payout; evalBuys/payout = how many eval purchases per ONE banked payout)")
