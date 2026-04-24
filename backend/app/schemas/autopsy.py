"""Pydantic schemas for the strategy autopsy report."""

from pydantic import BaseModel


class AutopsyConditionSlice(BaseModel):
    label: str
    trades: int
    net_r: float
    win_rate: float | None


class AutopsyReportRead(BaseModel):
    backtest_run_id: int
    overall_verdict: str
    edge_confidence: int
    go_live_recommendation: str  # not_ready | forward_test_only | small_size | validated
    strengths: list[str]
    weaknesses: list[str]
    overfitting_warnings: list[str]
    risk_notes: list[str]
    suggested_next_test: str
    best_conditions: list[AutopsyConditionSlice]
    worst_conditions: list[AutopsyConditionSlice]
