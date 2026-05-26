"""Run the final 15-minute Globex session-close study.

Example:

    python -m app.cli.final_15m_session_close_study \\
        --symbol NQ.c.0 \\
        --start 2025-05-01 \\
        --end 2026-05-01 \\
        --output-dir ../data/research/final_15m_session_close_nq_1y
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.reader import read_bars
from app.research.final_15m_session_close import (
    build_final_15m_session_close_study,
    summarize_study,
)

logger = logging.getLogger("final_15m_session_close_study")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="NQ.c.0", help="Symbol to study.")
    parser.add_argument("--start", type=_parse_date, required=True)
    parser.add_argument("--end", type=_parse_date, required=True)
    parser.add_argument(
        "--direction-deadzone-pts",
        type=float,
        default=0.0,
        help="Next-day return inside +/- this many points is labeled flat.",
    )
    parser.add_argument(
        "--prior-break-buffer-pts",
        type=float,
        default=0.0,
        help="Buffer beyond prior session high/low required to count a break.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for rows, distributions, stats, and summary JSON.",
    )
    args = parser.parse_args(argv)
    _setup_logging()

    if args.start >= args.end:
        parser.error("--start must be before --end")

    output_dir = args.output_dir or Path(
        f"../data/research/final_15m_session_close_{args.symbol.replace('.', '_')}_"
        f"{args.start}_{args.end}"
    )

    # Padding matters because a Globex day starts the previous ET evening,
    # and the last studied session needs the next session for its label.
    load_start = args.start - timedelta(days=3)
    load_end = args.end + timedelta(days=7)
    logger.info(
        "loading 15m bars for %s from %s to %s",
        args.symbol,
        load_start,
        load_end,
    )
    bars = read_bars(
        symbol=args.symbol,
        timeframe="15m",
        start=load_start,
        end=load_end,
    )
    logger.info("loaded %d bars", len(bars))

    study = build_final_15m_session_close_study(
        bars,
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        direction_deadzone_pts=args.direction_deadzone_pts,
        prior_break_buffer_pts=args.prior_break_buffer_pts,
    )
    summary = summarize_study(study)

    output_dir.mkdir(parents=True, exist_ok=True)
    study.to_csv(output_dir / "rows.csv", index=False)
    _write_summary_outputs(summary, output_dir)

    payload = {
        "output_dir": str(output_dir),
        "overview": summary["overview"],
        "bucket_stats_preview": _df_preview(summary["bucket_stats"]),
        "targeted_effect_stats_preview": _df_preview(summary["targeted_effect_stats"]),
        "context_effects_preview": _df_preview(summary["context_effects"]),
        "categorical_tests": _df_preview(summary["categorical_tests"]),
        "numeric_tests": _df_preview(summary["numeric_tests"]),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(_json_safe(payload), indent=2),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(payload), indent=2))
    return 0


def _write_summary_outputs(
    summary: dict[str, pd.DataFrame | dict[str, object]],
    output_dir: Path,
) -> None:
    for name in (
        "close_bucket_distribution",
        "close_bias_distribution",
        "bucket_stats",
        "targeted_effect_stats",
        "context_effects",
        "categorical_tests",
        "numeric_tests",
    ):
        value = summary[name]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / f"{name}.csv", index=False)


def _df_preview(value: Any, *, limit: int = 20) -> list[dict[str, object]]:
    if isinstance(value, pd.DataFrame):
        return value.head(limit).to_dict(orient="records")
    return []


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
