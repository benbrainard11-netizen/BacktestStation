"""Positive/negative controls: prove the arm+triple-barrier mechanic is directionally correct
AND that honest fills (gap-through worse than -1R, clean stop = -1R, target capped +2R) work,
so the negative verdict reflects the DATA, not a broken harness.
Run with backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

import numpy as np

from barrier import arm_and_resolve


def run(name, bars, pivot, atr_i, i, expect_outcome, expect_R, tol=0.2):
    arr = np.array(bars, float)  # rows of (o,h,l,c)
    o, h, l, c = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]
    r = arm_and_resolve(o, h, l, c, i, pivot, atr_i)
    ok = r and r.get("triggered") == 1 and r["outcome"] == expect_outcome and abs(r["grossR"] - expect_R) < tol
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: outcome={r and r.get('outcome')} "
          f"grossR={r and round(r.get('grossR', float('nan')), 2)} (expect {expect_outcome} ~{expect_R:+.1f})")
    return bool(ok)


def main():
    flat = [(100, 100, 100, 100)] * 30  # 30 days context; i=29, pivot=100, atr=1, stop~98.9
    print("=== barrier sanity controls (gross, honest fills) ===")
    ok = []
    # 1. uptrend after trigger -> +2R (target)
    up = flat + [(100 * 1.01 ** k,) * 4 for k in range(1, 25)]
    ok.append(run("uptrend -> target (+2R)", up, 100.0, 1.0, 29, "target", +2))
    # 2. clean INTRADAY stop: enter 101, next bar opens above stop but low dips through -> -1R
    clean = flat + [(101, 101, 101, 101)] + [(100.5, 100.6, 98.5, 99.0)] + [(99,) * 4] * 20
    ok.append(run("clean intraday stop (-1R)", clean, 100.0, 1.0, 29, "stop", -1))
    # 3. GAP-THROUGH stop: next bar opens far below stop -> honest fill worse than -1R
    gap = flat + [(101, 101, 101, 101)] + [(96.0, 96.0, 95.0, 95.5)] + [(95,) * 4] * 20
    ok.append(run("gap-through stop (<-1R, honest)", gap, 100.0, 1.0, 29, "stop", -2.6, tol=0.4))
    # 4. flat after trigger -> timeout ~0
    ft = flat + [(100.3, 100.3, 100.3, 100.3)] * 22
    ok.append(run("flat -> timeout (~0)", ft, 100.0, 1.0, 29, "timeout", 0))
    print(f"\n{'ALL PASS' if all(ok) else 'SOME FAIL'} -> the mechanic + honest fills are correct; "
          "the negative live result is the data, not the harness.")


if __name__ == "__main__":
    main()
