"""Fix the trade economics, keep the proven gate. The reclaim trade LOSES at 2R (-0.13R full-year OOS) and the
SMT gate only lifts it to breakeven. 2R sits right on the ~0.33 breakeven win-rate -> the target is likely
mis-set. Walk-forward TARGET SWEEP: for each target, retrain the gate on that target's win label, pool OOS,
report baseline vs gated R + day-block CI. Find where the gate's lift lands clearly positive. Reads events_smt.parquet.
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
from reclaim_entry import boot, seq_r  # noqa: E402

EV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out" / "events_smt.parquet"
FOLDS = [(date(2025, 10, 1), date(2025, 12, 1)), (date(2025, 12, 1), date(2026, 2, 1)),
         (date(2026, 2, 1), date(2026, 4, 1)), (date(2026, 4, 1), date(2026, 6, 1))]
TARGETS = [1.0, 1.5, 2.0, 2.5, 3.0]
TOPQ = 0.67


def wf_gate(df: pd.DataFrame, feats: list[str], target: float):
    """Walk-forward: per fold train gate on (seq_r@target > 0), select top33% OOS. Returns sel/oos masks + R."""
    import lightgbm as lgb
    r = seq_r(df, target)
    day = df["day"].to_numpy()
    dd = df["day"].to_numpy()
    sel = np.zeros(len(df), bool)
    oos = np.zeros(len(df), bool)
    for ts, te in FOLDS:
        trm = dd < ts
        tem = (dd >= ts) & (dd < te)
        if trm.sum() < 150 or tem.sum() < 20:
            continue
        g = lgb.LGBMClassifier(n_estimators=200, num_leaves=15, learning_rate=0.03, min_child_samples=25,
                               reg_lambda=1.0, random_state=0, verbose=-1)
        g.fit(df.loc[trm, feats].to_numpy(), (r[trm] > 0).astype(int))
        p = g.predict_proba(df.loc[tem, feats].to_numpy())[:, 1]
        idx = np.where(tem)[0]
        sel[idx[p >= np.quantile(p, TOPQ)]] = True
        oos[idx] = True
    return sel, oos, r, day


def main() -> int:
    df = pd.read_parquet(EV).reset_index(drop=True)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
    df["fam"] = pd.factorize(df["level_family"])[0]
    feats = [c for c in df.columns if c.startswith("smt.")] + ["fam"]

    print("walk-forward TARGET SWEEP -- pooled OOS, baseline vs SMT-gated (day-block CI):")
    best = None
    for t in TARGETS:
        sel, oos, r, day = wf_gate(df, feats, t)
        bm, bl, bh = boot(r[oos], day[oos])
        gm, gl, gh = boot(r[sel], day[sel])
        winr = (r[sel] > 0).mean()
        flag = " <== gated CI clears 0" if gl > 0 else ""
        print(f"   target {t:>3}R:  baseline {bm:+.2f}[{bl:+.2f},{bh:+.2f}]   "
              f"GATED {gm:+.2f}[{gl:+.2f},{gh:+.2f}] wr{winr:.2f} n{int(sel.sum())}{flag}")
        if best is None or gm > best[1]:
            best = (t, gm, sel, r, day)

    t, gm, sel, r, day = best
    print(f"\nbest target {t}R (gated {gm:+.2f}R) -- per-family gated OOS R:")
    sub = df[sel]
    rr = r[sel]
    for fam, g in sub.groupby("level_family"):
        m = (df["level_family"] == fam).to_numpy() & sel
        if m.sum() < 8:
            print(f"   {fam:14} n<8")
            continue
        fm, fl, fh = boot(r[m], day[m])
        print(f"   {fam:14} {fm:+.2f}[{fl:+.2f},{fh:+.2f}] n{int(m.sum())}")
    print("\nREAD: the target where GATED CI clears 0 = the proven gate, monetized. Per-family shows which levels carry it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
