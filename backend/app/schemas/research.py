"""Schemas for the per-strategy Research workspace."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ResearchKind = Literal["hypothesis", "decision", "question"]
ResearchStatus = Literal["open", "running", "confirmed", "rejected", "done"]

RESEARCH_KINDS: tuple[str, ...] = ("hypothesis", "decision", "question")
RESEARCH_STATUSES: tuple[str, ...] = (
    "open",
    "running",
    "confirmed",
    "rejected",
    "done",
)

# Each kind has a restricted status vocabulary. Hypotheses move through
# the test cycle (open → running → confirmed/rejected); decisions are
# permanent records (always done); questions are open until answered.
# Codex review 2026-04-30 caught that the old Literal alone allowed
# nonsense pairs like decision=confirmed.
ALLOWED_STATUSES_BY_KIND: dict[str, tuple[str, ...]] = {
    "hypothesis": ("open", "running", "confirmed", "rejected"),
    "decision": ("done",),
    "question": ("open", "done"),
}


def validate_kind_status_pair(kind: str, status: str) -> None:
    """Raise ValueError if the (kind, status) combination isn't allowed."""
    allowed = ALLOWED_STATUSES_BY_KIND.get(kind)
    if allowed is None:
        raise ValueError(
            f"kind must be one of {RESEARCH_KINDS}, got {kind!r}"
        )
    if status not in allowed:
        raise ValueError(
            f"status {status!r} not allowed for kind {kind!r}; "
            f"allowed: {allowed}"
        )


class ResearchEntryRead(BaseModel):
    """One research entry rendered in the workspace."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    kind: ResearchKind
    title: str
    body: str | None
    status: ResearchStatus
    linked_run_id: int | None
    linked_version_id: int | None
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime | None


class ResearchEntryCreate(BaseModel):
    """POST body to create an entry. `strategy_id` comes from the URL."""

    model_config = ConfigDict(extra="forbid")

    kind: ResearchKind
    title: str = Field(..., min_length=1, max_length=200)
    body: str | None = None
    status: ResearchStatus = "open"
    linked_run_id: int | None = None
    linked_version_id: int | None = None
    tags: list[str] | None = None

    def model_post_init(self, _: object) -> None:
        validate_kind_status_pair(self.kind, self.status)


class ResearchEntryUpdate(BaseModel):
    """PATCH body. Every field is optional; only the ones present are
    updated, matching how the rest of the app's PATCH endpoints work."""

    model_config = ConfigDict(extra="forbid")

    kind: ResearchKind | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None
    status: ResearchStatus | None = None
    linked_run_id: int | None = None
    linked_version_id: int | None = None
    tags: list[str] | None = None
