"""Iteration 2A: decision-layer economics on FROZEN v1 labels.

Tests ONLY: nested per-fold calibration (none/isotonic/sigmoid), payoff-ratio cap
(selection-side), nested EV_MIN (chosen on each fold's calibration segment), ranking
quality, residual-edge-over-geometry. Labels/objectives/features/splits/costs/holdout
untouched. Options stay quarantined.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\model_v2a.py
Output: out/report_v2a.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calib_lib as CL
import common as C
import eval_lib as E
from model_v1 import day_shuffle_mbp

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(13)
MODELS = {"B fut+geo": ("geo_", "fut_"), "D fut+geo+mbp": ("geo_", "fut_", "mbp_")}
METHODS = ("none", "isotonic", "sigmoid")


def calibrate_folds(folds: list[dict], method: str):
    """Apply nested calibration; returns (folds_cal, pooled_te, n_unstable)."""
    out, pooled, unstable = [], [], 0
    pcols = ["p_dn", "p_up", "p_none"]
    for seg in folds:
        cal, te = seg["cal"].copy(), seg["te"].copy()
        fitrows = cal[cal["y"] >= 0]
        fn, bad = CL.make_calibrator(fitrows[pcols].to_numpy(), fitrows["y"].to_numpy(), method)
        unstable += bad
        for fr in (cal, te):
            fr[pcols] = fn(fr[pcols].to_numpy())
        out.append({"cal": cal, "te": te})
        pooled.append(te)
    return out, pd.concat(pooled, ignore_index=True), unstable


def run_cell(folds_cal: list[dict], cap: float | None):
    """Nested threshold per fold -> pooled OOS trades + chosen thresholds."""
    trades, thrs = [], []
    for seg in folds_cal:
        thr = CL.pick_threshold(seg["cal"], cap)
        thrs.append(thr)
        te = CL.ev_frame(seg["te"], cap)
        t = te[te["edge"] >= thr].copy()
        t["r"] = CL.chosen_r(t)
        trades.append(t)
    return pd.concat(trades, ignore_index=True), thrs


def top_q_table(te_pool: pd.DataFrame, cap: float | None) -> dict:
    r = CL.ev_frame(te_pool, cap)
    r["r"] = CL.chosen_r(r)
    r = r.dropna(subset=["r"])
    out = {}
    for q, tag in ((0.9, "top10%"), (0.95, "top5%"), (0.98, "top2%")):
        thr = r.groupby("fold")["edge"].transform(lambda s: s.quantile(q))
        t = r[r["edge"] >= thr]
        out[tag] = (float(t["r"].mean()), int(len(t)))
    r["decile"] = r.groupby("fold")["edge"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 10, labels=False))
    edd, edu = r["entry"] - r["obj_dn"], r["obj_up"] - r["entry"]
    r["cost_r"] = np.where(r["side_long"], C.COST_PTS / edd, C.COST_PTS / edu)
    g = r.groupby("decile")
    out["deciles"] = pd.DataFrame({"net_r": g["r"].mean(), "gross_r": g["r"].mean() + g["cost_r"].mean(),
                                   "n": g.size()})
    from scipy.stats import spearmanr
    out["fold_spearman"] = {int(k): round(float(spearmanr(gg["edge"], gg["r"]).statistic), 3)
                            for k, gg in r.groupby("fold")}
    return out


def fmt(ev: dict) -> str:
    if "note" in ev:
        return f"n={ev['n']} ({ev['note']})"
    return (f"n={ev['n']:>4} meanR={ev['mean_r']:+.3f} med={ev['median_r']:+.3f} "
            f"gross={ev['gross_mean_r']:+.3f} win={ev['win']:.0%} PF={ev['pf']:.2f} "
            f"DD={ev['max_dd']:+.0f} CI=[{ev['ci'][0]:+.3f},{ev['ci'][1]:+.3f}] "
            f"mo+{ev['pos_months']}/{ev['months']} folds+{ev['pos_folds']}/{ev['n_folds']} "
            f"days%={ev['pct_days_traded']:.0%}")


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_v0.parquet").reset_index(drop=True)
    mbp = pd.read_parquet(OUT / "mbp_features_v0.parquet")
    df = df.merge(mbp, on=["date", "ms"], how="left")
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    y = df["y"].to_numpy()
    feats = {p: [c for c in df.columns if c.startswith(p)] for p in ("geo_", "fut_", "mbp_")}
    lines = ["# fuhhhhh 2A report — decision economics on frozen v1 labels\n"]
    print(f"{len(df)} rows; nested calibration (CAL_D={CL.CAL_D}d) + caps {CL.CAPS} + "
          f"nested EV_MIN grid {CL.EV_GRID}")

    cells, te_pools, folds_by_model = {}, {}, {}
    for mname, prefixes in MODELS.items():
        cols = [c for p in prefixes for c in feats[p]]
        folds = CL.fold_predictions(df, cols, y)
        folds_by_model[mname] = folds
        for method in METHODS:
            fc, te_pool, unstable = calibrate_folds(folds, method)
            te_pools[(mname, method)] = (fc, te_pool)
            res = te_pool[te_pool["y"] >= 0]
            p = res[["p_dn", "p_up", "p_none"]].to_numpy()
            ll = float(-np.mean(np.log(np.clip(np.take_along_axis(
                p, res["y"].to_numpy()[:, None], axis=1), 1e-9, 1))))
            br = float(np.mean(((p - np.eye(3)[res["y"].to_numpy()]) ** 2).sum(axis=1)))
            note = f" UNSTABLE x{unstable}" if (method == "isotonic" and unstable) else ""
            print(f"\n[{mname} | {method}] ll={ll:.4f} brier={br:.4f}{note}")
            lines.append(f"\n## {mname} | {method} (ll={ll:.4f} brier={br:.4f}{note})\n")
            for cap in CL.CAPS:
                trades, thrs = run_cell(fc, cap)
                ev = CL.pooled_metrics(trades, len(te_pool), te_pool)
                cells[(mname, method, cap)] = (trades, ev, thrs)
                cap_s = "uncap" if cap is None else f"cap{cap}"
                print(f"  {cap_s:<7} thr={thrs} {fmt(ev)}")
                lines.append(f"- {cap_s} thr={thrs}: {fmt(ev)}\n")

    # best cell per model (n>=100), full diagnostics
    lines.append("\n# Best-cell diagnostics\n")
    best = {}
    for mname in MODELS:
        ok = {k: v for k, v in cells.items() if k[0] == mname and "note" not in v[1] and v[1]["n"] >= 100}
        k = max(ok, key=lambda k: ok[k][1]["mean_r"])
        best[mname] = k
        trades, ev, thrs = cells[k]
        dd = CL.drop_days(trades)
        d1 = trades.copy()
        d1["r"] = CL.chosen_r(d1, "_d1")
        d1m = float(d1["r"].dropna().mean())
        print(f"\n== BEST {mname}: {k[1]}/{k[2]} ==\n  {fmt(ev)}")
        print(f"  drop_best5 {dd['drop_best5']:+.3f}  drop_both5 {dd['drop_both5']:+.3f}  "
              f"delayed_entry {d1m:+.3f}")
        lines.append(f"\n## BEST {mname} = {k[1]}/cap={k[2]}\n{fmt(ev)}\n"
                     f"drop_best5={dd['drop_best5']:+.3f} drop_both5={dd['drop_both5']:+.3f} "
                     f"delayed={d1m:+.3f}\nmonthly:\n{ev['monthly'].to_string()}\n")
        tq = top_q_table(te_pools[(mname, k[1])][1], k[2])
        print(f"  top10% {tq['top10%']}  top5% {tq['top5%']}  top2% {tq['top2%']}")
        print(f"  fold spearman(edge,r): {tq['fold_spearman']}")
        lines.append(f"top10%={tq['top10%']} top5%={tq['top5%']} top2%={tq['top2%']}\n"
                     f"fold_spearman={tq['fold_spearman']}\nEV deciles (gross+net):\n"
                     f"{tq['deciles'].round(4).to_string()}\n")

    # calibration curve + residual edge (calibrated, best method per model)
    for mname in MODELS:
        _, te_pool = te_pools[(mname, best[mname][1])]
        lines.append(f"\n## calibration curve {mname} ({best[mname][1]})\n"
                     f"{E.calibration_table(te_pool).round(3).to_string()}\n")
        tab = CL.residual_edge_table(te_pool)
        print(f"\n-- residual edge {mname} ({best[mname][1]}): top-2-decile by fold:")
        print(tab.attrs["top2_by_fold"].round(3).to_string())
        print(f"   deciles 8-9 net: {tab['net_r'].iloc[8]:+.3f}/{tab['net_r'].iloc[9]:+.3f}  "
              f"gross: {tab['gross_r'].iloc[8]:+.3f}/{tab['gross_r'].iloc[9]:+.3f}  "
              f"top2 delayed={tab.attrs['top2_d1']:+.3f}")
        lines.append(f"\n## residual edge {mname}\n{tab.round(4).to_string()}\n"
                     f"top2_by_fold:\n{tab.attrs['top2_by_fold'].round(3).to_string()}\n"
                     f"top2_delayed={tab.attrs['top2_d1']:+.3f}\n")

    # G: shuffled-target through the FULL nested pipeline (best D config)
    mname = "D fut+geo+mbp"
    cols = [c for p in MODELS[mname] for c in feats[p]]
    y_sh = y.copy()
    RNG.shuffle(y_sh)
    g_folds = CL.fold_predictions(df, cols, y_sh)
    g_fc, g_pool, _ = calibrate_folds(g_folds, best[mname][1])
    g_tr, _ = run_cell(g_fc, best[mname][2])
    g_ev = CL.pooled_metrics(g_tr, len(g_pool), g_pool)
    print(f"\n== G shuffled-target (full nested pipeline) ==  meanR={g_ev['mean_r']:+.3f} "
          f"n={g_ev['n']} (FAIL if positive)")
    lines.append(f"\n## G shuffled-target\nmeanR={g_ev['mean_r']:+.3f} n={g_ev['n']}\n")
    if g_ev["n"] > 50 and g_ev["mean_r"] > 0.03:
        print("FAIL  nested machinery manufactured positive R from shuffled labels")

    # H: day-shuffled MBP through the full pipeline (best D config)
    h_df = day_shuffle_mbp(df, feats["mbp_"])
    h_folds = CL.fold_predictions(h_df, cols, y)
    h_fc, h_pool, _ = calibrate_folds(h_folds, best[mname][1])
    h_tr, _ = run_cell(h_fc, best[mname][2])
    h_ev = CL.pooled_metrics(h_tr, len(h_pool), h_pool)
    print(f"== H day-shuffled MBP ==  meanR={h_ev['mean_r']:+.3f} ll={h_ev['logloss']:.4f} "
          f"(expect ~= B cell, not ~= D cell)")
    lines.append(f"\n## H day-shuffled MBP\n{fmt(h_ev)} ll={h_ev['logloss']:.4f}\n")

    (OUT / "report_v2a.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nreport -> {OUT / 'report_v2a.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
