"""Overfit / stability check for lgbm_quality.py.

(1) Retrain the SAME model with 5 different random seeds (lgb seed + bagging + feature seeds)
    and report OOS (2024-26) Spearman for each.
(2) Drop the top feature spy_ret60 and retrain (seed 0), report OOS Spearman.

Mirrors lgbm_quality.py exactly except for the parameterized seed + feature list.
Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
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


def load_df():
    R = pd.read_parquet(OUT / "intraday_entry_results_full.parquet")[["tkr", "date", "R"]]
    S = pd.read_parquet(OUT / "setups.parquet")
    S = S[S["is_breakout"] == 1]
    sec = pd.read_parquet(POLY / "_xregime_with_sector.parquet")[["tkr", "date", "sector"]]
    df = R.merge(S, left_on=["tkr", "date"], right_on=["ticker", "date"], how="left").merge(
        sec, on=["tkr", "date"], how="left"
    )
    df["sector"] = df["sector"].fillna("Unknown").astype("category")
    df["y"] = df["R"].clip(-3, 10)
    return df


def run(df, features, seed):
    import lightgbm as lgb

    feats = features + ["sector"]
    d = df.dropna(subset=features)

    tr = d[d["date"] < 20230101]
    va = d[(d["date"] >= 20230101) & (d["date"] < 20240101)]
    te = d[d["date"] >= 20240101].copy()

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
        seed=seed,
        bagging_seed=seed,
        feature_fraction_seed=seed,
        data_random_seed=seed,
        deterministic=True,
        force_row_wise=True,
    )
    m = lgb.train(
        params,
        dtr,
        num_boost_round=3000,
        valid_sets=[dva],
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )
    te["pred"] = m.predict(te[feats])
    rho = te[["pred", "R"]].corr(method="spearman").iloc[0, 1]
    return float(rho), int(m.best_iteration), len(tr), len(va), len(te)


def main():
    df = load_df()
    results = {}

    # (1) 5 seeds, full feature set
    seed_rhos = []
    for seed in [0, 1, 2, 3, 4]:
        rho, best_it, ntr, nva, nte = run(df, FEATURES, seed)
        seed_rhos.append(round(rho, 4))
        print(f"[seed {seed}] OOS Spearman {rho:+.4f}  best_iter={best_it}  tr={ntr} va={nva} te={nte}")
    results["seed_spearmans"] = seed_rhos

    # (2) drop top feature spy_ret60, seed 0
    feats_drop = [f for f in FEATURES if f != "spy_ret60"]
    rho_drop, best_it, _, _, _ = run(df, feats_drop, 0)
    results["spearman_without_top_feature"] = round(rho_drop, 4)
    print(f"\n[drop spy_ret60, seed 0] OOS Spearman {rho_drop:+.4f}  best_iter={best_it}")

    print("\n=== SUMMARY ===")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
