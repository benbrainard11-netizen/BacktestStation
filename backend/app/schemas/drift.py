"""API response shapes for the Forward Drift Monitor."""

from datetime import datetime

from pydantic import BaseModel, Field


class DriftResultRead(BaseModel):
    """One drift signal computation result.

    `signal_type` enumerates which signal this is (currently `win_rate` or
    `entry_time`); each has its own interpretation of `live_value`,
    `baseline_value`, and `deviation`. See `app.services.drift_comparison`
    for the formulas.

    `status` is a tri-color summary: OK / WATCH / WARN. `incomplete` flags
    when the sample size was below the threshold for a reliable read —
    callers should display the result with a "tentative" hint.
    """

    signal_type: str
    status: str  # "OK" | "WATCH" | "WARN"
    live_value: float | None
    baseline_value: float | None
    deviation: float | None
    sample_size_live: int
    sample_size_baseline: int
    incomplete: bool
    message: str


class DriftComparisonRead(BaseModel):
    """Full drift comparison for a strategy version."""

    strategy_version_id: int
    baseline_run_id: int
    live_run_id: int | None
    computed_at: datetime
    results: list[DriftResultRead] = Field(default_factory=list)


class StrategyVersionBaselineUpdate(BaseModel):
    """Body for PATCH /strategy-versions/{id}/baseline.

    `run_id=None` clears the baseline. Otherwise the referenced run must
    exist and must NOT be source="live" — comparing live against itself
    is meaningless.
    """

    run_id: int | None
