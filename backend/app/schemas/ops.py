"""Schemas for the operator status snapshot."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

OpsCheckStatus = Literal["ok", "warn", "fail", "missing", "not_wired", "unknown"]


class OpsCheck(BaseModel):
    id: str
    label: str
    status: OpsCheckStatus
    message: str
    path: str | None = None
    exists: bool | None = None
    updated_at: datetime | None = None
    age_seconds: int | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class OpsStatusRead(BaseModel):
    fetched_at: datetime
    overall_status: Literal["ok", "warn", "fail"]
    warehouse_root: str
    insync_app_root: str
    checks: list[OpsCheck]
    alerts: list[str] = Field(default_factory=list)
