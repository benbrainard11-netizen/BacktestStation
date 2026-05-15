"""Tests for the schema-safe feature loader.

Locks in the no-label-leak invariant required by Prompt B
("Never use `label.*` columns as model inputs.").
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.ml.gpu_train_constants import LABEL_COLUMN_PREFIX, MANUAL_CELL_COLUMN
from scripts.ml.gpu_train_schema_safe import (
    assert_no_label_leak,
    coerce_binary_label,
    encode_like_train,
    load_schema,
    schema_safe_feature_columns,
    select_usable_features,
)


def test_schema_safe_feature_columns_drops_label_prefixed():
    schema = {
        "feature_columns": [
            "ctx.regime_a",
            "ctx.regime_b",
            "label.something_that_leaked",
            "label.another_leak",
            "anchor.event_id",
        ]
    }
    safe = schema_safe_feature_columns(schema)
    assert "label.something_that_leaked" not in safe
    assert "label.another_leak" not in safe
    assert "ctx.regime_a" in safe
    assert "ctx.regime_b" in safe
    assert "anchor.event_id" in safe
    assert not any(c.startswith(LABEL_COLUMN_PREFIX) for c in safe)


def test_manual_cell_excluded_by_default_and_optable_in():
    schema = {
        "feature_columns": [
            "ctx.foo",
            MANUAL_CELL_COLUMN,
        ]
    }
    default = schema_safe_feature_columns(schema)
    assert MANUAL_CELL_COLUMN not in default
    opt_in = schema_safe_feature_columns(schema, include_manual_cell=True)
    assert MANUAL_CELL_COLUMN in opt_in


def test_assert_no_label_leak_raises_on_label_prefix():
    with pytest.raises(ValueError, match="label-prefixed"):
        assert_no_label_leak(["ctx.foo", "label.range_expanded"])


def test_assert_no_label_leak_silent_on_clean_input():
    assert assert_no_label_leak(["ctx.foo", "ctx.bar", "anchor.event_id"]) is None


def test_select_usable_features_drops_all_nan_and_constant():
    df = pd.DataFrame(
        {
            "ctx.useful": [1.0, 2.0, 3.0, 4.0],
            "ctx.all_nan": [np.nan, np.nan, np.nan, np.nan],
            "ctx.constant": [5.0, 5.0, 5.0, 5.0],
            "ctx.cat": ["a", "b", "a", "c"],
        }
    )
    usable, categorical, dropped = select_usable_features(
        df, ["ctx.useful", "ctx.all_nan", "ctx.constant", "ctx.cat", "ctx.missing"]
    )
    assert "ctx.useful" in usable
    assert "ctx.cat" in usable
    assert "ctx.cat" in categorical
    assert "ctx.all_nan" in dropped
    assert "ctx.constant" in dropped
    assert "ctx.missing" not in usable
    assert "ctx.missing" not in dropped  # not present in df → silently skipped


def test_encode_like_train_one_hots_categoricals_and_floats():
    df = pd.DataFrame(
        {
            "ctx.num": [1.0, 2.0, 3.0],
            "ctx.cat": ["a", "b", "a"],
        }
    )
    encoded = encode_like_train(df, ["ctx.num", "ctx.cat"], ["ctx.cat"])
    assert all(encoded.dtypes == "float64")
    # One-hot columns appear; categorical column is gone.
    assert "ctx.cat" not in encoded.columns
    cat_cols = [c for c in encoded.columns if c.startswith("ctx.cat_")]
    assert len(cat_cols) >= 2


def test_encode_like_train_reindexes_to_train_columns():
    train = pd.DataFrame({"ctx.num": [1.0, 2.0], "ctx.cat": ["a", "b"]})
    x_train = encode_like_train(train, ["ctx.num", "ctx.cat"], ["ctx.cat"])
    train_cols = list(x_train.columns)

    # Test set has a category the train didn't see; the encoding must
    # still produce the same column set (extra category dropped, missing
    # category filled with zeros).
    test = pd.DataFrame({"ctx.num": [9.0], "ctx.cat": ["c"]})
    x_test = encode_like_train(test, ["ctx.num", "ctx.cat"], ["ctx.cat"], train_cols)
    assert list(x_test.columns) == train_cols


def test_coerce_binary_label_handles_bool_and_numeric():
    bool_s = pd.Series([True, False, True])
    out = coerce_binary_label(bool_s)
    assert out.tolist() == [1, 0, 1]

    num_s = pd.Series([1, 0, np.nan, 1])
    out2 = coerce_binary_label(num_s)
    assert out2.dropna().astype(int).tolist() == [1, 0, 1]


def test_load_schema_round_trips_json(tmp_path: Path):
    path = tmp_path / "schema.json"
    payload = {"feature_columns": ["a", "b"], "label_columns": ["label.x"]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    out = load_schema(path)
    assert out == payload
