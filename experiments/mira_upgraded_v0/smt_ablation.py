"""v2 ablation: does FVG-fill or gap-fill divergence GROW the classic-SMT gate's +0.21R @2.5R?
Same walk-forward + day-block CI ruler. Each fill type added separately (your "which type works"). Reads events_smtfill.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot  # noqa: E402
from smt_economics import wf_gate  # noqa: E402  (walk-forward gate, target-parameterized)

EV = Path(__file__).resolve().parent / "out" / "events_smtfill.parquet"
TARGET = 2.5


def main() -> int:
    df = pd.read_parquet(EV).reset_index(drop=True)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
    df["fam"] = pd.factorize(df["level_family"])[0]
    classic = [c for c in df.columns if c.startswith("smt.")]
    fvg = [c for c in df.columns if c.startswith("smt_fvg.")]
    gap = [c for c in df.columns if c.startswith("smt_gap.")]

    configs = {
        "classic+fam (base)": classic + ["fam"],
        "+FVG": classic + fvg + ["fam"],
        "+gap": classic + gap + ["fam"],
        "+FVG+gap (all)": classic + fvg + gap + ["fam"],
        "FVG only": fvg + ["fam"],
        "gap only": gap + ["fam"],
    }
    print(f"v2 ablation @ {TARGET}R, walk-forward pooled OOS, SMT-gated R [day-block CI]:")
    for name, feats in configs.items():
        sel, oos, r, day = wf_gate(df, feats, TARGET)
        gm, gl, gh = boot(r[sel], day[sel])
        flag = "  <== clears 0" if gl > 0 else ""
        print(f"   {name:20} {gm:+.2f}R [{gl:+.2f},{gh:+.2f}] wr{(r[sel] > 0).mean():.2f} n{int(sel.sum())}{flag}")
    print("\nREAD: a config clearly above classic+fam = that fill type adds orthogonal signal (your 'which type works').")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
