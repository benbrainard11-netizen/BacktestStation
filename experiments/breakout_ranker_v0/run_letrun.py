"""Does LETTING WINNERS RUN rescue it? Same setup + same arm + same initial stop (pivot-1*ATR),
but instead of a fixed +2R target we ride a chandelier trail (highest-high-since-entry minus
TRAIL*ATR) up to a long max hold. This is the classic "cut losers at 1R, let winners run" exit
that breakout traders rely on. We resolve the gated setups AND the matched random null with the
identical let-run mechanic and ask: does the gated setup now beat the null, across years, ex-2020,
after dropping the fat tail? Run with backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import common as C
from build_setups import _is_setup, _ticker_arrays

RNG = np.random.default_rng(0)
CONFIGS = [(3.0, 60), (2.5, 60), (3.0, 120)]  # (trail_atr, max_hold)


def letrun(o, h, l, c, i, pivot, atr_i, trail, hold):
    n = len(c)
    if not (np.isfinite(pivot) and np.isfinite(atr_i) and atr_i > 0):
        return None
    trigger = pivot + C.TRIG_ATR * atr_i
    j = None
    for k in range(i + 1, min(i + 1 + C.TRIG_WIN, n)):
        if h[k] >= trigger:
            j, entry = k, max(trigger, o[k])
            break
    if j is None:
        return None
    stop = (pivot - C.STOP_ATR * atr_i) * (1 - C.STOP_BUF)
    risk = entry - stop
    if risk <= 0:
        return None
    cost_R = 2 * C.FRIC * entry / risk
    cur, run_hi = stop, entry
    end = min(j + hold, n)
    R = (c[end - 1] - entry) / risk
    for k in range(j, end):
        if o[k] <= cur:           # gap-through the trail at the open
            R = (o[k] - entry) / risk
            break
        if l[k] <= cur:
            R = (cur - entry) / risk
            break
        run_hi = max(run_hi, h[k])
        cur = max(cur, run_hi - trail * atr_i)
    grossR = float(np.clip(R, -C.RCAP, C.RCAP))
    return grossR, float(np.clip(grossR - cost_R, -C.RCAP, C.RCAP))


def collect(trail, hold):
    df = C.load_universe()
    g, nrows = [], []
    for t, d in df.groupby("ticker", sort=False):
        if t == "SPY" or len(d) < 280:
            continue
        a = _ticker_arrays(d)
        n = len(a["c"])
        lo_i, hi_i = 252, n - (hold + C.TRIG_WIN + 1)
        if hi_i <= lo_i:
            continue
        liquid = (a["c"] >= C.MIN_PRICE) & np.isfinite(a["dvol"]) & (a["dvol"] >= C.MIN_DVOL)
        setup = np.zeros(n, bool)
        for i in range(lo_i, hi_i):
            if liquid[i]:
                setup[i] = _is_setup(a, i)
        for i in np.where(setup)[0]:
            r = letrun(a["o"], a["h"], a["l"], a["c"], i, a["pivot"][i], a["atr14"][i], trail, hold)
            if r:
                g.append((int(a["dts"][i]) // 10000, *r))
        elig = np.where(liquid & ~setup)[0]
        elig = elig[(elig >= lo_i) & (elig < hi_i)]
        k = int(setup.sum())
        if k and len(elig):
            for jj in RNG.choice(elig, size=min(k, len(elig)), replace=False):
                r = letrun(a["o"], a["h"], a["l"], a["c"], jj, a["pivot"][jj], a["atr14"][jj], trail, hold)
                if r:
                    nrows.append((int(a["dts"][jj]) // 10000, *r))
    return (pd.DataFrame(g, columns=["yr", "grossR", "netR"]),
            pd.DataFrame(nrows, columns=["yr", "grossR", "netR"]))


def report(G, N, trail, hold):
    print(f"\n========== LET-IT-RUN  (chandelier {trail}xATR, max {hold}d) ==========")
    print(f"  GATED  n {len(G):,}  net mean {G['netR'].mean():+.3f}  median {G['netR'].median():+.2f}  "
          f"gross {G['grossR'].mean():+.3f}")
    print(f"  NULL   n {len(N):,}  net mean {N['netR'].mean():+.3f}  median {N['netR'].median():+.2f}  "
          f"gross {N['grossR'].mean():+.3f}")
    print(f"  DELTA net {G['netR'].mean() - N['netR'].mean():+.3f}  gross {G['grossR'].mean() - N['grossR'].mean():+.3f}")
    deltas = []
    for y in sorted(set(G.yr) & set(N.yr)):
        dm = G[G.yr == y]["netR"].mean() - N[N.yr == y]["netR"].mean()
        deltas.append(dm)
    print(f"  by-year net delta>0 in {sum(d>0 for d in deltas)}/{len(deltas)} yrs (mean {np.mean(deltas):+.3f})")
    print(f"  ex-2020 gated net {G[G.yr != 2020]['netR'].mean():+.3f}")
    cut = G["grossR"].quantile(0.99)
    print(f"  drop-top-1% gated gross {G[G['grossR'] < cut]['grossR'].mean():+.3f} (full gross {G['grossR'].mean():+.3f})")
    cutn = N["grossR"].quantile(0.99)
    print(f"  drop-top-1% null  gross {N[N['grossR'] < cutn]['grossR'].mean():+.3f}")


def main():
    for trail, hold in CONFIGS:
        G, N = collect(trail, hold)
        report(G, N, trail, hold)
    print("\nREAD: let-run rescues it ONLY if gated net>0 AND beats the null in MOST years AND ex-2020")
    print("AND survives drop-top-1%. A positive MEAN with a deeply negative MEDIAN + null ~ gated +")
    print("drop-top-1% collapse = a fat-tail lottery, not a breakout edge.")


if __name__ == "__main__":
    main()
