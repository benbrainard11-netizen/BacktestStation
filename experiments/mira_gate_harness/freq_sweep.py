"""How to add MORE SETUPS: the drift threshold is a tunable freq<->edge dial. Sweep it (and show
+RTY) on the operating-point universe (reclaim + zone, working families). Report trades/mo + pooled
+ 2025-OOS edge at each setting so Ben can pick a frequency/edge operating point before deploy."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
MONTHS = 13.3  # 2025-05 .. 2026-06


def load(f, syms, fams=None):
    d = pd.read_parquet(RUNS / f)
    d = d[d["symbol"].isin(syms)].copy()
    return d[d["level_family"].isin(fams)] if fams is not None else d


def build(syms):
    std = load("mbp1_stack_features.parquet", syms)
    std = std[std["level_family"] != "opening_range"]
    parts = [std, load("mbp1_stack_ndog_levels_full.parquet", syms),
             load("mbp1_stack_stacked_failure_full.parquet", syms, ["eqhigh_stack"])]
    fc = pd.concat(parts, ignore_index=True)
    fc = fc.drop_duplicates(["symbol", "session_date", "decision_ts_utc", "level_price", "side"])
    fc["drift"] = pd.to_numeric(fc["w90_drift_dir_ticks"], errors="coerce")
    fc["zf"] = fc["zone_5m_has"] == 1
    fc["R"] = pd.to_numeric(fc["trail_2R"], errors="coerce")
    fc = fc[fc["R"].abs() < 50].copy()
    fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
    return fc


def stat(x):
    x = x.dropna()
    return (len(x), x.mean(), 100 * (x > 0).mean()) if len(x) else (0, np.nan, np.nan)


def sweep(fc, syms, label):
    print(f"\n{'='*78}\n{label}  ({'/'.join(s.split('.')[0] for s in syms)})")
    print(f"{'drift pctile':>12s} {'thr(tk/sym)':>22s} {'n':>5s} {'tr/mo':>6s} "
          f"{'pooledR':>8s} {'2025-OOS':>9s} {'win%':>5s}")
    for p in [70, 60, 50, 40, 30, 20, 10, 0]:
        thr = {s: float(np.percentile(fc[(fc.symbol == s) & fc.zf & (fc.yr == 2026)]["drift"].dropna(), p))
               for s in syms if ((fc.symbol == s) & fc.zf & (fc.yr == 2026)).sum() >= 5}
        op = fc[fc.zf & (fc.drift >= fc.symbol.map(thr))]
        n, rp, _ = stat(op["R"])
        no, ro, wo = stat(op[op.yr == 2025]["R"])
        tstr = "/".join(f"{thr.get(s, np.nan):.0f}" for s in syms)
        print(f"{p:>10d}th {tstr:>22s} {n:>5d} {n/MONTHS:>6.1f} {rp:>+8.3f} {ro:>+9.3f} {wo:>5.0f}")
    # reference rows: zone-only (no drift) and all-reclaims (no filter)
    zn, zr, _ = stat(fc[fc.zf]["R"])
    an, ar, _ = stat(fc["R"])
    print(f"  zone-only (no drift): n={zn} ({zn/MONTHS:.0f}/mo) R={zr:+.3f}  | "
          f"all reclaims: n={an} ({an/MONTHS:.0f}/mo) R={ar:+.3f}")


fc3 = build(["ES.c.0", "NQ.c.0", "YM.c.0"])
sweep(fc3, ["ES.c.0", "NQ.c.0", "YM.c.0"], "LIQUID-3 (deployed)")
fc4 = build(["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"])
sweep(fc4, ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"], "ALL-4 (+RTY for frequency)")
print(f"\nNOTE: drift thr is per-symbol pctile of 2026 zone-formed drift (frozen); 2025 is fresh OOS.")
print(f"Lower pctile = more trades, less edge. The deployed op = 70th. RTY adds freq at lower edge.")
