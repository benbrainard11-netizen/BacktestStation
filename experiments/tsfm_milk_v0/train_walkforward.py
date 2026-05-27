"""Train all Forecaster implementations across all walk-forward folds.

Reads:
  out/dataset/fold_*_{train,val,test}.parquet
  walk_forward.yaml

Trains:
  For each model in args.models:
    For each fold in folds:
      forecaster = model_factory(model_name)
      forecaster.fit(train, val)
      preds_val  = forecaster.predict_proba(val)
      preds_test = forecaster.predict_proba(test)
      forecaster.save(out/models/{model}/{fold_id}/)
      preds → out/predictions/{model}/fold_{fold_id}_{val,test}.parquet

Available models (v0):
  - naive            (sanity floor)
  - lightgbm         (strong baseline)
  - ttm              (v0 primary)

Available models (v0.5+):
  - moirai

Usage:
  python train_walkforward.py --models naive lightgbm ttm
  python train_walkforward.py --models ttm --folds 1 2 3   # subset

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("train_walkforward.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
