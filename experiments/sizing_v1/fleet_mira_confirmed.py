"""Milk projection on the CONFIRMED Jan-2026 with-MBO distribution (not the synthetic +0.38R shift).

fleet_mira.py shifted the MBO-free shape up to a HOPED +0.38R. This uses the ACTUAL realized-R array
from the reproduced Jan with-MBO OOS exit replay (replay_jan_withmbo.py -> jan2026_withmbo_exits.parquet,
139 real trades, trail_2R, same honest stressed costs). Three cases through the staggered Apex fleet:

  MBO-FREE 2025 (mean -0.11R, n=909)  -> the loser baseline (measurable at scale).
  WITH-MBO Jan  (mean +0.44R, n=139)  -> the CONFIRMED real shape (the milk upside, real not assumed).
  WITH-MBO /2   (edge halved, ~+0.22R) -> STRESS: Jan is one month; what if the forward edge is half?

Honest caveat: the with-MBO array is 139 trades over ONE month (Jan 2026, a genuine pre-training OOS
slice). Bootstrapping it to annual fleets assumes Jan generalizes -- it is the best data we have, not proof.

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/fleet_mira_confirmed.py
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
import fleet_mira as fm  # noqa: E402  reuse run_fleet + constants
from profile_per_firm import build_firms, business_days  # noqa: E402

JAN = HERE / "out" / "mira_oos_withmbo" / "jan2026_withmbo_exits.parquet"
MBOFREE = HERE / "out" / "mira_oos_mbofree" / "oos_exits.parquet"


def main() -> int:
    R_mf = pd.read_parquet(MBOFREE)["r_trail_2R"].dropna().to_numpy()
    R_jan = pd.read_parquet(JAN)["r_trail_2R"].dropna().to_numpy()
    R_half = R_jan - R_jan.mean() + 0.5 * R_jan.mean()   # same shape, edge halved

    firm = build_firms()["Apex"]
    fee = firm.eval_fee_usd + firm.monthly_subscription_usd * (fm.HORIZON / 21.0)
    days = business_days(dt.date(2025, 1, 6), fm.HORIZON)

    print(f"Mira milk -- CONFIRMED Jan with-MBO dist | Apex, {fm.N_ACCT} acct staggered, "
          f"{fm.N_FLEETS} fleets, {fm.TPD} trades/day, {fm.HORIZON}d")
    print(f"  MBO-free 2025 : mean {R_mf.mean():+.3f}R  win {np.mean(R_mf>0):.0%}  n={len(R_mf)}")
    print(f"  WITH-MBO Jan  : mean {R_jan.mean():+.3f}R  win {np.mean(R_jan>0):.0%}  n={len(R_jan)}")
    print(f"  WITH-MBO /2   : mean {R_half.mean():+.3f}R  (edge halved stress)\n")
    print(f"{'case':16} {'$/R':>5} | {'mean fleet$':>12} {'5%tile$':>11} {'95%tile$':>11} {'mean blown':>11}")

    cases = [("MBO-free", R_mf), ("WITH-MBO Jan", R_jan), ("WITH-MBO /2", R_half)]
    for name, R in cases:
        for rpr in (75, 150, 300):
            rng = random.Random(7)
            tot = []
            for _ in range(fm.N_FLEETS):
                t, _b = fm.run_fleet(firm, R, rpr, fm.HORIZON, rng, days)
                tot.append(t - fee * fm.N_ACCT)
            tot = np.array(tot)
            bl = []  # recompute blown rate cheaply on a few fleets
            rng2 = random.Random(11)
            for _ in range(50):
                _t, b = fm.run_fleet(firm, R, rpr, fm.HORIZON, rng2, days)
                bl.append(b)
            print(f"{name:16} {rpr:>5} | {tot.mean():>12,.0f} {np.percentile(tot,5):>11,.0f} "
                  f"{np.percentile(tot,95):>11,.0f} {np.mean(bl):>11.0%}")
        print()
    print("Each fleet = 40 staggered Apex accounts over ~100 business days (~5 months). $/R = risk per R.")
    print("Numbers are net of eval+subscription fees. One sim 'unit' ~ a 5-month milking cohort.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
