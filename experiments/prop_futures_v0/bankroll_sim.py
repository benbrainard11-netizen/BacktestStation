"""bankroll_sim — can the prop eval ASYMMETRY flip a small bankroll into a big one? (risk of ruin)

The honest "small -> big" question. No market edge needed: a high-win ~0-EV generator (the reversion,
fade_R distribution) farms the eval asymmetry (small fee -> funded payout). This sims a BANKROLL process:
start $B in eval fees, keep buying evals; each attempt costs a fee, passes with P(pass) (from the
reversion's real distribution through eval_ev's firm machinery), and a funded pass yields a payout drawn
from the simulated funded-account payout distribution. Track P(flip to TARGET) vs P(bust).

Honest about fragility: runs at MODEL EV and a STRESSED EV (payouts haircut, simulating consistency-rule
friction / the variance-farm being against-spirit). EXPLORATORY (13-mo generator distribution).

  python bankroll_sim.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MOD = Path(__file__).resolve().parent
OUT = MOD / "out"
sys.path.insert(0, str(MOD.parent / "prop_model_v0"))
sys.path.insert(0, str(MOD))
import eval_ev  # noqa: E402
import eval_reversion as ER  # noqa: E402
from eval_ev import FUNNELS  # noqa: E402

TARGET = 10000.0      # "big" = flip to $10k in extracted payouts
MAX_EVALS = 60        # give up after this many eval attempts
N_PATHS = 20000
FIRM = "lucid"        # oneoff fee, loosest rules (best variance-farm host); n/risk = conservative-ish
N_TRADES, RISK = 2, 600
RNG = np.random.default_rng(20)


def setup():
    df = pd.concat([pd.read_parquet(p) for p in OUT.glob("events_*.parquet")], ignore_index=True)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["fade_R"])
    ER.DIST = df["fade_R"].to_numpy()
    eval_ev.day_draws = ER.emp_draws
    spec = FUNNELS[FIRM]
    p_pass, _ = eval_ev.eval_sim(spec, 0.5, 1.0, N_TRADES, RISK)
    diag = eval_ev.funded_sim(spec, 0.5, 1.0, N_TRADES, RISK, diag=True)
    paid = diag["paid_array"]                      # trader-side payout per funded account ($)
    fee = spec["eval"]["fee"]; reset = spec["eval"].get("reset") or fee; act = spec["eval"]["act"]
    return p_pass, paid, fee, reset, act


def bankroll_mc(p_pass, paid, fee, reset, act, B0, payout_mult=1.0):
    paid_pos = paid * payout_mult
    flips = busts = 0; finals = []; n_evals = []
    for _ in range(N_PATHS):
        B = B0; ev = 0; passed_once = False
        while ev < MAX_EVALS:
            cost = (reset if passed_once else fee)
            if B < cost:
                break
            B -= cost; ev += 1
            if RNG.random() < p_pass:
                passed_once = True
                payout = float(RNG.choice(paid_pos)) - act
                B += max(payout, 0.0)
                if B >= TARGET:
                    break
        finals.append(B); n_evals.append(ev)
        if B >= TARGET:
            flips += 1
        elif B < fee:
            busts += 1
    finals = np.array(finals)
    return dict(flip=flips / N_PATHS, bust=busts / N_PATHS, med_final=float(np.median(finals)),
                mean_final=float(finals.mean()), med_evals=float(np.median(n_evals)))


def main():
    p_pass, paid, fee, reset, act = setup()
    print(f"FIRM={FIRM} reversion gen (n={N_TRADES},risk=${RISK}): P(pass)={p_pass:.3f} "
          f"| fee=${fee} reset=${reset} act=${act} | funded payout: mean ${paid.mean():.0f} "
          f"P(any payout)={np.mean(paid>0):.2f} | TARGET=${TARGET:.0f}")
    print(f"\n{'bankroll':>9} {'scenario':>10} {'P(flip $10k)':>13} {'P(bust)':>9} {'med final':>10} {'mean final':>11} {'med evals':>10}")
    for B0 in [300, 600, 1000, 2000, 5000]:
        for label, mult in [("model", 1.0), ("stressed", 0.6)]:
            r = bankroll_mc(p_pass, paid, fee, reset, act, B0, mult)
            print(f"  ${B0:>6} {label:>10} {r['flip']:>12.1%} {r['bust']:>8.1%} "
                  f"${r['med_final']:>8.0f} ${r['mean_final']:>9.0f} {r['med_evals']:>9.0f}")
    print("\nMODEL = reversion eval-EV as estimated; STRESSED = payouts x0.6 (consistency-rule friction /"
          " variance-farm being against-spirit / rule tightening). Honest read: see P(bust) vs P(flip).")


if __name__ == "__main__":
    main()
