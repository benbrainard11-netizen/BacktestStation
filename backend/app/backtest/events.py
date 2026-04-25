"""Event log dataclasses.

Every notable thing the engine does emits an Event. The runner
serializes the event log to `events.parquet` so post-mortem analysis
(autopsy, replay, audit) can walk the run step by step.

Event types are intentionally stringly-named (not enum int values) so
the parquet column reads cleanly in DuckDB / pandas without joins.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventType(str, Enum):
    ORDER_SUBMITTED = "order_submitted"
    ORDER_CANCELLED = "order_cancelled"
    FILL = "fill"
    STOP_HIT = "stop_hit"
    TARGET_HIT = "target_hit"
    AMBIGUOUS_FILL = "ambiguous_fill"
    EOD_FLATTEN = "eod_flatten"
    DAY_ROLLOVER = "day_rollover"
    SESSION_OPEN = "session_open"
    SESSION_CLOSE = "session_close"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"


@dataclass(frozen=True)
class Event:
    """One row in the event log. Free-form `payload` keeps the dataclass
    stable while letting different event types attach different details."""

    ts: dt.datetime
    type: EventType
    bar_index: int
    payload: dict[str, Any]
