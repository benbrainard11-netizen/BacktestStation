"""walkforward — honest expanding-window walk-forward of the day-flat SELECTION PROCESS.

The 12-month sealed holdout was consumed by the ES-ORB shot, and no fresh/future data exists. The
rigorous substitute (chosen 2026-06-20): test the whole selection pipeline out-of-sample. For each
test fold, re-run the full bake-off (6 instruments x 5 families x params) on PRIOR-years-only,
deploy whatever the survivor rule would have picked, and measure the result on the next (unseen) year.

Validity note: families.py is LOCAL — a day's trade depends only on that day + the prior ~14 days
(ATR) and the prior RTH close; there are NO whole-window percentile gates. So computing each config's
full trade list once and slicing by date into train/test folds is identical to (and cleaner than)
re-running on bare slices. Selection uses train-fold summary only; OOS = the next-year trades.

  python walkforward.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from families import run_family  # noqa: E402
from orb_engine import build_dataset, get_spec  # noqa: E402
from screen_families import GRID  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
START = "2016-01-01"
DESIGN_END = "2025-06-09"
UNIVERSE = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0", "CL.c.0", "GC.c.0"]

# expanding-window folds (train = START .. train_end; test = the next slice). All within design.
FOLDS = [
    ("2021",   "2021-01-01", "2021-12-31", "2020-12-31"),
    ("2022",   "2022-01-01", "2022-12-31", "2021-12-31"),
    ("2023",   "2023-01-01", "2023-12-31", "2022-12-31"),
    ("2024",   "2024-01-01", "2024-12-31", "2023-12-31"),
    ("2025H1", "2025-01-01", "2025-06-09", "2024-12-31"),
]
FOLD_MIN_N = 60   # per-fold survivor min trade count (train windows are shorter than full design)


def _summ(r: np.ndarray, years: np.ndarray) -> dict:
    if len(r) == 0:
        return {"n": 0}
    half = len(r) // 2
    order = np.argsort(np.argsort(years))  # stable chronological is already by date; use as-is
    k = max(1, int(np.ceil(0.02 * len(r))))
    ex_top = np.sort(r)[: len(r) - k]
    by_year = pd.Series(r).groupby(years).mean()
    return {"n": int(len(r)), "net_R": float(r.mean()), "median_R": float(np.median(r)),
            "win": float((r > 0).mean()), "net_R_h1": float(r[:half].mean()) if half else 0.0,
            "net_R_h2": float(r[half:].mean()) if half else 0.0,
            "worst_year": float(by_year.min()), "net_R_ex_top2pct": float(ex_top.mean())}


def _is_survivor(s: dict) -> bool:
    return (s.get("n", 0) >= FOLD_MIN_N and s["net_R"] > 0 and s["net_R_h1"] > 0 and s["net_R_h2"] > 0
            and s["worst_year"] > -0.20 and s["net_R_ex_top2pct"] > 0)


def main():
    # 1) full trade list per (symbol, family, params) — computed once on the whole design window
    full = {}
    for sym in UNIVERSE:
        spec = get_spec(sym)
        df = build_dataset(sym, START, DESIGN_END)
        for fam, plist in GRID.items():
            for p in plist:
                t = run_family(df, spec, fam, p)
                if len(t):
                    t = t.assign(d=pd.to_datetime(t["date"]))
                    full[(sym, fam, str(p))] = t[["d", "year", "net_R"]].reset_index(drop=True)
        print(f"  loaded {sym}")

    # 2) walk forward: select on train, measure on test
    rows = []
    oos_single = []   # trades from the single best-selected config each fold
    oos_allsurv = []  # trades from ALL survivors each fold (equal-weight by trade)
    for label, ts, te, tr_end in FOLDS:
        ts_, te_, tre_ = pd.Timestamp(ts), pd.Timestamp(te), pd.Timestamp(tr_end)
        cands = []
        for key, t in full.items():
            tr = t[t["d"] <= tre_]
            if len(tr) < FOLD_MIN_N:
                continue
            s = _summ(tr["net_R"].to_numpy(), tr["year"].to_numpy())
            if _is_survivor(s):
                cands.append((key, s["net_R"], s["net_R_ex_top2pct"]))
        # selection = highest train net_R among survivors
        cands.sort(key=lambda x: x[1], reverse=True)
        n_surv = len(cands)
        if not cands:
            rows.append({"fold": label, "n_survivors": 0, "selected": "NONE", "train_net_R": np.nan,
                         "oos_n": 0, "oos_net_R": np.nan, "oos_median_R": np.nan})
            continue
        best_key, best_tr_netR, _ = cands[0]
        bt = full[best_key]
        test = bt[(bt["d"] >= ts_) & (bt["d"] <= te_)]
        oos_single.append(test["net_R"].to_numpy())
        os_ = _summ(test["net_R"].to_numpy(), test["year"].to_numpy())
        rows.append({"fold": label, "n_survivors": n_surv,
                     "selected": f"{best_key[0].split('.')[0]}/{best_key[1]}/{best_key[2]}",
                     "train_net_R": round(best_tr_netR, 4), "oos_n": os_.get("n", 0),
                     "oos_net_R": round(os_.get("net_R", np.nan), 4),
                     "oos_median_R": round(os_.get("median_R", np.nan), 4)})
        for key, _, _ in cands:  # all-survivors portfolio OOS
            ct = full[key]
            ct = ct[(ct["d"] >= ts_) & (ct["d"] <= te_)]
            oos_allsurv.append(ct["net_R"].to_numpy())

    res = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    res.to_csv(OUT / "walkforward.csv", index=False)
    print("\n===== WALK-FORWARD (select on prior years, test on next) =====")
    print(res.to_string(index=False))

    sb = np.concatenate(oos_single) if oos_single else np.array([])
    al = np.concatenate(oos_allsurv) if oos_allsurv else np.array([])
    print("\n--- Pooled OOS: SINGLE best-selected config per fold ---")
    if len(sb):
        print(f"  n={len(sb)}  mean_net_R={sb.mean():+.4f}  median={np.median(sb):+.4f}  win={(sb>0).mean():.3f}  sumR={sb.sum():+.2f}")
        k = max(1, int(np.ceil(0.02 * len(sb))))
        print(f"  ex-top-2% mean={np.sort(sb)[:len(sb)-k].mean():+.4f}")
    else:
        print("  (no deployments)")
    print("\n--- Pooled OOS: ALL survivors equal-weight per fold ---")
    if len(al):
        print(f"  n={len(al)}  mean_net_R={al.mean():+.4f}  median={np.median(al):+.4f}  win={(al>0).mean():.3f}")
    # how often RTY gap_fade was the pick
    picks = [r["selected"] for r in rows if r["selected"] != "NONE"]
    rty_gf = sum(1 for p in picks if p.startswith("RTY/gap_fade"))
    print(f"\nRTY/gap_fade selected in {rty_gf}/{len(picks)} deploying folds. Picks: {picks}")


if __name__ == "__main__":
    main()
