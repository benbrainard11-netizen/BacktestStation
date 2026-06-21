"""expand — does the intraday-RV edge generalize across cointegrated pairs? + OOS bootstrap.

CL-BZ showed a monotonic high-z RV edge that turns holdout-positive at |z|>=3.5. A single hand-picked
pair is fragile; this runs the SAME construction across index / rates / energy cointegrated pairs and
bootstraps the out-of-sample net. A robust, scalable, automatable day-flat RV strategy needs SEVERAL
pairs clearing cost on design AND holdout, not one.

  python expand.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rv_backtest as R  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
PAIRS = [
    ("index", "ES.c.0", "NQ.c.0"), ("index", "ES.c.0", "YM.c.0"), ("index", "ES.c.0", "RTY.c.0"),
    ("index", "NQ.c.0", "YM.c.0"), ("index", "NQ.c.0", "RTY.c.0"), ("index", "YM.c.0", "RTY.c.0"),
    ("rates", "ZN.c.0", "ZF.c.0"), ("rates", "ZN.c.0", "ZB.c.0"), ("rates", "ZN.c.0", "ZT.c.0"),
    ("rates", "ZF.c.0", "ZB.c.0"), ("rates", "ZF.c.0", "ZT.c.0"), ("rates", "ZB.c.0", "ZT.c.0"),
    ("energy", "CL.c.0", "BZ.c.0"), ("energy", "CL.c.0", "HO.c.0"), ("energy", "CL.c.0", "RB.c.0"),
    ("energy", "HO.c.0", "RB.c.0"), ("energy", "CL.c.0", "NG.c.0"),
]
THRS = [2.5, 3.0, 3.5]
HEADLINE = 3.0


def boot_holdout(t, thr_ok=True, iters=1000):
    de = int(R.DESIGN_END.replace("-", ""))
    h = t[t.date > de]
    if len(h) < 20:
        return (float("nan"), float("nan"), float("nan"))
    days = h.groupby("date")["pnl"].apply(list)
    arr = list(days.values)
    rng = np.random.default_rng(13)
    means = []
    for _ in range(iters):
        samp = rng.integers(0, len(arr), len(arr))
        vals = [x for i in samp for x in arr[i]]
        means.append(np.mean(vals))
    lo, hi = np.percentile(means, [5, 95])
    return (float(lo), float(hi), float(np.mean(np.array(means) > 0)))


def main():
    rows = []
    for cls, a, b in PAIRS:
        try:
            m, sa, sb = R.prepare(a, b)
        except Exception as e:
            print(f"  {a}-{b}: prepare ERR {type(e).__name__}: {str(e)[:60]}", flush=True); continue
        for thr in THRS:
            t = R.simulate(m, sa, sb, entry=thr)
            st = R.split_stats(t)
            row = dict(cls=cls, pair=f"{a.split('.')[0]}-{b.split('.')[0]}", thr=thr,
                       d_n=st["design"]["n"], d_net=st["design"].get("net", float("nan")),
                       h_n=st["holdout"]["n"], h_net=st["holdout"].get("net", float("nan")),
                       h_win=st["holdout"].get("win", float("nan")))
            if thr == HEADLINE:
                lo, hi, pgt0 = boot_holdout(t)
                row.update(h_boot_lo=lo, h_boot_hi=hi, h_p_gt0=pgt0)
            rows.append(row)
        print(f"  done {a.split('.')[0]}-{b.split('.')[0]}", flush=True)
    df = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "rv_expand.csv", index=False)
    print("\n== intraday RV across pairs (net$/trade, design vs holdout) ==")
    for thr in THRS:
        s = df[df.thr == thr].sort_values("h_net", ascending=False)
        print(f"\n-- entry |z|>{thr} --")
        for _, r in s.iterrows():
            extra = (f" boot90[{r.h_boot_lo:+.0f},{r.h_boot_hi:+.0f}] P>0={r.h_p_gt0:.2f}"
                     if thr == HEADLINE and not pd.isna(r.get("h_p_gt0", float("nan"))) else "")
            print(f"  {r.cls:6s} {r.pair:9s} d_net={r.d_net:+7.1f}(n{int(r.d_n)}) "
                  f"h_net={r.h_net:+7.1f}(n{int(r.h_n)},win{r.h_win:.2f}){extra}")
    # generalizers at headline: design>0 AND holdout>0 AND bootstrap P>0 high
    h = df[df.thr == HEADLINE]
    gen = h[(h.d_net > 0) & (h.h_net > 0) & (h.h_p_gt0 > 0.8)]
    print(f"\nGENERALIZERS (|z|>{HEADLINE}, design>0 & holdout>0 & bootP>0.8): "
          f"{list(gen.pair) if len(gen) else 'NONE'}")


if __name__ == "__main__":
    main()
