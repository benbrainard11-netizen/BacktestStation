"""Iteration 1: order-flow confirmation increment vs the futures+geometry champion.

Frozen this iteration: labels, objective engine, options features, WF splits, costs,
holdout (untouched). New: timeout-patched EV (eval_lib), mbp_ block, ablations A-F,
controls G (shuffled target) + H (day-shuffled MBP), delayed-entry robustness I,
ranking/calibration/regime/stability diagnostics.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\model_v1.py
Output: out/report_v1.md + out/oos_preds_v1.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import eval_lib as E

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(11)

ABLATIONS = {
    "A geometry": ("geo_",),
    "B futures+geo [champion]": ("geo_", "fut_"),
    "C mbp+geo": ("geo_", "mbp_"),
    "D fut+geo+mbp [candidate]": ("geo_", "fut_", "mbp_"),
    "E options+geo [diag]": ("geo_", "opt_"),
    "F all [diag]": ("geo_", "fut_", "opt_", "mbp_"),
}


def fmt(ev: dict) -> str:
    if "note" in ev:
        return f"n={ev['n']} ({ev['note']})"
    return (f"n={ev['n']:>4} rate={ev['trade_rate']:.0%} meanR={ev['mean_r']:+.3f} "
            f"med={ev['median_r']:+.3f} gross={ev['gross_mean_r']:+.3f} win={ev['win']:.0%} "
            f"PF={ev['pf']:.2f} maxDD={ev['max_dd']:+.1f} CI90=[{ev['ci'][0]:+.3f},{ev['ci'][1]:+.3f}] "
            f"mo+ {ev['pos_months']}/{ev['months']} ll={ev['logloss']:.4f} br={ev['brier']:.4f}")


def day_shuffle_mbp(df: pd.DataFrame, mbp_cols: list[str]) -> pd.DataFrame:
    """Control H: replace each day's mbp block with a random other day's (ms-aligned)."""
    days = sorted(df["date"].unique())
    donor = dict(zip(days, [days[i] for i in RNG.permutation(len(days))]))
    lut = {d: g.set_index("ms")[mbp_cols] for d, g in df.groupby("date")}
    out = df.copy()
    for d, g in out.groupby("date"):
        src = lut[donor[d]].reindex(g["ms"].to_numpy())
        out.loc[g.index, mbp_cols] = src.to_numpy()
    return out


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_v0.parquet").reset_index(drop=True)
    mbp = pd.read_parquet(OUT / "mbp_features_v0.parquet")
    mbp_cols = [c for c in mbp.columns if c.startswith("mbp_")]
    df = df.merge(mbp, on=["date", "ms"], how="left")  # LEFT: never shrink the universe
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    match = df[mbp_cols[0]].notna().mean()
    y = df["y"].to_numpy()
    print(f"{len(df)} rows, {df['date'].nunique()} days, mbp match {match:.1%}, "
          f"{len(mbp_cols)} mbp features")

    feats = {p: [c for c in df.columns if c.startswith(p)] for p in ("geo_", "fut_", "opt_", "mbp_")}
    regime_cols = df[["date", "ms", "fut_rv_30m", "fut_ret_15m", "fut_vol_burst",
                      "geo_dist_up", "geo_dist_dn"]]
    lines = [f"# fuhhhhh v1 report — order-flow increment (timeout-patched EV, EV>={E.EV_MIN}R)\n",
             f"rows={len(df)} days={df['date'].nunique()} mbp_match={match:.1%}\n"]
    results, all_res = {}, []

    for name, prefixes in ABLATIONS.items():
        cols = [c for p in prefixes for c in feats[p]]
        res, imps = E.run_wf(df, cols, y, name)
        ev = E.trade_eval(res)
        results[name] = (res, imps, ev)
        all_res.append(res)
        print(f"\n== {name} ({len(cols)}f) ==\n  {fmt(ev)}")
        lines.append(f"\n## {name} ({len(cols)} feats)\n{fmt(ev)}\n\n{ev['monthly'].to_string()}\n"
                     f"\nfolds:\n{ev['fold_means'].to_string()}\n")

    champ, cand = "B futures+geo [champion]", "D fut+geo+mbp [candidate]"
    for name in (champ, cand):
        res = results[name][0]
        tab = E.ranking_table(res)
        sp = E.rank_spearman(tab)
        print(f"\n-- EV-decile ranking: {name}  (spearman {sp:+.2f}, top decile "
              f"{tab['mean'].iloc[-1]:+.3f} n={int(tab['count'].iloc[-1])})")
        print(tab.round(3).to_string())
        lines.append(f"\n## ranking {name} (spearman {sp:+.2f})\n{tab.round(4).to_string()}\n")
    lines.append(f"\n## calibration {cand}\n{E.calibration_table(results[cand][0]).round(3).to_string()}\n")

    # G: shuffled-target control on the candidate feature set (FAIL only if positive)
    y_sh = y.copy()
    RNG.shuffle(y_sh)
    g_res, _ = E.run_wf(df, [c for p in ("geo_", "fut_", "mbp_") for c in feats[p]], y_sh, "G")
    g_ev = E.trade_eval(g_res)
    print(f"\n== G shuffled-target ==  meanR={g_ev['mean_r']:+.3f} n={g_ev['n']} (healthy=negative)")
    lines.append(f"\n## G shuffled-target\nmeanR={g_ev['mean_r']:+.3f} n={g_ev['n']} (FAIL only if positive)\n")
    if g_ev["n"] > 50 and g_ev["mean_r"] > 0.03:
        print("FAIL  shuffled-target control POSITIVE — leak in selection machinery")

    # H: day-shuffled MBP control — candidate run on misaligned mbp must fall back to ~champion
    h_df = day_shuffle_mbp(df, mbp_cols)
    h_res, _ = E.run_wf(h_df, [c for p in ("geo_", "fut_", "mbp_") for c in feats[p]],
                        y, "H")
    h_ev = E.trade_eval(h_res)
    print(f"== H day-shuffled MBP ==  meanR={h_ev['mean_r']:+.3f} ll={h_ev['logloss']:.4f} "
          f"(expect ~= champion, not ~= candidate)")
    lines.append(f"\n## H day-shuffled MBP\n{fmt(h_ev)}\n")

    # I: one-bar-delayed-entry robustness (same selections, outcomes from t+1m entry)
    print()
    for name in (champ, cand):
        base = results[name][2]
        d1 = E.trade_eval(results[name][0], suffix="_d1")
        delta = d1["mean_r"] - base["mean_r"] if "note" not in d1 else np.nan
        print(f"== I delayed-entry {name} ==  base {base['mean_r']:+.3f} -> d1 {d1['mean_r']:+.3f} "
              f"(delta {delta:+.3f}, dropped {d1.get('n_dropped_nan', '?')})")
        lines.append(f"\n## I delayed-entry {name}\nbase {base['mean_r']:+.3f} -> d1 "
                     f"{d1['mean_r']:+.3f} (delta {delta:+.3f}, n={d1['n']}, dropped={d1.get('n_dropped_nan')})\n")

    lines.append(f"\n## regimes {cand}\n{E.regime_table(results[cand][0], regime_cols).round(3).to_string()}\n")
    stab = E.importance_stability(results[cand][1])
    one_fold = stab[(stab["folds_top20"] == 1) & (stab["gain_share"] > 0.005)]
    lines.append(f"\n## importance stability {cand} (top 25)\n{stab.head(25).round(4).to_string()}\n"
                 f"\none-fold wonders (top20 in exactly 1 fold): {list(one_fold.index)}\n")
    print(f"\ntop 10 candidate features: {list(stab.head(10).index)}")
    print(f"one-fold wonders: {list(one_fold.index)}")

    pd.concat(all_res, ignore_index=True).to_parquet(OUT / "oos_preds_v1.parquet")
    (OUT / "report_v1.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nreport -> {OUT / 'report_v1.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
