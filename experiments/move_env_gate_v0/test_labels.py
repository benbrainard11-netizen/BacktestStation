from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from labels import attach_move_env_labels


def test_attach_move_env_labels_partitions_move_and_chop() -> None:
    df = pd.DataFrame(
        {
            "mfe_R": [1.2, 0.2, 0.6],
            "mae_R": [0.1, 1.1, 0.4],
            "realized_R": [1.0, -1.0, 0.1],
        }
    )

    out = attach_move_env_labels(df)

    assert out["y_move"].tolist() == [1, 1, 0]
    assert out["y_favorable_move"].tolist() == [1, 0, 0]
    assert out["y_bad_env"].tolist() == [0, 1, 0]
    assert out["y_chop"].tolist() == [0, 0, 1]
