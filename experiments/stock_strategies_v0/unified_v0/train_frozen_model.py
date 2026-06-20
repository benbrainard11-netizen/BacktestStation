"""Train the FROZEN deployment model: one LightGBM on ALL breakout setups, saved for live scoring of
new setups going forward. Same features/params as the walk-forward (lgbm_quality.py); num_boost_round
fixed at the walk-forward's typical best_iteration (~380, no validation since we train on everything).
Writes frozen_model.txt + frozen_meta.json. Re-run periodically (e.g., monthly) to refresh.
Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import json
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
    m = lgb.train(
        params, lgb.Dataset(df[feats], df["y"], categorical_feature=["sector"]), num_boost_round=380
    )
    m.save_model(str(OUT / "frozen_model.txt"))
    sectors = sorted(df["sector"].cat.categories.tolist())
    json.dump(
        {
            "features": feats,
            "categorical": ["sector"],
            "sectors": sectors,
            "trained_through": int(df["date"].max()),
            "n_train": int(len(df)),
            "sizing": {
                "base_risk": 0.0075,
                "max_positions": 5,
                "pred_mult_cap": 2.0,
                "adv_frac": 0.01,
                "buf_entry": 0.001,
                "k_atr": 1.0,
            },
        },
        open(OUT / "frozen_meta.json", "w"),
        indent=2,
    )
    print(f"frozen model trained on {len(df):,} setups through {int(df['date'].max())} -> frozen_model.txt")


if __name__ == "__main__":
    main()
