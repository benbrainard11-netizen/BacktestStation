"""API response schemas for imported strategy results."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StrategyVersionRead(OrmModel):
    id: int
    strategy_id: int
    version: str
    entry_md: str | None
    exit_md: str | None
    risk_md: str | None
    git_commit_sha: str | None
    created_at: datetime
    archived_at: datetime | None = None


class StrategyRead(OrmModel):
    id: int
    name: str
    slug: str
    description: str | None
    status: str
    tags: list[str] | None
    created_at: datetime
    versions: list[StrategyVersionRead] = []


class BacktestRunRead(OrmModel):
    id: int
    strategy_version_id: int
    name: str | None
    symbol: str
    timeframe: str | None
    session_label: str | None
    start_ts: datetime | None
    end_ts: datetime | None
    import_source: str | None
    source: str
    status: str
    tags: list[str] | None = None
    created_at: datetime


class TradeRead(OrmModel):
    id: int
    backtest_run_id: int
    entry_ts: datetime
    exit_ts: datetime | None
    symbol: str
    side: str
    entry_price: float
    exit_price: float | None
    stop_price: float | None
    target_price: float | None
    size: float
    pnl: float | None
    r_multiple: float | None
    exit_reason: str | None
    tags: list[str] | None


class EquityPointRead(OrmModel):
    id: int
    backtest_run_id: int
    ts: datetime
    equity: float
    drawdown: float | None


class RunMetricsRead(OrmModel):
    id: int
    backtest_run_id: int
    net_pnl: float | None
    net_r: float | None
    win_rate: float | None
    profit_factor: float | None
    max_drawdown: float | None
    avg_r: float | None
    avg_win: float | None
    avg_loss: float | None
    trade_count: int | None
    longest_losing_streak: int | None
    best_trade: float | None
    worst_trade: float | None


class ConfigSnapshotRead(OrmModel):
    id: int
    backtest_run_id: int
    payload: dict[str, Any]
    created_at: datetime


class ImportBacktestResponse(OrmModel):
    backtest_id: int
    strategy_id: int
    strategy_version_id: int
    trades_imported: int
    equity_points_imported: int
    metrics_imported: bool
    config_imported: bool


class BacktestRunUpdate(BaseModel):
    """PATCH /api/backtests/{id} body. Send `null` to clear the name."""

    name: str | None = Field(default=None)

    @field_validator("name", mode="after")
    @classmethod
    def _trim_or_reject_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("name must be non-empty after trimming, or null to clear")
        return trimmed


class BacktestRunTagsUpdate(BaseModel):
    """PUT /api/backtests/{id}/tags body. Replaces the full tag list."""

    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="after")
    @classmethod
    def _clean_tags(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in value:
            trimmed = raw.strip()
            if trimmed == "":
                continue
            if trimmed in seen:
                continue
            seen.add(trimmed)
            cleaned.append(trimmed)
        return cleaned


# Strategy lifecycle vocabulary. Frontend pipeline board columns mirror this.
STRATEGY_STAGES: tuple[str, ...] = (
    "idea",
    "research",
    "building",
    "backtest_validated",
    "forward_test",
    "live",
    "retired",
    "archived",
)


class StrategyCreate(BaseModel):
    """POST /api/strategies body."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    status: str = Field(default="idea", max_length=20)
    tags: list[str] | None = None

    @field_validator("name", mode="after")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("name must be non-empty")
        return trimmed

    @field_validator("slug", mode="after")
    @classmethod
    def _normalize_slug(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if trimmed == "":
            raise ValueError("slug must be non-empty")
        return trimmed

    @field_validator("status", mode="after")
    @classmethod
    def _valid_status(cls, value: str) -> str:
        if value not in STRATEGY_STAGES:
            raise ValueError(
                f"status must be one of {STRATEGY_STAGES}, got {value!r}"
            )
        return value


class StrategyUpdate(BaseModel):
    """PATCH /api/strategies/{id} body. Only fields present in the request
    are applied; omit a field to leave it untouched."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    status: str | None = None
    tags: list[str] | None = None

    @field_validator("name", mode="after")
    @classmethod
    def _trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("name must be non-empty after trimming")
        return trimmed

    @field_validator("status", mode="after")
    @classmethod
    def _valid_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in STRATEGY_STAGES:
            raise ValueError(
                f"status must be one of {STRATEGY_STAGES}, got {value!r}"
            )
        return value


class StrategyVersionCreate(BaseModel):
    """POST /api/strategies/{id}/versions body."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(..., min_length=1, max_length=40)
    entry_md: str | None = None
    exit_md: str | None = None
    risk_md: str | None = None
    git_commit_sha: str | None = Field(default=None, max_length=40)

    @field_validator("version", mode="after")
    @classmethod
    def _trim_version(cls, value: str) -> str:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("version must be non-empty")
        return trimmed


class StrategyVersionUpdate(BaseModel):
    """PATCH /api/strategy-versions/{id} body."""

    model_config = ConfigDict(extra="forbid")

    version: str | None = None
    entry_md: str | None = None
    exit_md: str | None = None
    risk_md: str | None = None
    git_commit_sha: str | None = None


class StrategyStagesRead(BaseModel):
    """GET /api/strategies/stages body. Exposes the lifecycle vocabulary so
    the frontend pipeline board column order is driven by the backend."""

    stages: list[str] = Field(default_factory=lambda: list(STRATEGY_STAGES))
