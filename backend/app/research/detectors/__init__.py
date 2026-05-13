"""Detector registry + Protocol.

Mirrors the `app.features.FEATURES` registry pattern: each detector
module registers itself at import time, and the scan orchestrator
looks detectors up by name.

A detector is anything that, given a date range + symbols + a bar
reader callable, produces a list of `ResearchEventCreate` payloads.
The scan orchestrator handles the DB writes via
`services.research_events.record_event` (idempotent).

Adding a detector:

  1. Create a new module under this package, e.g.
     `app/research/detectors/my_detector.py`.
  2. Define a class implementing the `Detector` protocol.
  3. At module bottom, call `register("my_detector_name", instance)`.
  4. Import the module in this file's bottom side-effect block.

See `docs/RESEARCH_DETECTORS.md` for the full how-to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from typing import Any, Callable, Protocol

import pandas as pd

from app.schemas.research_events import ResearchEventCreate


# A bar reader is a callable matching `app.data.reader.read_bars`'s
# signature. Detectors take it as a dependency to make tests trivial:
# inject a mock that returns synthetic DataFrames.
BarReader = Callable[..., pd.DataFrame]


@dataclass(frozen=True, slots=True)
class DetectorContext:
    """Everything a detector needs to run one scan.

    Detectors should not reach for global state — the context carries
    the bar reader, symbols, date range, and any detector-specific
    mode parameter.
    """

    symbols: list[str]
    start: date_type
    end: date_type
    bar_reader: BarReader
    mode: str | None = None
    # Detector-specific parameters not covered by `mode`. Passed
    # through from the CLI's `--params 'k=v,k2=v2'` if present.
    params: dict[str, Any] = field(default_factory=dict)


class Detector(Protocol):
    """A research-event detector.

    Implementations must be importable, stateless across calls, and
    write nothing themselves — the scan orchestrator is the only
    write path. Detectors return events; the orchestrator persists
    them.
    """

    feature_name: str
    detector_version: str
    supported_modes: tuple[str, ...]

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        """Run one detection pass over `ctx.start` → `ctx.end` for
        the given symbols and mode. Return a list of event payloads.
        Idempotence is the orchestrator's responsibility — same bar
        + same detector + same event_type produces the same event_id
        and is deduped at insert time.
        """
        ...


# ---------- registry ----------


DETECTORS: dict[str, Detector] = {}


def register(name: str, detector: Detector) -> None:
    """Register a detector under a stable string name.

    Names are the CLI's `--detector` value. Snake_case slug, no
    spaces. Re-registration under the same name raises — duplicate
    detectors are bugs, not features.
    """
    if name in DETECTORS:
        raise ValueError(f"detector {name!r} already registered")
    DETECTORS[name] = detector


def get(name: str) -> Detector:
    """Look up a registered detector by name. KeyError if unknown."""
    if name not in DETECTORS:
        known = ", ".join(sorted(DETECTORS.keys())) or "<none>"
        raise KeyError(
            f"detector {name!r} not registered. Known detectors: {known}"
        )
    return DETECTORS[name]


def list_names() -> list[str]:
    """Sorted list of registered detector names. Used by the CLI's
    --list flag."""
    return sorted(DETECTORS.keys())


# ---------- side-effect imports ----------
# Each detector module calls `register(...)` on import. Adding a new
# detector means a new line here.

from app.research.detectors import (  # noqa: E402,F401
    displacement_candle,
    equal_levels,
    first_third_range,
    forming_volume_profile,
    fvg_formation,
    interval_true_range,
    liquidity_sweep,
    opening_gap_levels,
    opening_range_breakout,
    order_block,
    psp_candle_divergence,
    smt_htf_reference_divergence,
    swing_pivot,
    time_profile,
    volume_profile,
)
