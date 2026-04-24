"""Pydantic schemas for research notes."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    body: str = Field(..., min_length=1)
    backtest_run_id: int | None = None
    trade_id: int | None = None


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    backtest_run_id: int | None
    trade_id: int | None
    body: str
    created_at: datetime
