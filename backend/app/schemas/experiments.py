"""Pydantic schemas for the Experiment Ledger.

Experiments capture structured research: a hypothesis, a baseline run,
an optional variant run, what changed between them, and a decision
about what to do next. The shape is intentionally minimal — fields
become structured later if real usage shows the need.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Decision vocabulary — surfaced at /api/experiments/decisions, mirrors
# STRATEGY_STAGES / NOTE_TYPES patterns.
EXPERIMENT_DECISIONS: tuple[str, ...] = (
    "pending",
    "promote",
    "reject",
    "retest",
    "forward_test",
    "archive",
)


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_version_id: int
    hypothesis: str = Field(..., min_length=1)
    baseline_run_id: int | None = None
    variant_run_id: int | None = None
    change_description: str | None = None
    decision: str = Field(default="pending")
    notes: str | None = None

    @field_validator("hypothesis", mode="after")
    @classmethod
    def _trim_hypothesis(cls, value: str) -> str:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("hypothesis must be non-empty")
        return trimmed

    @field_validator("decision", mode="after")
    @classmethod
    def _valid_decision(cls, value: str) -> str:
        if value not in EXPERIMENT_DECISIONS:
            raise ValueError(
                f"decision must be one of {EXPERIMENT_DECISIONS}, "
                f"got {value!r}"
            )
        return value


class ExperimentUpdate(BaseModel):
    """PATCH /api/experiments/{id} body. Only fields present are applied."""

    model_config = ConfigDict(extra="forbid")

    hypothesis: str | None = None
    baseline_run_id: int | None = None
    variant_run_id: int | None = None
    change_description: str | None = None
    decision: str | None = None
    notes: str | None = None

    @field_validator("hypothesis", mode="after")
    @classmethod
    def _trim_hypothesis(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("hypothesis must be non-empty after trimming")
        return trimmed

    @field_validator("decision", mode="after")
    @classmethod
    def _valid_decision(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in EXPERIMENT_DECISIONS:
            raise ValueError(
                f"decision must be one of {EXPERIMENT_DECISIONS}, "
                f"got {value!r}"
            )
        return value


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_version_id: int
    hypothesis: str
    baseline_run_id: int | None
    variant_run_id: int | None
    change_description: str | None
    decision: str
    notes: str | None
    created_at: datetime
    updated_at: datetime | None


class ExperimentDecisionsRead(BaseModel):
    """GET /api/experiments/decisions body."""

    decisions: list[str] = Field(
        default_factory=lambda: list(EXPERIMENT_DECISIONS)
    )
