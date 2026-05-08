"""Pydantic schemas for the Research Event Store.

A research event is one per-detector observation in market data.
See `docs/RESEARCH_KNOWLEDGE_LAYER.md` for the surrounding taxonomy.

The shape mirrors `app.db.models.ResearchEvent`. `event_id` is the
idempotency key — same inputs produce the same id, and the writer
service (`app.services.research_events.record_event`) skips
duplicates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_symbols(value: list[str]) -> list[str]:
    """Trim, dedupe (preserve order), drop empties. Required to be
    non-empty after normalization."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in value:
        trimmed = raw.strip()
        if trimmed == "" or trimmed in seen:
            continue
        seen.add(trimmed)
        cleaned.append(trimmed)
    if not cleaned:
        raise ValueError("symbols must contain at least one non-empty entry")
    return cleaned


class ResearchEventCreate(BaseModel):
    """Body for `POST /api/research/events` (write-side; primarily used
    by detector scan jobs via `services.research_events.record_event`,
    not exposed to the frontend in v1)."""

    model_config = ConfigDict(extra="forbid")

    feature_name: str = Field(..., min_length=1, max_length=80)
    event_type: str = Field(..., min_length=1, max_length=60)
    bar_end_utc: datetime
    primary_symbol: str = Field(..., min_length=1, max_length=40)
    symbols: list[str] = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1, max_length=20)
    event_data: dict[str, Any]

    side: str | None = Field(default=None, max_length=20)
    knowledge_card_id: int | None = None
    context: dict[str, Any] | None = None
    outcomes: dict[str, Any] | None = None
    replay_pointer: dict[str, Any] | None = None
    source_dataset: str | None = None
    source_run_id: int | None = None
    detector_version: str | None = Field(default=None, max_length=40)

    @field_validator("symbols", mode="after")
    @classmethod
    def _normalize_symbols_list(cls, value: list[str]) -> list[str]:
        return _normalize_symbols(value)

    @field_validator("primary_symbol", mode="after")
    @classmethod
    def _trim_primary(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("primary_symbol must be non-empty")
        return trimmed


class ResearchEventRead(BaseModel):
    """`GET /api/research/events` row shape."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    feature_name: str
    knowledge_card_id: int | None
    event_type: str
    bar_end_utc: datetime
    primary_symbol: str
    symbols: list[str]
    timeframe: str
    side: str | None
    event_data: dict[str, Any]
    context: dict[str, Any] | None
    outcomes: dict[str, Any] | None
    replay_pointer: dict[str, Any] | None
    source_dataset: str | None
    source_run_id: int | None
    detector_version: str | None
    created_at: datetime
