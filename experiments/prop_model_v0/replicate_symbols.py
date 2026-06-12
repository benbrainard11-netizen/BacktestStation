"""Cross-symbol replication of the recent-era cross-asset signal.

PRE-STATED TEST (before running): the ES no-gx model shows positive fold ICs since
~2024-07, carried by the cross-asset block. If that structure is REAL, the same
feature recipe on NQ / RTY / YM (never modeled — fresh targets, distinct labels)
should ALSO show positive recent-era fold ICs. Pass = recent-era mean fold IC > 0
on at least 2 of 3 fresh symbols WITH the pooled recent-era IC across them positive.
Shuffled control runs on NQ. Labels/protocol identical to ES (day-flat triple-barrier,
purged WF, per-fold IC).

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/replicate_symbols.py
Artifact: report/replication.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from features_index import build  # noqa: E402
from model_wf import fold_ic, run_wf  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

SYMS = ["NQ.c.0", "RTY.c.0", "YM.c.0"]
ERA_START = pd.Timestamp("2024-07-01")


def run_symbol(sym: str, control: bool = False) -> dict:
    tag = sym.split(".")[0].lower()
    fp = MODULE / "data" / f"features_{tag}.parquet"
    if not fp.exists():
        build(sym)
    f = pd.read_parquet(fp)
    feats = [
        c
        for c in f.columns
        if not c.startswith(("y_", "gx_")) and c not in ("rv20_bps", "c_px")
    ]
    y = f["y_tbR"]
    out = {"symbol": sym}
    if control:
        pc, fc = run_wf(f[feats], y, shuffle_target=True)
        mc = pc.notna() & y.notna()
        out["control_ic"] = round(fold_ic(pc, y, fc, mc), 3)
    pr, fr_ = run_wf(f[feats], y, shuffle_target=False)
    mr = pr.notna() & y.notna()
    era = mr & (pd.DatetimeIndex(f.index) >= ERA_START)
    out["ic_full"] = round(fold_ic(pr, y, fr_, mr), 3)
    out["ic_era"] = round(fold_ic(pr, y, fr_, era), 3)
    out["n_era"] = int(era.sum())
    # era decile gross R (both sides) for magnitude
    rows = []
    for fid in sorted(fr_[era].unique()):
        m = era & (fr_ == fid)
        if m.sum() < 25:
            continue
        pb = pr[m]
        hi, lo = pb.quantile(0.9), pb.quantile(0.1)
        rows += [y.loc[d] for d, p_ in pb.items() if p_ >= hi]
        rows += [-y.loc[d] for d, p_ in pb.items() if p_ <= lo]
    out["era_decile_grossR"] = round(float(np.mean(rows)), 3) if rows else np.nan
    out["era_decile_n"] = len(rows)
    print(out)
    return out


def main() -> int:
    rows = [run_symbol(s, control=(s == "NQ.c.0")) for s in SYMS]
    tab = pd.DataFrame(rows)
    n_pos = int((tab["ic_era"] > 0).sum())
    verdict = (
        "REPLICATES"
        if n_pos >= 2 and tab["ic_era"].mean() > 0
        else "FAILS TO REPLICATE"
    )
    lines = [
        "# Cross-symbol replication — recent-era cross-asset signal",
        "",
        tab.to_string(index=False),
        "",
        f"era = {ERA_START.date()}+ | fresh symbols with era IC > 0: {n_pos}/3",
        f"## VERDICT: {verdict}",
        "(pre-stated bar: >=2/3 positive AND mean > 0. Symbols are day-correlated —",
        "this is replication of the FEATURE STRUCTURE, not 3 independent samples.)",
    ]
    (MODULE / "report" / "replication.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print("\n" + "\n".join(lines[2:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
