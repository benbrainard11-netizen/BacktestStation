"""Outcome computer registry + Protocol.

An outcome computer takes already-detected `ResearchEvent` rows and
populates their `outcomes` JSON column with forward-looking reaction
data. Detection answers "did the pattern fire?"; outcomes answer
"what happened next?".

Mirrors the `app.research.detectors` pattern:
  - Protocol-based, structurally typed
  - Registry keyed by `feature_name` (each detector gets one matching
    outcome computer; rare but not forbidden to have multiple
    computers for the same detector — pick by `outcome_version`)
  - Side-effect imports at the bottom register everything

Computers DO NOT modify event_data, primary_symbol, or any other
detection-time fields. They write only to the `outcomes` JSON column
and only via `runner.run_outcomes`.

See `docs/RESEARCH_DETECTORS.md` for the broader research-knowledge
layer architecture.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

import pandas as pd

from app.db.models import ResearchEvent

BarReader = Callable[..., pd.DataFrame]


class OutcomeComputer(Protocol):
    """Computes the `outcomes` dict for one ResearchEvent.

    Implementations must be stateless across calls and idempotent —
    same inputs produce the same outcomes dict. The runner calls
    `compute(event, bar_reader)` and writes the returned dict (or
    None to skip) to `event.outcomes`.
    """

    feature_name: str
    outcome_version: str

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        ...


# ---------- registry ----------


OUTCOMES: dict[str, OutcomeComputer] = {}


def register(name: str, computer: OutcomeComputer) -> None:
    """Register an outcome computer under a stable string name.

    The CLI `--feature-name` value picks a computer by its
    `feature_name`; the registry key is what the CLI looks up when
    multiple computers exist for the same feature_name (rare).
    """
    if name in OUTCOMES:
        raise ValueError(f"outcome computer {name!r} already registered")
    OUTCOMES[name] = computer


def get(name: str) -> OutcomeComputer:
    if name not in OUTCOMES:
        known = ", ".join(sorted(OUTCOMES.keys())) or "<none>"
        raise KeyError(
            f"outcome computer {name!r} not registered. Known: {known}"
        )
    return OUTCOMES[name]


def get_by_feature(feature_name: str) -> OutcomeComputer:
    """Find the registered computer for a given feature_name. Errors
    if zero or multiple match."""
    matches = [c for c in OUTCOMES.values() if c.feature_name == feature_name]
    if not matches:
        known = ", ".join(sorted({c.feature_name for c in OUTCOMES.values()}))
        raise KeyError(
            f"no outcome computer registered for feature_name={feature_name!r}. "
            f"Known feature_names: {known}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"multiple outcome computers registered for {feature_name!r}; "
            "use `get(name)` with the explicit registry key"
        )
    return matches[0]


def list_names() -> list[str]:
    return sorted(OUTCOMES.keys())


# ---------- side-effect imports ----------

from app.research.outcomes import (  # noqa: E402,F401
    smt_htf_reactions,
)
