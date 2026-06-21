from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_strategy_event_table import normalize_fractal  # noqa: E402


def test_normalize_fractal_builds_trade_labels(tmp_path: Path) -> None:
    csv = tmp_path / "trades.csv"
    pd.DataFrame(
        {
            "entry_time": ["2024-01-02 11:51", "2024-01-02 12:21"],
            "exit_time": ["2024-01-02 13:51", "2024-01-02 12:30"],
            "direction": ["BEARISH", "BULLISH"],
            "pnl_r": [0.75, -1.0],
            "risk": [85.25, 10.25],
            "exit_reason": ["timeout", "SL"],
        }
    ).to_csv(csv, index=False)

    out = normalize_fractal(csv, move_r=0.5, bad_r=1.0)

    assert out["direction"].tolist() == ["short", "long"]
    assert out["y_good_trade"].tolist() == [1, 0]
    assert out["y_bad_env"].tolist() == [0, 1]
    assert out["baseline_trade"].all()
    assert out["source_status"].unique().tolist() == ["usable"]
