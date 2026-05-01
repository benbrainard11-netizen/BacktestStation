"""Schemas for the Knowledge Library.

Knowledge cards are reusable memory objects for quant concepts,
orderflow formulas, setup archetypes, and research playbooks. They are
not claims of truth by themselves; `status` records whether Ben treats
the card as draft, needs-testing, trusted, rejected, or archived.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

KNOWLEDGE_CARD_KINDS: tuple[str, ...] = (
    "market_concept",
    "orderflow_formula",
    "indicator_formula",
    "setup_archetype",
    "research_playbook",
    "risk_rule",
    "execution_concept",
)

KNOWLEDGE_CARD_STATUSES: tuple[str, ...] = (
    "draft",
    "needs_testing",
    "trusted",
    "rejected",
    "archived",
)


def _clean_list(value: list[str] | None) -> list[str] | None:
    """Trim, dedupe, and drop empty strings from a small text list."""
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


def _trim_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class KnowledgeCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int | None
    kind: str
    name: str
    summary: str | None
    body: str | None
    formula: str | None
    inputs: list[str] | None
    use_cases: list[str] | None
    failure_modes: list[str] | None
    status: str
    source: str | None
    linked_run_id: int | None
    linked_version_id: int | None
    linked_research_entry_id: int | None
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime | None


class KnowledgeCardCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    name: str = Field(..., min_length=1, max_length=160)
    summary: str | None = Field(default=None, max_length=800)
    body: str | None = None
    formula: str | None = None
    inputs: list[str] | None = None
    use_cases: list[str] | None = None
    failure_modes: list[str] | None = None
    status: str = Field(default="draft")
    source: str | None = None
    linked_run_id: int | None = None
    linked_version_id: int | None = None
    linked_research_entry_id: int | None = None
    tags: list[str] | None = None
    strategy_id: int | None = None

    @field_validator("kind", mode="after")
    @classmethod
    def _valid_kind(cls, value: str) -> str:
        if value not in KNOWLEDGE_CARD_KINDS:
            raise ValueError(
                f"kind must be one of {KNOWLEDGE_CARD_KINDS}, got {value!r}"
            )
        return value

    @field_validator("status", mode="after")
    @classmethod
    def _valid_status(cls, value: str) -> str:
        if value not in KNOWLEDGE_CARD_STATUSES:
            raise ValueError(
                "status must be one of "
                f"{KNOWLEDGE_CARD_STATUSES}, got {value!r}"
            )
        return value

    @field_validator("name", mode="after")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("name must be non-empty after trimming")
        return trimmed

    @field_validator("summary", "body", "formula", "source", mode="after")
    @classmethod
    def _trim_text(cls, value: str | None) -> str | None:
        return _trim_optional(value)

    @field_validator(
        "inputs", "use_cases", "failure_modes", "tags", mode="after"
    )
    @classmethod
    def _normalize_lists(cls, value: list[str] | None) -> list[str] | None:
        return _clean_list(value)


class KnowledgeCardUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = Field(default=None, max_length=800)
    body: str | None = None
    formula: str | None = None
    inputs: list[str] | None = None
    use_cases: list[str] | None = None
    failure_modes: list[str] | None = None
    status: str | None = None
    source: str | None = None
    linked_run_id: int | None = None
    linked_version_id: int | None = None
    linked_research_entry_id: int | None = None
    tags: list[str] | None = None
    strategy_id: int | None = None

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

    @field_validator("summary", "body", "formula", "source", mode="after")
    @classmethod
    def _trim_text(cls, value: str | None) -> str | None:
        return _trim_optional(value)

    @field_validator(
        "inputs", "use_cases", "failure_modes", "tags", mode="after"
    )
    @classmethod
    def _normalize_lists(cls, value: list[str] | None) -> list[str] | None:
        return _clean_list(value)


class KnowledgeCardKindsRead(BaseModel):
    kinds: list[str] = Field(default_factory=lambda: list(KNOWLEDGE_CARD_KINDS))


class KnowledgeCardStatusesRead(BaseModel):
    statuses: list[str] = Field(
        default_factory=lambda: list(KNOWLEDGE_CARD_STATUSES)
    )
