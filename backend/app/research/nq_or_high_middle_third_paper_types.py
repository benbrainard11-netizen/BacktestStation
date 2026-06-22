"""Types and constants for the OR-high shadow paper monitor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.paths import DATA_DIR, LIVE_STATUS_PATH
from app.research.nq_opening_range_mbp_execution_types import (
    EntryStyle,
    OpeningRangeMbpExecutionConfig,
)

DEFAULT_OUTPUT_DIR = DATA_DIR / "live_paper" / "nq_or_high_middle_third"
SNAPSHOT_FILE = "paper_snapshot.json"
POSITIONS_FILE = "paper_positions.csv"
SNAPSHOTS_JSONL = "paper_snapshots.jsonl"
SIGNALS_JSONL = "paper_signals.jsonl"
CLOSED_TRADES_JSONL = "paper_closed_trades.jsonl"


@dataclass(frozen=True)
class PaperMonitorConfig:
    symbol: str = "NQ.c.0"
    primary_entry_style: EntryStyle = "immediate_break"
    context_deadzone_pts: float = 8.0
    output_dir: Path = DEFAULT_OUTPUT_DIR
    live_status_path: Path = LIVE_STATUS_PATH
    execution: OpeningRangeMbpExecutionConfig = OpeningRangeMbpExecutionConfig()
