"""Monte Carlo: how fast to a +$4k balance in a FUNDED account, at different $risk/trade sizing.
Funded model: start +$0, each trade P&L = R * $size (fixed-5R operating-point R-series, bootstrapped),
trailing DD $2000 that LOCKS at +$2100 (can't lose below start once +$2100 banked). Reach +$4000 =
target. Reports P(hit $4k before DD breach), P(blow up first), and time (trades -> months at the op's
realized frequency). Run at the 60th-pctile op (recommended, ~39/mo) and 70th (deployed, ~27/mo)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prop_sizing as PS  # noqa: E402  (build_r_series(pct), sim_path)

MONTHS = 13.3
N_MC = 8000
SIZES = [100, 150, 200, 250, 300, 400]
TARGET, DD, LOCK = 4000.0, 2000.0, 2100.0
MAX_TRADES = 1200


def avg_dollar_risk_per_micro() -> float:
    """Median structure-stop $risk for 1 MICRO contract across the op trades (for a contracts guide)."""
    MICRO = {"ES.c.0": 5.0, "NQ.c.0": 2.0, "YM.c.0": 0.5, "RTY.c.0": 5.0}  # $/pt micro
    src = pd.concat([pd.read_parquet(HERE / "runs" / f) for f in
                     ["legal_bars_full.parquet", "ndog_levels_full.parquet", "stacked_failure_full.parquet"]],
                    ignore_index=True)
    src = src[src["symbol"].isin(PS.EX.LIQ) & (src["status"] == "entered")]
    src["dr"] = pd.to_numeric(src["risk_pts"], errors="coerce") * src["symbol"].map(MICRO)
    return float(src["dr"].median())


def time_stats(Rs, size):
    hit, blew, trades = 0, 0, []
    for _ in range(N_MC):
        reached, blewup = PS.sim_path(Rs, size, DD, LOCK, [TARGET], max_trades=MAX_TRADES)
        if reached[TARGET] is not None:
            hit += 1; trades.append(reached[TARGET])
        elif blewup:
            blew += 1
    t = np.array(trades) if trades else np.array([np.nan])
    return hit / N_MC, blew / N_MC, np.median(t), np.percentile(t, 25), np.percentile(t, 75)


def run(pct, label, micro_risk):
    Rs = PS.build_r_series(pct=pct)
    freq = len(Rs) / MONTHS
    print(f"\n{'='*90}\n{label}: R-series n={len(Rs)}, meanR={Rs.mean():+.3f}, win={100*(Rs>0).mean():.0f}%, "
          f"~{freq:.0f} trades/mo")
    print(f"{'$risk/tr':>9s} {'~micros':>8s} {'P(hit $4k)':>11s} {'P(blow 1st)':>12s} "
          f"{'median time':>20s} {'p25-p75':>18s}")
    for size in SIZES:
        p, pb, med, p25, p75 = time_stats(Rs, size)
        mc = max(1, round(size / micro_risk))
        if np.isnan(med):
            print(f"{size:>7d}$ {('~'+str(mc)):>8s} {100*p:>10.0f}% {100*pb:>11.0f}% {'never':>20s}")
            continue
        mo, mo25, mo75 = med / freq, p25 / freq, p75 / freq
        print(f"{size:>7d}$ {('~'+str(mc)):>8s} {100*p:>10.0f}% {100*pb:>11.0f}% "
              f"{med:>5.0f}tr (~{mo:>4.1f}mo) {p25:>4.0f}-{p75:>4.0f}tr (~{mo25:.1f}-{mo75:.1f}mo)")


def main():
    mr = avg_dollar_risk_per_micro()
    print(f"(~micros = $risk/trade / median ${mr:.0f} structure-stop per 1 micro; rough — varies by symbol/stop)")
    run(60, "60th PCTILE (recommended, higher frequency)", mr)
    run(70, "70th PCTILE (deployed / conservative)", mr)
    print(f"\nNOTE: IID bootstrap (real losing streaks cluster on regime days -> optimistic; block-bootstrap "
          f"is the harden step). Fixed-5R exit. P(blow 1st) = hit trailing DD before +$4k.")


if __name__ == "__main__":
    main()
