"""v0 model: LightGBM 3-class objective-race, purged day-block walk-forward.

Embedded ablations of the SAME system (SPEC phase 1): geometry-only floor /
futures+geo / options+geo / combined — plus a shuffled-target negative control.
Money metric: net realized R of conviction-selected trades (top CONV_Q per fold),
day-block bootstrap CI, monthly means. Diagnostics: logloss, class accuracy.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\model_v0.py
Output: out/report_v0.md + out/oos_preds_v0.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(7)

PARAMS = dict(objective="multiclass", num_class=3, learning_rate=0.05, num_leaves=31,
              n_estimators=400, min_child_samples=50, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, verbose=-1, seed=7, n_jobs=-1)
MIN_TRAIN_D = 110  # trading days before the first test block
TEST_D = 21        # test block length (≈ one month)
EMBARGO_D = 1      # ≥ label horizon (45 min) — one full day is generous
CONV_Q = 0.80      # diagnostic rule: top-20% conviction rows per fold
EV_MIN = 0.05      # primary rule: trade when model EV >= +0.05R net of costs
BOOT_N = 1000

ABLATIONS = {  # name -> column predicate over feature names
    "geometry": lambda c: c.startswith("geo_"),
    "futures": lambda c: c.startswith(("geo_", "fut_")),
    "options": lambda c: c.startswith(("geo_", "opt_")),
    "combined": lambda c: c.startswith(("geo_", "fut_", "opt_")),
}


def wf_folds(days: list[str]) -> list[tuple[list[str], list[str]]]:
    folds, i = [], MIN_TRAIN_D
    while i + TEST_D <= len(days):
        folds.append((days[: i - EMBARGO_D], days[i : i + TEST_D]))
        i += TEST_D
    if i < len(days) and len(days) - i >= 10:  # final ragged block
        folds.append((days[: i - EMBARGO_D], days[i:]))
    return folds


def run_wf(df: pd.DataFrame, cols: list[str], y: np.ndarray, label: str) -> pd.DataFrame:
    days = sorted(df["date"].unique())
    preds = []
    for k, (tr_days, te_days) in enumerate(wf_folds(days)):
        tr = df["date"].isin(tr_days).to_numpy() & (y >= 0)  # ambiguous rows never train
        te = df["date"].isin(te_days).to_numpy()  # ...but ARE evaluated (scored as stops)
        m = lgb.LGBMClassifier(**PARAMS)
        m.fit(df.loc[tr, cols], y[tr])
        p = m.predict_proba(df.loc[te, cols])
        out = df.loc[te, ["date", "ms", "y", "r_long_net", "r_short_net",
                          "price", "obj_up", "obj_dn"]].copy()
        out["p_dn"], out["p_up"], out["p_none"] = p[:, 0], p[:, 1], p[:, 2]
        out["fold"] = k
        preds.append(out)
    res = pd.concat(preds, ignore_index=True)
    res["ablation"] = label
    return res


def trade_eval(res: pd.DataFrame, rule: str = "ev") -> dict:
    """Trade selection on OOS probabilities.

    rule="ev" (primary): EV in R units from calibratable probs x payoff geometry,
    trade max(ev_long, ev_short) when it clears EV_MIN after costs — the origin
    spec's actual decision rule. rule="conviction": top-CONV_Q |p_up - p_dn| per fold
    (kept as a diagnostic; it adversely selects tiny-payoff rows by construction).
    """
    r = res.copy()
    du, dd = r["obj_up"] - r["price"], r["price"] - r["obj_dn"]
    ev_long = r["p_up"] * (du / dd) - r["p_dn"] - C.COST_PTS / dd
    ev_short = r["p_dn"] * (dd / du) - r["p_up"] - C.COST_PTS / du
    if rule == "ev":
        r["edge"], long_side = np.maximum(ev_long, ev_short), ev_long >= ev_short
        t = r[r["edge"] >= EV_MIN].copy()
    else:
        r["edge"], long_side = (r["p_up"] - r["p_dn"]).abs(), r["p_up"] > r["p_dn"]
        thresh = r.groupby("fold")["edge"].transform(lambda s: s.quantile(CONV_Q))
        t = r[r["edge"] >= thresh].copy()
    t["r"] = np.where(long_side.loc[t.index], t["r_long_net"], t["r_short_net"])
    t = t.dropna(subset=["r"])
    if t.empty:
        return dict(n=0, mean_r=np.nan, win=np.nan, ci=(np.nan, np.nan),
                    pos_months=0, months=0, monthly=pd.DataFrame(), logloss=np.nan)
    day_means = t.groupby("date")["r"].mean()
    boots = [RNG.choice(day_means.to_numpy(), size=len(day_means), replace=True).mean() for _ in range(BOOT_N)]
    lo, hi = np.percentile(boots, [5, 95])
    monthly = t.groupby(t["date"].str.slice(0, 7))["r"].agg(["mean", "count"])
    resl = res[res["y"] >= 0]  # logloss only defined on resolved labels
    ll = -np.mean(np.log(np.clip(
        np.take_along_axis(resl[["p_dn", "p_up", "p_none"]].to_numpy(),
                           resl["y"].to_numpy()[:, None], axis=1), 1e-9, 1)))
    return dict(n=len(t), mean_r=float(t["r"].mean()), win=float((t["r"] > 0).mean()),
                ci=(float(lo), float(hi)), pos_months=int((monthly["mean"] > 0).sum()),
                months=len(monthly), monthly=monthly, logloss=float(ll))


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_v0.parquet").reset_index(drop=True)
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    y = df["y"].to_numpy()  # y=-1 ambiguous rows kept: excluded from fit, scored as stops
    feat_all = [c for c in df.columns if c.startswith(("geo_", "fut_", "opt_"))]
    counts = df["y"].value_counts().sort_index().to_dict()
    print(f"{len(df)} rows, {df['date'].nunique()} days, {len(feat_all)} features, "
          f"classes (ambig/dn/up/neither) {counts}")

    lines = [f"# fuhhhhh v0 report\n\nrows={len(df)} days={df['date'].nunique()} "
             f"classes (ambig/dn/up/neither) = {counts}\n",
             f"primary trade rule: EV >= {EV_MIN}R net of {C.COST_PTS} pts costs; entry = first "
             f"post-decision print; ambiguous bars scored as stops. conviction rule = diagnostic only.\n"]
    all_res = []
    for name, pred in ABLATIONS.items():
        cols = [c for c in feat_all if pred(c)]
        res = run_wf(df, cols, y, name)
        all_res.append(res)
        print(f"\n== {name} ({len(cols)} feats) ==")
        for rule in ("ev", "conviction"):
            ev = trade_eval(res, rule)
            tag = f"{rule:<10} n={ev['n']:>5}  meanR={ev['mean_r']:+.3f}  win={ev['win']:.1%}  " \
                  f"CI90=[{ev['ci'][0]:+.3f},{ev['ci'][1]:+.3f}]  months+ {ev['pos_months']}/{ev['months']}"
            print(f"  {tag}  logloss={ev['logloss']:.4f}")
            lines.append(f"\n## {name} / {rule} ({len(cols)} feats)\n{tag} logloss={ev['logloss']:.4f}\n\n"
                         f"{ev['monthly'].to_string()}\n")

    # Shuffled-target negative control. NOTE the race construction's math: any race is
    # ~zero-EV GROSS under drift-free geometry (P(up first) ≈ dd/(du+dd)), so an
    # UNINFORMED model nets out at minus the cost drag + miscalibrated-selection drag —
    # strongly NEGATIVE is the expected, healthy reading. The control fails only if it
    # comes out POSITIVE (selection machinery manufacturing edge from nothing).
    y_sh = y.copy()
    RNG.shuffle(y_sh)
    ctrl = trade_eval(run_wf(df, feat_all, y_sh, "control"), "ev")
    print(f"\n== shuffled-target control (ev rule) ==  meanR={ctrl['mean_r']:+.3f} n={ctrl['n']} "
          f"(healthy = clearly negative; FAIL if positive)")
    lines.append(f"\n## shuffled-target control (ev)\nmeanR={ctrl['mean_r']:+.3f} n={ctrl['n']} "
                 f"CI90=[{ctrl['ci'][0]:+.3f},{ctrl['ci'][1]:+.3f}] — healthy=negative (cost drag); FAIL if positive\n")
    if ctrl["n"] > 50 and ctrl["mean_r"] > 0.03:
        print("FAIL  control is POSITIVE — selection machinery is leaking; nothing above is believable")

    # feature importance from a last-fold combined fit
    days = sorted(df["date"].unique())
    tr = df["date"].isin(days[:-TEST_D]).to_numpy() & (y >= 0)
    m = lgb.LGBMClassifier(**PARAMS).fit(df.loc[tr, feat_all], y[tr])
    imp = pd.Series(m.booster_.feature_importance("gain"), index=feat_all).sort_values(ascending=False)
    lines.append("\n## top-20 features (gain, last-fold combined)\n" + imp.head(20).to_string() + "\n")
    print("\ntop 10 features:", list(imp.head(10).index))

    pd.concat(all_res, ignore_index=True).to_parquet(OUT / "oos_preds_v0.parquet")
    (OUT / "report_v0.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nreport -> {OUT / 'report_v0.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
