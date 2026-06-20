"""Walk-forward / regime-robustness re-test of the setup-quality LightGBM model.

For each test_year in [2019..2025]: train on all breakout setups with year < test_year (>= 2017),
test on test_year only. Report Spearman(pred, realR) and realized meanR of the top/bottom predicted
deciles (R capped at 10 for the meanR). The model + features mirror lgbm_quality.py exactly.
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

PARAMS = dict(
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


def load() -> pd.DataFrame:
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
    df["yr"] = df["date"] // 10000
    return df


def main():
    import lightgbm as lgb

    df = load()
    feats = FEATURES + ["sector"]
    results = []

    for ty in [2019, 2020, 2021, 2022, 2023, 2024, 2025]:
        tr = df[(df["yr"] >= 2017) & (df["yr"] < ty)]
        te = df[df["yr"] == ty].copy()
        # carve last in-train year as early-stopping validation, like the original
        va_yr = ty - 1
        va = tr[tr["yr"] == va_yr]
        trc = tr[tr["yr"] < va_yr]
        if len(trc) < 2000 or len(va) < 500:  # too little to hold out a val year
            trc, va = tr, tr

        dtr = lgb.Dataset(trc[feats], trc["y"], categorical_feature=["sector"])
        dva = lgb.Dataset(va[feats], va["y"], reference=dtr)
        m = lgb.train(
            PARAMS,
            dtr,
            num_boost_round=3000,
            valid_sets=[dva],
            callbacks=[lgb.early_stopping(100, verbose=False)],
        )

        te["pred"] = m.predict(te[feats])
        te["dec"] = pd.qcut(te["pred"], 10, labels=False, duplicates="drop") + 1
        top = float(te[te["dec"] == te["dec"].max()]["R"].clip(upper=10).mean())
        bot = float(te[te["dec"] == te["dec"].min()]["R"].clip(upper=10).mean())
        rho = float(te[["pred", "R"]].corr(method="spearman").iloc[0, 1])
        base = float(te["R"].clip(upper=10).mean())
        results.append(
            dict(
                test_year=ty,
                n_train=len(tr),
                n_test=len(te),
                spearman=round(rho, 4),
                top_decile_R=round(top, 4),
                bot_decile_R=round(bot, 4),
                spread=round(top - bot, 4),
                base=round(base, 4),
                best_iter=m.best_iteration,
            )
        )
        print(
            f"test {ty}  n_tr={len(tr):6,}  n_te={len(te):5,}  rho {rho:+.4f}  "
            f"top {top:+.3f}  bot {bot:+.3f}  spread {top-bot:+.3f}  base {base:+.3f}"
        )

    print("\nJSON:\n" + json.dumps(results, indent=2))
    bad = [r for r in results if r["test_year"] in (2019, 2022)]
    print("\nBAD-year check (2019, 2022): top>bot?")
    for r in bad:
        print(
            f"  {r['test_year']}: top {r['top_decile_R']:+.3f} vs bot {r['bot_decile_R']:+.3f} "
            f"-> {'BEATS' if r['top_decile_R'] > r['bot_decile_R'] else 'FAILS'}"
        )


if __name__ == "__main__":
    main()
