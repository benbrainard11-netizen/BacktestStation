"""Is the SMT-structure gate real or one lucky split? Walk-forward: expanding-window train, ~2mo test folds
across the full year, pool the gate-selected trades' OOS R + day-block CI. Reads events_smt.parquet.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import TARGET_R, boot, seq_r  # noqa: E402

EV = Path(__file__).resolve().parent / "out" / "events_smt.parquet"
FOLDS = [(date(2025, 10, 1), date(2025, 12, 1)), (date(2025, 12, 1), date(2026, 2, 1)),
         (date(2026, 2, 1), date(2026, 4, 1)), (date(2026, 4, 1), date(2026, 6, 1))]
TOPQ = 0.67


def main() -> int:
    import lightgbm as lgb
    df = pd.read_parquet(EV)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
    df["r"] = seq_r(df, TARGET_R)
    df["fam"] = pd.factorize(df["level_family"])[0]
    feats = [c for c in df.columns if c.startswith("smt.")] + ["fam"]

    sel_r, sel_day, base_r, base_day = [], [], [], []
    print(f"walk-forward SMT-structure gate (top{int((1-TOPQ)*100)}%), expanding train:")
    for ts, te in FOLDS:
        tr = df[df["day"] < ts]
        tef = df[(df["day"] >= ts) & (df["day"] < te)]
        if len(tr) < 150 or len(tef) < 20:
            print(f"   {ts}..{te}: thin (tr={len(tr)} te={len(tef)})")
            continue
        g = lgb.LGBMClassifier(n_estimators=200, num_leaves=15, learning_rate=0.03, min_child_samples=25,
                               reg_lambda=1.0, random_state=0, verbose=-1)
        g.fit(tr[feats].to_numpy(), (tr["r"] > 0).astype(int).to_numpy())
        p = g.predict_proba(tef[feats].to_numpy())[:, 1]
        tk = p >= np.quantile(p, TOPQ)
        fr, fd = tef["r"].to_numpy(), tef["day"].to_numpy()
        sel_r += list(fr[tk]); sel_day += list(fd[tk]); base_r += list(fr); base_day += list(fd)
        print(f"   {ts}..{te}: tr={len(tr)} te={len(tef)}  fold gated meanR {fr[tk].mean():+.2f} (n_take={int(tk.sum())})  "
              f"base {fr.mean():+.2f}")

    bm, bl, bh = boot(np.array(base_r), np.array(base_day, dtype=object))
    gm, gl, gh = boot(np.array(sel_r), np.array(sel_day, dtype=object))
    print(f"\nPOOLED OOS ({len(base_r)} trades, {len(sel_r)} gated):")
    print(f"   baseline      {bm:+.2f}R [{bl:+.2f},{bh:+.2f}]")
    print(f"   SMT-gated     {gm:+.2f}R [{gl:+.2f},{gh:+.2f}]")
    print("\nREAD: gated CI clearly > 0 AND > baseline across pooled folds = the structure gate is real, not one split.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
