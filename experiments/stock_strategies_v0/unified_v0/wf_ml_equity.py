"""Walk-forward ML strategy + equity. Each year's trades are scored by a LightGBM quality model
trained ONLY on prior years (deployable, no look-ahead). We then take the trades the model predicts
positive (pred>0) and compare the with-ML edge to the all-trades baseline, year by year, and save the
selected trades so the Monte Carlo can project the with-ML equity. 2018 is excluded (too little train
history before it). Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
POLY = Path(r"D:\data\processed\stocks\polygon")
FEATURES = [
    "big_gap",
    "gap",
    "vol_spike",
    "ret_3m",
    "ret_6m",
    "ret_12_1",
    "rs_6m",
    "high52_prox",
    "atr_pct",
    "vol_contract",
    "base_width",
    "dist_ma50",
    "regime_up",
    "spy_ret60",
    "log_price",
    "log_dvol",
]


def main():
    import lightgbm as lgb

    R = pd.read_parquet(OUT / "intraday_entry_results_full.parquet")[["tkr", "date", "R"]]
    S = pd.read_parquet(OUT / "setups.parquet")
    S = S[S["is_breakout"] == 1]
    sec = pd.read_parquet(POLY / "_xregime_with_sector.parquet")[["tkr", "date", "sector"]]
    df = R.merge(S, left_on=["tkr", "date"], right_on=["ticker", "date"], how="left").merge(
        sec, on=["tkr", "date"], how="left"
    )
    df["sector"] = df["sector"].fillna("Unknown").astype("category")
    df["y"] = df["R"].clip(-3, 10)
    df = df.dropna(subset=FEATURES)
    feats = FEATURES + ["sector"]
    params = dict(
        objective="huber",
        alpha=2.0,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=6,
        min_child_samples=500,
        feature_fraction=0.8,
        bagging_fraction=0.8,
        bagging_freq=1,
        verbose=-1,
    )

    preds = []
    for ty in range(2019, 2027):
        tr = df[df["date"] < ty * 10000]
        te = df[(df["date"] >= ty * 10000) & (df["date"] < (ty + 1) * 10000)]
        if len(te) == 0 or len(tr) < 20000:
            continue
        cut = (ty - 1) * 10000  # last train year = early-stopping validation
        t2, v2 = tr[tr["date"] < cut], tr[tr["date"] >= cut]
        m = lgb.train(
            params,
            lgb.Dataset(t2[feats], t2["y"], categorical_feature=["sector"]),
            num_boost_round=3000,
            valid_sets=[lgb.Dataset(v2[feats], v2["y"])],
            callbacks=[lgb.early_stopping(100, verbose=False)],
        )
        te = te.copy()
        te["pred"] = m.predict(te[feats])
        preds.append(te[["tkr", "date", "R", "pred"]])
        print(f"  scored {ty}: {len(te):,} trades (train {len(tr):,})", flush=True)

    wf = pd.concat(preds, ignore_index=True)
    wf["yr"] = wf["date"] // 10000
    wf["Rc"] = wf["R"].clip(upper=10)
    wf.to_parquet(OUT / "wf_ml_predictions.parquet")

    print("\n=== with-ML vs baseline, by year (walk-forward, deployable) ===")
    print(f"{'yr':>4} {'base n':>7} {'base R':>7} | {'ML n':>6} {'ML R':>7} {'keep%':>6} | {'top30% R':>8}")
    for y in sorted(wf["yr"].unique()):
        d = wf[wf["yr"] == y]
        ml = d[d["pred"] > 0]
        thr = d["pred"].quantile(0.70)
        t30 = d[d["pred"] >= thr]
        mlr = ml["Rc"].mean() if len(ml) else float("nan")
        print(
            f"{int(y):>4} {len(d):>7,} {d['Rc'].mean():+7.3f} | {len(ml):>6,} {mlr:+7.3f} "
            f"{100*len(ml)/len(d):5.0f}% | {t30['Rc'].mean():+8.3f}"
        )

    base = wf["Rc"].mean()
    sel = wf[wf["pred"] > 0]
    print(
        f"\nOVERALL  baseline {base:+.3f} (n={len(wf):,})  ->  ML pred>0 {sel['Rc'].mean():+.3f} "
        f"(n={len(sel):,}, {100*len(sel)/len(wf):.0f}% kept)"
    )
    sel[["tkr", "date", "R"]].to_parquet(OUT / "ml_selected_results.parquet")
    print(f"saved ML-selected trades -> {OUT/'ml_selected_results.parquet'}")
    print("READ: done")


if __name__ == "__main__":
    main()
