"""Generalization + power: run the proven SMT-magnitude gate @2.5R with each index as PRIMARY (ES/NQ/YM/RTY,
each reads the other three as SMT partners). Does the +0.21R edge hold across the complex, or is it an ES artifact?
Computes SMT per primary (cached), walk-forward gate, pooled OOS R + day-block CI. Needs events_<tag>_full.parquet.
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
from smt_economics import wf_gate  # noqa: E402
from smt_features import build_smt  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
PRIMARIES = [("es", "ES.c.0", "events_fullyear.parquet"), ("nq", "NQ.c.0", "events_nq_full.parquet"),
             ("ym", "YM.c.0", "events_ym_full.parquet"), ("rty", "RTY.c.0", "events_rty_full.parquet")]
TARGET = 2.5


def main() -> int:
    print(f"SMT-magnitude gate @ {TARGET}R across the index complex (walk-forward pooled OOS):")
    rows = []
    for tag, sym, fn in PRIMARIES:
        reg = OUT / fn
        if not reg.exists():
            print(f"   {tag.upper():4} regen {fn} missing -- skip")
            continue
        smt_path = OUT / f"events_{tag}_smt.parquet"
        if smt_path.exists():
            df = pd.read_parquet(smt_path)
        else:
            df = build_smt(pd.read_parquet(reg), sym)
            df.to_parquet(smt_path)
        df["day"] = pd.to_datetime(df["session_date"]).dt.date
        df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
        df["fam"] = pd.factorize(df["level_family"])[0]
        feats = [c for c in df.columns if c.startswith("smt.")] + ["fam"]
        sel, oos, r, day = wf_gate(df, feats, TARGET)
        bm, bl, bh = boot(r[oos], day[oos])
        gm, gl, gh = boot(r[sel], day[sel])
        flag = "  <== clears 0" if gl > 0 else ""
        print(f"   {tag.upper():4} reclaimed={len(df):4}  base {bm:+.2f}[{bl:+.2f},{bh:+.2f}]  "
              f"GATED {gm:+.2f}[{gl:+.2f},{gh:+.2f}] n{int(sel.sum())}{flag}")
        rows.append((tag, gm, gl, bm))
    if rows:
        pooled_g = np.mean([g for _, g, _, _ in rows])
        clears = sum(gl > 0 for _, _, gl, _ in rows)
        print(f"\nacross {len(rows)} primaries: mean gated {pooled_g:+.2f}R, {clears}/{len(rows)} clear 0")
    print("READ: edge holding across primaries (gated>base, several clearing 0) = real, not an ES artifact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
