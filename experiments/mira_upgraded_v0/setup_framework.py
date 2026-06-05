"""Run the SETUP REGISTRY through the proven gate + ruler across all 4 assets. Each setup uses its own entry/R;
the SMT/TF-sync gate + walk-forward + day-block CI are identical for all. Answers: at a swept level, does the gate
know REVERSE vs CONTINUE -- and which setup pays where? Reads events_<tag>_tf.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot  # noqa: E402
from setups import SETUPS  # noqa: E402
from smt_economics import wf_gate  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
ASSETS = [("ES", "events_es_tf.parquet"), ("NQ", "events_nq_tf.parquet"),
          ("YM", "events_ym_tf.parquet"), ("RTY", "events_rty_tf.parquet")]
TARGET = 3.0


def main() -> int:
    print(f"SETUP FRAMEWORK @ {TARGET}R -- gated R per (asset x setup), walk-forward pooled OOS:")
    for tag, fn in ASSETS:
        p = OUT / fn
        if not p.exists():
            print(f"  {tag}: {fn} missing")
            continue
        df0 = pd.read_parquet(p)
        df0["day"] = pd.to_datetime(df0["session_date"]).dt.date
        df0["fam"] = pd.factorize(df0["level_family"])[0]
        feats = [c for c in df0.columns if c.startswith("smt_tf.")] + ["fam"]
        cells = []
        for name, (mask_fn, r_fn) in SETUPS.items():
            sub = df0[mask_fn(df0)].reset_index(drop=True)
            if len(sub) < 130:
                cells.append(f"{name}: thin({len(sub)})")
                continue
            r = r_fn(sub, TARGET)
            sel, oos, _, day = wf_gate(sub, feats, TARGET, r=r)
            if oos.sum() < 10 or sel.sum() < 5:
                cells.append(f"{name}: thin-folds({len(sub)})")
                continue
            bm, bl, bh = boot(r[oos], day[oos])
            gm, gl, gh = boot(r[sel], day[sel])
            flag = "*" if gl > 0 else " "
            cells.append(f"{name}: base {bm:+.2f} -> GATE {gm:+.2f}[{gl:+.2f},{gh:+.2f}]{flag} n{int(sel.sum())}")
        print(f"  {tag:4} " + "   ".join(cells))
    print("\nREAD: GATE CI>0 (*) = that setup is tradeable on that asset; compare reverse vs continue per asset.")
    print("NOTE: reverse is fill-verified; continue is bucket-R (own fill-realism pass still TODO).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
