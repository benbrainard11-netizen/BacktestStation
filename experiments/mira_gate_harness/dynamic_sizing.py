"""DYNAMIC sizing for the funded account: risk a fixed FRACTION of the buffer (distance to the
trailing-DD floor) each trade, instead of a fixed $. Aggressive with cushion, auto-de-risks near the
floor -> can't blow up in one trade. Compare the speed-vs-survival frontier to fixed sizing, to +$4k.
Buffer = balance - floor; floor = peak-2000 (trails) until peak>=+2100 then locks at 0 (breakeven).
Contracts are discrete so $size is clamped to [1 micro ~ $14, MAX]."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prop_sizing as PS  # noqa: E402

MONTHS = 13.3
N_MC = 12000
TARGET, DD, LOCK = 4000.0, 2000.0, 2100.0
MAX_TRADES = 1500
MIN_SZ, MAX_SZ = 14.0, 600.0  # 1 micro .. cap (~firm max contracts)


def sim(Rs, size_fn, rng):
    idx = rng.integers(0, len(Rs), MAX_TRADES)
    bal = peak = 0.0
    for t in range(MAX_TRADES):
        floor = 0.0 if peak >= LOCK else (peak - DD)
        size = min(MAX_SZ, max(MIN_SZ, size_fn(bal - floor, bal)))
        bal += Rs[idx[t]] * size
        peak = max(peak, bal)
        floor = 0.0 if peak >= LOCK else (peak - DD)
        if bal <= floor:
            return None, True
        if bal >= TARGET:
            return t + 1, False
    return None, False


def stats(Rs, size_fn, freq):
    rng = np.random.default_rng(7)
    hit, blew, tt = 0, 0, []
    for _ in range(N_MC):
        t, b = sim(Rs, size_fn, rng)
        if t is not None:
            hit += 1; tt.append(t)
        elif b:
            blew += 1
    med = np.median(tt) if tt else np.nan
    return hit / N_MC, blew / N_MC, med, (med / freq if med == med else np.nan)


def main():
    Rs = PS.build_r_series(pct=60)
    freq = len(Rs) / MONTHS
    print(f"60th-pctile op: n={len(Rs)} meanR={Rs.mean():+.3f} ~{freq:.0f}/mo; target +$4k, "
          f"DD $2000 lock@+$2100, size clamp [${MIN_SZ:.0f},${MAX_SZ:.0f}]\n")

    print(f"{'model':32s} {'P(hit $4k)':>11s} {'P(blow 1st)':>12s} {'median time':>18s}")
    print("-" * 76)
    print("FIXED $/trade:")
    for s in (100, 150, 200, 250, 300):
        p, pb, med, mo = stats(Rs, (lambda v, b, s=s: s), freq)
        print(f"  fixed ${s:<25d} {100*p:>10.0f}% {100*pb:>11.0f}% {med:>5.0f}tr (~{mo:>4.1f}mo)")
    print("\nDYNAMIC: risk f% of buffer (distance to DD floor):")
    for f in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30):
        p, pb, med, mo = stats(Rs, (lambda v, b, f=f: f * v), freq)
        print(f"  frac {int(f*100):>2d}% of buffer{'':>11s} {100*p:>10.0f}% {100*pb:>11.0f}% "
              f"{med:>5.0f}tr (~{mo:>4.1f}mo)")
    print("\nDYNAMIC + LOCK-LATE: f% of buffer, but halve size within $800 of target (bank the win):")
    for f in (0.15, 0.20, 0.25):
        def sf(v, b, f=f):
            base = f * v
            return base * 0.5 if b >= TARGET - 800 else base
        p, pb, med, mo = stats(Rs, sf, freq)
        print(f"  frac {int(f*100):>2d}% + lock-late{'':>9s} {100*p:>10.0f}% {100*pb:>11.0f}% "
              f"{med:>5.0f}tr (~{mo:>4.1f}mo)")
    print(f"\nNOTE: IID bootstrap (optimistic vs real daily clustering). Frontier comparison: a dynamic "
          f"model WINS if it gives higher P(hit) AND/OR faster time at lower P(blowup) than any fixed row.")


if __name__ == "__main__":
    main()
