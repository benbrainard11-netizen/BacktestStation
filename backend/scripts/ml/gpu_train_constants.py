"""Named constants for the GPU XGBoost training runner.

Centralized so the runner, fold builder, schema-safe loader, and tests
all reference the same values (CLAUDE.md rule #7 — no inline magic).
"""

from __future__ import annotations

# --- Walk-forward split offsets --------------------------------------------
#
# Train spans years [first_available, test_year - TRAIN_END_OFFSET].
# Val is the single year `test_year - VAL_OFFSET`.
# Test is the single year `test_year`.
#
# Matches the existing CPU LightGBM walk-forward in
# `backend/scripts/ml/snapshot_walk_forward.py:_run_fold`.
TRAIN_END_OFFSET = 2
VAL_OFFSET = 1

# Default test years from Prompt B (context-layers experiment scope).
DEFAULT_TEST_YEARS: tuple[int, ...] = (2020, 2021, 2022, 2023, 2024, 2025)

# --- Matrix filter columns --------------------------------------------------
#
# These names are produced by the upstream `build_*_snapshot_matrix.py`
# scripts on the main PC. The GPU runner only consumes them.
SNAPSHOT_COLUMN = "asof.snapshot"
EVENT_TYPE_COLUMN = "anchor.event_type"
SIDE_COLUMN = "anchor.side"
YEAR_COLUMN = "ts.year"

# Any column starting with this prefix is a label, never a feature.
# Hard-gates leakage even when a schema lists one in `feature_columns`.
LABEL_COLUMN_PREFIX = "label."

# Manual-composite sentinel feature inherited from the SMT pipeline.
# Carried forward only when the caller explicitly opts in. Source:
# `backend/scripts/ml/snapshot_model_runner.py:28`.
MANUAL_CELL_COLUMN = "pc.manual_active_1hpsp_4hfvg_cell"

# --- Split-size minimums ---------------------------------------------------
#
# Mirrors `backend/scripts/ml/snapshot_walk_forward.py:_run_fold` so a
# fold that's "too small to trust" for LightGBM is also skipped here.
MIN_TRAIN_ROWS = 100
MIN_TEST_ROWS = 50
MIN_TRAIN_CLASS = 50
MIN_TEST_CLASS = 20

# Top-bucket reporting size (top 10% of test rows by predicted prob).
# Mirrors the existing leaderboard's `top_pct=0.10` default.
TOP_BUCKET_PCT = 0.10

# --- Reproducibility -------------------------------------------------------
#
# Matches `backend/scripts/ml/snapshot_model_leaderboard.py:234`
# so the GPU vs CPU comparison uses the same seed family.
SEED = 20260510

# --- XGBoost training defaults ---------------------------------------------
#
# Picked to mirror the LightGBM baseline shape so the GPU vs CPU
# comparison isolates the device + library, not hyperparameters.
# LightGBM equivalents are listed alongside.
NUM_BOOST_ROUND = 500  # matches `num_boost_round=500`
LEARNING_RATE = 0.03  # matches `learning_rate=0.03`
EARLY_STOPPING_ROUNDS = 30  # matches `lgb.early_stopping(30)`
MAX_DEPTH = 6  # rough analog of `num_leaves=31`
MIN_CHILD_WEIGHT = 25  # mirrors `min_data_in_leaf=25`
SUBSAMPLE = 0.85  # mirrors `bagging_fraction=0.85`
COLSAMPLE_BYTREE = 0.85  # mirrors `feature_fraction=0.85`

# --- Device selection ------------------------------------------------------
#
# XGBoost 2.x uses `device='cuda'` + `tree_method='hist'`. The 1.x
# vocabulary (`tree_method='gpu_hist'`) is unused — Prompt B's target
# host runs xgboost>=2.1.
DEVICE_CUDA = "cuda"
DEVICE_CPU = "cpu"
TREE_METHOD = "hist"

# Pre-resolved "auto" sentinel for the CLI. The runner picks
# DEVICE_CUDA if `xgboost.build_info()['USE_CUDA']` is truthy, else
# DEVICE_CPU.
DEVICE_AUTO = "auto"
