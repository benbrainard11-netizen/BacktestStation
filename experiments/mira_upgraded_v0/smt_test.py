"""Honest SMT signal read: does the STRUCTURAL divergence separate reclaim winners? MBO as enhancement on top.

(1) FILTER -- your literal setup: does a divergence subset beat the flat baseline (OOS, day-block CI)?
(2) GATE   -- structure-first: SMT-only vs MBO-only vs SMT+MBO. Tests your architecture (structure is the
    setup; MBO enhances). Same honest sequenced R + day-block CI as reclaim_entry. Reads events_smt.parquet.
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
from reclaim_entry import OOS_START, TARGET_R, boot, seq_r  # noqa: E402

EV = Path(__file__).resolve().parent / "out" / "events_smt.parquet"


def main() -> int:
    df = pd.read_parquet(EV)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
    df["r"] = seq_r(df, TARGET_R)
    df["fam"] = pd.factorize(df["level_family"])[0]
    smt = [c for c in df.columns if c.startswith("smt.")]
    mbo = [c for c in df.columns if c.startswith("mbo.")]
    OOS_SMT = pd.Timestamp("2026-01-01").date()       # SMT is price-based -> train all 2025, test 2026 (5mo, ~3x OOS)
    oos = df[df["day"] >= OOS_SMT]
    bm, bl, bh = boot(oos["r"].to_numpy(), oos["day"].to_numpy())
    print(f"reclaimed n={len(df)}  OOS(2026, SMT) n={len(oos)}  baseline R {bm:+.2f}[{bl:+.2f},{bh:+.2f}]\n")

    print("(1) divergence FILTERS -- does the literal setup beat baseline? (OOS R [day-block CI], n):")
    filters = {
        "nq pday div": oos["smt.pday.nq.div"] > 0,
        "nq div+sym": (oos["smt.pday.nq.div"] > 0) & (oos["smt.pday.nq.sym"] > 0),
        "ym pday div": oos["smt.pday.ym.div"] > 0,
        "rty pday div": oos["smt.pday.rty.div"] > 0,
        ">=2 partners div": oos["smt.n_div"] >= 2,
        "all 3 div": oos["smt.n_div"] >= 3,
        "no divergence": oos["smt.any_div"] < 1,
    }
    for name, m in filters.items():
        m = m.fillna(False).to_numpy()
        if m.sum() < 15:
            print(f"   {name:18} n<15 ({int(m.sum())})")
            continue
        mm, ll, hh = boot(oos["r"].to_numpy()[m], oos["day"].to_numpy()[m])
        print(f"   {name:18} {mm:+.2f}[{ll:+.2f},{hh:+.2f}] n{int(m.sum())}")

    print("\n(2) POOLED gate -- structure first, then MBO enhancement (OOS R [CI], gated subset):")
    import lightgbm as lgb

    def gate(feats: list[str], label: str, base: pd.DataFrame | None = None, split=OOS_SMT) -> None:
        b = df if base is None else base
        tr, te = b[b["day"] < split], b[b["day"] >= split]
        g = lgb.LGBMClassifier(n_estimators=200, num_leaves=15, learning_rate=0.03, min_child_samples=25,
                               reg_lambda=1.0, random_state=0, verbose=-1)
        g.fit(tr[feats].to_numpy(), (tr["r"] > 0).astype(int).to_numpy())
        p = g.predict_proba(te[feats].to_numpy())[:, 1]
        cells = []
        for q, lab in [(0.50, "top50"), (0.67, "top33")]:
            tk = p >= np.quantile(p, q)
            mm, ll, hh = boot(te["r"].to_numpy()[tk], te["day"].to_numpy()[tk])
            cells.append(f"{lab} {mm:+.2f}[{ll:+.2f},{hh:+.2f}]n{int(tk.sum())}")
        print(f"   {label} " + "  ".join(cells))

    mp = df[df["mbo.pre_60s.n_events"].notna()] if "mbo.pre_60s.n_events" in df.columns else df
    gate(smt + ["fam"], "SMT+fam (25->26)  ")           # full-year power
    gate(mbo + ["fam"], "MBO+fam (26 split) ", mp, OOS_START)   # MBO era only
    gate(smt + mbo + ["fam"], "SMT+MBO (26 split) ", mp, OOS_START)
    print("\nREAD: a filter or gate subset with CI clearly > the flat baseline = structural divergence is real; "
          "SMT+MBO > SMT alone = MBO enhances (your architecture).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
