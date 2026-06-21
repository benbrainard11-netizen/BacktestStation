"""Fleet economics, built on the VERIFIED eval_ev sim (not the buggy sizing_v1 Account).

Run N accounts (firm cap) as one fleet. The mean scales N x per-account; the TAIL depends on
correlation. We bracket it:
  SYNCED  (copy-trade lockstep, max correlation) = N x (one random account) -> all blow together.
  STAGGERED (~independent, the proven decorrelation win) = sum of N independent accounts.
Real staggered sits near the independent bound (prior fleet_sim finding: staggering ~ decorrelation).
Per-slot net = funded payout (trader-side) - expected eval cost to fund it. Zero edge + +0.05R.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_ev import FUNNELS, eval_sim, funded_sim

RNG = np.random.default_rng(7)
RISK, N_TRADES, TRIALS = 400.0, 2, 4000
FIRMS = ["topstep", "lucid", "apex", "mffu", "tradeify"]
EDGES = [("zero edge", 0.50), ("+0.05R", 0.525)]


def cost_to_fund(spec, p_pass, days):
    e = spec["eval"]
    attempts = 1.0 / p_pass
    if e["fee_kind"] == "monthly":
        months = max(np.ceil((days if days == days else e["max_days"]) / 21), 1)
        fees = e["fee"] * months * attempts
    else:
        retry = e["reset"] if e.get("reset") else e["fee"]
        fees = e["fee"] + (attempts - 1) * retry
    return fees + e["act"]


for label, p in EDGES:
    print(f"\n================  FLEET — {label} (win_R=1, {N_TRADES} trades/day, ${RISK:.0f}/trade)  ================")
    print(f"{'firm':9s} {'N':>3s} {'perAcct$':>8s} | {'fleet mean$':>11s} | {'SYNCED 5%':>10s} {'P(syncLoss)':>11s} | {'STAGGER 5%':>11s} {'P(stagLoss)':>11s}")
    for fm in FIRMS:
        spec = FUNNELS[fm]
        N = spec.get("accounts_cap", 5) or 5
        pp, days = eval_sim(spec, p, 1.0, N_TRADES, RISK)
        if pp < 0.01:
            print(f"{fm:9s}  eval never passes"); continue
        d = funded_sim(spec, p, 1.0, N_TRADES, RISK, diag=True)
        cost = cost_to_fund(spec, pp, days)
        net = d["paid_array"] - cost                    # per-slot net $ (payout - eval cost to fund)
        per_acct = float(net.mean())
        # SYNCED: fleet = N x one random account
        sync = RNG.choice(net, TRIALS) * N
        # STAGGERED ~ independent: sum of N independent draws per trial
        stag = RNG.choice(net, (TRIALS, N)).sum(axis=1)
        print(f"{fm:9s} {N:>3d} {per_acct:>8.0f} | {per_acct*N:>11.0f} | "
              f"{np.percentile(sync,5):>10.0f} {(sync<0).mean()*100:>10.0f}% | "
              f"{np.percentile(stag,5):>11.0f} {(stag<0).mean()*100:>10.0f}%")
    print("  (5% = 5th-percentile fleet outcome = the bad-case; P(Loss) = chance the fleet nets negative.")
    print("   SYNCED = copy-trade lockstep; STAGGERED = decorrelated starts. Same mean, very different tail.)")
