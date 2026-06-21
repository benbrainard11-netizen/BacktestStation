"""STEP-4 validity gate for the 10yr gamma-wall recompute (run AFTER merge_gex_shards.py).

Asserts a freshly-merged out/gex_levels_<idx>.parquet reproduces the snapshotted 2025-26 walls
(out/baseline_2025_26/) byte-identically on the overlap. call_wall/put_wall are argmax/argmin of
net signed GEX by strike -> robust to float-add-order, so they MUST match exactly; total_gex /
zero_gamma may drift in the last digits (sharded sum order differs) and are reported, not asserted.

A wall mismatch == definition drift (wrong builder, wrong WINDOW_DAYS, or missing cache requests)
-> STOP and fix before trusting any deep result.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/recompute_overlap_check.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
BASE = OUT / "baseline_2025_26"
INDICES = ["spx", "djx", "rut", "ndx"]

fail = False
for idx in INDICES:
    bpath, npath = BASE / f"gex_levels_{idx}.parquet", OUT / f"gex_levels_{idx}.parquet"
    if not bpath.exists():
        print(f"{idx:4s}  no baseline snapshot — skip")
        continue
    if not npath.exists():
        print(f"{idx:4s}  no current gex_levels — skip")
        continue
    b = pd.read_parquet(bpath).set_index("date").sort_index()
    n = pd.read_parquet(npath).set_index("date").sort_index()
    common = b.index.intersection(n.index)
    if not len(common):
        print(f"{idx:4s}  NO overlapping dates (current may be deep-only?) — cannot gate")
        continue
    bc, nc = b.loc[common], n.loc[common]
    cw_eq = np.isclose(bc["call_wall"], nc["call_wall"], rtol=0, atol=1e-9)
    pw_eq = np.isclose(bc["put_wall"], nc["put_wall"], rtol=0, atol=1e-9)
    tg_diff = float(np.nanmax(np.abs(bc["total_gex"].to_numpy() - nc["total_gex"].to_numpy())))
    zg_diff = float(np.nanmax(np.abs(bc["zero_gamma"].to_numpy() - nc["zero_gamma"].to_numpy())))
    ok = bool(cw_eq.all() and pw_eq.all())
    fail = fail or not ok
    tag = "PASS" if ok else "*** FAIL ***"
    print(f"{idx:4s}  overlap={len(common):4d}  call_wall match={cw_eq.mean()*100:5.1f}%  "
          f"put_wall match={pw_eq.mean()*100:5.1f}%  | total_gex maxdiff={tg_diff:.3e} "
          f"zero_gamma maxdiff={zg_diff:.3e}  {tag}")
    if not ok:
        mism = common[~(cw_eq & pw_eq)]
        for d in mism[:6]:
            print(f"      mismatch {int(d)}: base cw={bc.loc[d,'call_wall']} pw={bc.loc[d,'put_wall']} "
                  f"vs new cw={nc.loc[d,'call_wall']} pw={nc.loc[d,'put_wall']}")

print("\n" + ("OVERLAP GATE FAILED — definition drift; do NOT trust deep walls" if fail
             else "OVERLAP GATE PASSED — deep recompute is identically-defined to the 2025-26 walls"))
raise SystemExit(1 if fail else 0)
