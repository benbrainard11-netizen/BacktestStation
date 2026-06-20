"""Setup-quality model: predict a volume-confirmed breakout's expected R from its causal setup
features, so trades can be RANKED / SIZED by predicted edge. LightGBM regression, strict TEMPORAL
split (train 2017-2022, validate 2023, test OUT-OF-SAMPLE 2024-2026). The forward-return columns
(x20/x40) are DROPPED -- they are look-ahead labels, not features.

Honest test: on the 2024-26 holdout, sort trades by predicted R into deciles and check the realized
meanR is monotonic + the top slice beats the +0.20R baseline. If the OOS gradient is flat, the model
adds nothing. Run with backend\\.venv\\Scripts\\python.exe.
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
    df["y"] = df["R"].clip(-3, 10)  # target: expected R, tails tamed
    feats = FEATURES + ["sector"]
    df = df.dropna(subset=FEATURES)

    tr = df[df["date"] < 20230101]
    va = df[(df["date"] >= 20230101) & (df["date"] < 20240101)]
    te = df[df["date"] >= 20240101]
    print(f"train {len(tr):,} (2017-22) | val {len(va):,} (2023) | OOS test {len(te):,} (2024-26)\n")

    dtr = lgb.Dataset(tr[feats], tr["y"], categorical_feature=["sector"])
    dva = lgb.Dataset(va[feats], va["y"], reference=dtr)
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
    m = lgb.train(
        params,
        dtr,
        num_boost_round=3000,
        valid_sets=[dva],
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )
    print(f"best iteration: {m.best_iteration}")

    te = te.copy()
    te["pred"] = m.predict(te[feats])
    base = te["R"].clip(upper=10).mean()
    print(f"\nOOS baseline meanR (all volume-confirmed, 2024-26): {base:+.3f}  n={len(te):,}")
    print("\n=== OOS: realized meanR by PREDICTED-edge decile (1=lowest pred, 10=highest) ===")
    te["dec"] = pd.qcut(te["pred"], 10, labels=False, duplicates="drop") + 1
    g = te.groupby("dec").apply(
        lambda d: pd.Series({"n": len(d), "pred": d["pred"].mean(), "realR": d["R"].clip(upper=10).mean()})
    )
    for dec, row in g.iterrows():
        print(
            f"  decile {int(dec):2d}  n={int(row['n']):5,}  pred {row['pred']:+.3f}  realR {row['realR']:+.3f}"
        )

    top = te[te["dec"] >= 8]["R"].clip(upper=10).mean()
    bot = te[te["dec"] <= 3]["R"].clip(upper=10).mean()
    rho = te[["pred", "R"]].corr(method="spearman").iloc[0, 1]
    print(f"\n  top-30% predicted realR {top:+.3f}  vs  bottom-30% {bot:+.3f}  (baseline {base:+.3f})")
    print(f"  Spearman rank-corr(pred, realR) on OOS: {rho:+.4f}")
    print("\n=== feature importance (gain) ===")
    imp = pd.Series(m.feature_importance("gain"), index=feats).sort_values(ascending=False)
    for f, v in imp.items():
        print(f"  {f:14s} {v/imp.sum()*100:5.1f}%")
    te[["tkr", "date", "R", "pred", "dec"]].to_parquet(OUT / "lgbm_oos_pred.parquet")


if __name__ == "__main__":
    main()
