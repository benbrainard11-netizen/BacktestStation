"""Pydantic schemas for the data-quality endpoint."""

from pydantic import BaseModel


class DataQualityIssue(BaseModel):
    category: str
    severity: str  # "low" | "medium" | "high"
    message: str
    count: int = 0
    affected_range: str | None = None
    distort_backtest: str = "unknown"


class DataQualityReportRead(BaseModel):
    backtest_run_id: int
    symbol: str
    dataset_status: str  # "ok" | "missing" | "partial"
    total_bars: int
    first_bar_ts: str | None
    last_bar_ts: str | None
    reliability_score: int
    issues: list[DataQualityIssue]
    deferred_checks: list[str]
