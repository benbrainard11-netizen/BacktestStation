"""Pydantic schemas for research notes."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Research Workspace note vocabulary. Mirrors the STRATEGY_STAGES pattern
# in schemas/results.py — frontend reads this through GET /api/notes/types.
NOTE_TYPES: tuple[str, ...] = (
    "observation",
    "hypothesis",
    "question",
    "decision",
    "bug",
    "risk_note",
)


def _clean_tags(value: list[str] | None) -> list[str] | None:
    """Trim, dedupe, drop empties. Returns None if the result is empty."""
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


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(..., min_length=1)
    note_type: str = Field(default="observation")
    tags: list[str] | None = None
    strategy_id: int | None = None
    strategy_version_id: int | None = None
    backtest_run_id: int | None = None
    trade_id: int | None = None

    @field_validator("note_type", mode="after")
    @classmethod
    def _valid_note_type(cls, value: str) -> str:
        if value not in NOTE_TYPES:
            raise ValueError(
                f"note_type must be one of {NOTE_TYPES}, got {value!r}"
            )
        return value

    @field_validator("tags", mode="after")
    @classmethod
    def _normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        return _clean_tags(value)


class NoteUpdate(BaseModel):
    """PATCH /api/notes/{id} body. Only fields present in the request
    are applied; omit a field to leave it untouched. Cannot move a note
    between attachments — delete and recreate for that."""

    model_config = ConfigDict(extra="forbid")

    body: str | None = None
    note_type: str | None = None
    tags: list[str] | None = None

    @field_validator("body", mode="after")
    @classmethod
    def _trim_body(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("body must be non-empty after trimming")
        return trimmed

    @field_validator("note_type", mode="after")
    @classmethod
    def _valid_note_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in NOTE_TYPES:
            raise ValueError(
                f"note_type must be one of {NOTE_TYPES}, got {value!r}"
            )
        return value

    @field_validator("tags", mode="after")
    @classmethod
    def _normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        return _clean_tags(value)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int | None
    strategy_version_id: int | None
    backtest_run_id: int | None
    trade_id: int | None
    note_type: str
    tags: list[str] | None
    body: str
    created_at: datetime
    updated_at: datetime | None


class NoteTypesRead(BaseModel):
    """GET /api/notes/types body. Surfaces NOTE_TYPES vocabulary so the
    frontend stays driven by the backend."""

    types: list[str] = Field(default_factory=lambda: list(NOTE_TYPES))
