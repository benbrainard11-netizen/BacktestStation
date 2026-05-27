"""Train Type A and Type B heads with expanding-window walk-forward.

Loads:
  out/features.parquet
  out/labels.parquet
  walk_forward.yaml         (4 expanding-window folds + final holdout)
  detector_families.yaml    (family dispatch)

Trains separate heads per family:
  Type A: y_bad classifier + y_mae_r quantile regressor + y_ttt regressor
  Type B: y_tail classifier + pred_mae_r_q95 quantile regressor

Saves per fold:
  out/models/{fold_id}/type_a/...
  out/models/{fold_id}/type_b/...
  out/predictions/fold_{fold_id}.parquet

Baseline ladder (run as separate experiments):
  0. current_engine             (size_mult=1.0, no model)
  1. static_detector_session    f(detector, family, symbol, session) sizing
  2. ohlcv_only_subset          no MBP-1 features
  3. mbp1_same_symbol           + MBP-1 features
  4. cross_asset                + xasset features
  5. full_v0                    + 5 MBO features + calibrated family policy

See PLAN §5 for the full ladder spec and PLAN §6 for kill criteria.

Algorithm: LightGBM CUDA (RTX 5080).

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "train_walkforward.py is a stub. "
        "Implement after features.parquet and labels.parquet exist."
    )


if __name__ == "__main__":
    raise SystemExit(main())
