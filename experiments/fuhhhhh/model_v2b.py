"""Iteration 2B: re-lock baselines + candidate on the v2 economic-filter datasets.

Decision layer carried from 2A's pre-registered winner: nested isotonic calibration +
payoff cap 1.5 + nested EV_MIN (cap variants {None, 3.0} reported for the candidate so
nothing is hidden). Options stay quarantined (E/F diagnostic only). Controls: G
shuffled-target, H day-shuffled MBP, delayed entry, drop-days. Residual-edge tables,
regime splits incl. cost-burden and MBP-signal strength.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\model_v2b.py v2_c006
Output: out/report_<tag>.md
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
from model_v2a import calibrate_folds, run_cell, top_q_table, fmt

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(17)
METHOD, CAP = "isotonic", 1.5  # 2A's pre-registered winner
ABLATIONS = {
    "A geometry": ("geo_",),
    "B futures+geo": ("geo_", "fut_"),
    "C mbp+geo": ("geo_", "mbp_"),
    "D fut+geo+mbp [candidate]": ("geo_", "fut_", "mbp_"),
    "E options+geo [diag]": ("geo_", "opt_"),
    "F all [diag]": ("geo_", "fut_", "opt_", "mbp_"),
}


def load_v2(tag: str) -> pd.DataFrame:
    df = pd.read_parquet(OUT / f"dataset_{tag}.parquet").reset_index(drop=True)
    mbp = pd.read_parquet(OUT / f"mbp_features_{tag}.parquet")
    inter = ["mbp_svz_x_invup", "mbp_svz_x_invdn", "mbp_tbi_x_invup", "mbp_tbi_x_invdn"]
    df = df.merge(mbp.drop(columns=[c for c in inter if c in mbp.columns]),
                  on=["date", "ms"], how="left")
    # objective-relative interactions recomputed against THIS dataset's objectives
    df["mbp_svz_x_invup"] = df["mbp_sv_1m_z"] / (df["geo_dist_up"] + 0.1)
    df["mbp_svz_x_invdn"] = -df["mbp_sv_1m_z"] / (df["geo_dist_dn"] + 0.1)
    df["mbp_tbi_x_invup"] = df["mbp_tbi"] / (df["geo_dist_up"] + 0.1)
    df["mbp_tbi_x_invdn"] = -df["mbp_tbi"] / (df["geo_dist_dn"] + 0.1)
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    return df


def dataset_comparison(df: pd.DataFrame, tag: str) -> str:
    v1 = pd.read_parquet(OUT / "dataset_v0.parquet", columns=["date", "y", "entry", "obj_up", "obj_dn"])
    et_h = df["ms"] / 3600_000
    sess = pd.cut(et_h, [9, 11.5, 14, 16.1], labels=["morning", "midday", "afternoon"]).value_counts()
    return (f"v1 rows={len(v1)} vs {tag} rows={len(df)} (days {df['date'].nunique()})\n"
            f"classes dn/up/neither: {df['y'].value_counts().sort_index().to_dict()} "
            f"(v1 timeout rate {(v1['y'] == 2).mean():.1%} -> {tag} {(df['y'] == 2).mean():.1%})\n"
            f"median dist up/dn pts: {df['dist_up_pts'].median():.1f}/{df['dist_dn_pts'].median():.1f} "
            f"(v1: {(v1['obj_up'] - v1['entry']).median():.2f}/{(v1['entry'] - v1['obj_dn']).median():.2f})\n"
            f"median cost_to_up/dn: {df['cost_to_up'].median():.4f}/{df['cost_to_dn'].median():.4f} "
            f"(v1: {(C.COST_PTS / (v1['obj_up'] - v1['entry'])).median():.4f}/"
            f"{(C.COST_PTS / (v1['entry'] - v1['obj_dn'])).median():.4f})\n"
            f"median mins_to_resolve: {df['mins_to_resolve'].median():.0f}\n"
            f"session distribution: {sess.to_dict()}\n")


def split_table(trades: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    cols = df[["date", "ms", "fut_rv_30m", "cost_to_dn", "mbp_sv_1m_z", "geo_dist_up", "geo_dist_dn"]]
    t = trades.merge(cols, on=["date", "ms"], how="left").dropna(subset=["r"])
    et_h = t["ms"] / 3600_000
    near = np.minimum(t["geo_dist_up"], t["geo_dist_dn"])
    sigstr = t["mbp_sv_1m_z"].abs()
    splits = {
        "morning": et_h < 11.5, "midday": (et_h >= 11.5) & (et_h < 14), "afternoon": et_h >= 14,
        "near obj": near <= near.median(), "far obj": near > near.median(),
        "high rv30": t["fut_rv_30m"] > t["fut_rv_30m"].median(),
        "low rv30": t["fut_rv_30m"] <= t["fut_rv_30m"].median(),
        "high cost burden": t["cost_to_dn"] > t["cost_to_dn"].median(),
        "low cost burden": t["cost_to_dn"] <= t["cost_to_dn"].median(),
        "strong mbp signal": sigstr > sigstr.median(), "weak mbp signal": sigstr <= sigstr.median(),
    }
    rows = [{"split": k, "mean_r": float(t.loc[m, "r"].mean()), "n": int(m.sum())}
            for k, m in splits.items() if m.sum() >= 25]
    return pd.DataFrame(rows).set_index("split")


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "v2_c006"
    df = load_v2(tag)
    y = df["y"].to_numpy()
    feats = {p: [c for c in df.columns if c.startswith(p)] for p in ("geo_", "fut_", "opt_", "mbp_")}
    comp = dataset_comparison(df, tag)
    print(f"=== {tag} ===\n{comp}")
    lines = [f"# fuhhhhh 2B report — {tag} (decision layer: {METHOD}/cap{CAP}, nested EV_MIN)\n",
             f"## dataset comparison\n{comp}\n"]

    cells = {}
    for name, prefixes in ABLATIONS.items():
        cols = [c for p in prefixes for c in feats[p]]
        folds = CL.fold_predictions(df, cols, y)
        fc, te_pool, _ = calibrate_folds(folds, METHOD)
        trades, thrs = run_cell(fc, CAP)
        ev = CL.pooled_metrics(trades, len(te_pool), te_pool)
        cells[name] = (trades, ev, te_pool, fc)
        print(f"== {name} ({len(cols)}f) ==  {fmt(ev)}  ll={ev.get('logloss', float('nan')):.4f}"
              if "note" not in ev else f"== {name} ==  {fmt(ev)}")
        lines.append(f"\n## {name}\nthr={thrs} {fmt(ev)} ll={ev.get('logloss', float('nan')):.4f} "
                     f"brier={ev.get('brier', float('nan')):.4f}\n"
                     + (f"monthly:\n{ev['monthly'].to_string()}\n" if "note" not in ev else ""))

    cand = "D fut+geo+mbp [candidate]"
    # candidate cap variants — nothing hidden
    for cap_v in (None, 3.0):
        tr_v, _ = run_cell(cells[cand][3], cap_v)
        ev_v = CL.pooled_metrics(tr_v, len(cells[cand][2]), cells[cand][2])
        print(f"  [candidate cap={cap_v}]  {fmt(ev_v)}")
        lines.append(f"\ncandidate cap={cap_v}: {fmt(ev_v)}\n")

    # ranking + robustness on champion + candidate
    for name in ("B futures+geo", cand):
        trades, ev, te_pool, _ = cells[name]
        if "note" in ev:
            continue
        tq = top_q_table(te_pool, CAP)
        dd = CL.drop_days(trades)
        d1 = trades.copy()
        d1["r"] = CL.chosen_r(d1, "_d1")
        print(f"\n-- {name}: top10% {tq['top10%']} top5% {tq['top5%']} top2% {tq['top2%']}")
        print(f"   fold spearman: {tq['fold_spearman']}  drop_best5={dd['drop_best5']:+.3f} "
              f"delayed={float(d1['r'].dropna().mean()):+.3f}")
        lines.append(f"\n## ranking {name}\ntop10%={tq['top10%']} top5%={tq['top5%']} "
                     f"top2%={tq['top2%']}\nfold_spearman={tq['fold_spearman']}\n"
                     f"drop_best5={dd['drop_best5']:+.3f} drop_both5={dd['drop_both5']:+.3f} "
                     f"delayed={float(d1['r'].dropna().mean()):+.3f}\n"
                     f"EV deciles:\n{tq['deciles'].round(4).to_string()}\n")
        tab = CL.residual_edge_table(te_pool)
        lines.append(f"\n## residual edge {name}\n{tab.round(4).to_string()}\n"
                     f"top2_by_fold:\n{tab.attrs['top2_by_fold'].round(3).to_string()}\n"
                     f"top2_delayed={tab.attrs['top2_d1']:+.3f}\n")
        print(f"   residual-edge deciles 8/9 net: {tab['net_r'].iloc[8]:+.3f}/{tab['net_r'].iloc[9]:+.3f} "
              f"gross: {tab['gross_r'].iloc[8]:+.3f}/{tab['gross_r'].iloc[9]:+.3f}")

    lines.append(f"\n## regime splits {cand}\n{split_table(cells[cand][0], df).round(3).to_string()}\n")

    # G: shuffled-target through full nested pipeline (candidate config)
    cols = [c for p in ABLATIONS[cand] for c in feats[p]]
    y_sh = y.copy()
    RNG.shuffle(y_sh)
    g_fc, g_pool, _ = calibrate_folds(CL.fold_predictions(df, cols, y_sh), METHOD)
    g_tr, _ = run_cell(g_fc, CAP)
    g_ev = CL.pooled_metrics(g_tr, len(g_pool), g_pool)
    print(f"\n== G shuffled-target ==  meanR={g_ev.get('mean_r', float('nan')):+.3f} "
          f"n={g_ev['n']} (FAIL if positive)")
    lines.append(f"\n## G shuffled-target\n{fmt(g_ev)}\n")

    # H: day-shuffled MBP (candidate config)
    h_df = day_shuffle_mbp(df, feats["mbp_"])
    h_fc, h_pool, _ = calibrate_folds(CL.fold_predictions(h_df, cols, y), METHOD)
    h_tr, _ = run_cell(h_fc, CAP)
    h_ev = CL.pooled_metrics(h_tr, len(h_pool), h_pool)
    print(f"== H day-shuffled MBP ==  meanR={h_ev.get('mean_r', float('nan')):+.3f} "
          f"ll={h_ev.get('logloss', float('nan')):.4f}")
    lines.append(f"\n## H day-shuffled MBP\n{fmt(h_ev)} ll={h_ev.get('logloss', float('nan')):.4f}\n")

    (OUT / f"report_{tag}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nreport -> {OUT / f'report_{tag}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
