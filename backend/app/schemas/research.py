"""Schemas for the per-strategy Research workspace."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.knowledge import (
    KNOWLEDGE_CARD_KINDS,
    KNOWLEDGE_CARD_STATUSES,
)


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
    knowledge_card_ids: list[int] | None
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
    knowledge_card_ids: list[int] | None = None
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
    knowledge_card_ids: list[int] | None = None
    tags: list[str] | None = None


class ResearchExperimentCreate(BaseModel):
    """POST body for turning a hypothesis into an Experiment."""

    model_config = ConfigDict(extra="forbid")

    strategy_version_id: int | None = None
    baseline_run_id: int | None = None
    variant_run_id: int | None = None
    change_description: str | None = None
    notes: str | None = None


class ResearchEntryPromoteRequest(BaseModel):
    """POST body for promoting a research entry into a knowledge card.

    Every field is optional. Defaults pull from the entry: kind defaults
    to "research_playbook"; name defaults to entry.title; body and tags
    default to the entry's; strategy_id defaults to the entry's strategy.
    Status is computed from (entry.kind, entry.status) unless overridden.
    Payload values replace entry values — they don't merge.
    """

    model_config = ConfigDict(extra="forbid")

    kind: str | None = None
    status: str | None = None
    strategy_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = Field(default=None, max_length=800)
    body: str | None = None
    formula: str | None = None
    tags: list[str] | None = None

    @field_validator("kind", mode="after")
    @classmethod
    def _valid_kind(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in KNOWLEDGE_CARD_KINDS:
            raise ValueError(
                f"kind must be one of {KNOWLEDGE_CARD_KINDS}, got {value!r}"
            )
        return value

    @field_validator("status", mode="after")
    @classmethod
    def _valid_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in KNOWLEDGE_CARD_STATUSES:
            raise ValueError(
                "status must be one of "
                f"{KNOWLEDGE_CARD_STATUSES}, got {value!r}"
            )
        return value

    @field_validator("name", mode="after")
    @classmethod
    def _trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("name must be non-empty after trimming")
        return trimmed

    @field_validator("summary", "body", "formula", mode="after")
    @classmethod
    def _trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("tags", mode="after")
    @classmethod
    def _normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in value:
            trimmed = raw.strip()
            if trimmed == "" or trimmed in seen:
                continue
            seen.add(trimmed)
            cleaned.append(trimmed)
        return cleaned or None
