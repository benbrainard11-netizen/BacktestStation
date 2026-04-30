"""Schemas for the per-strategy AI chat panel."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageRead(BaseModel):
    """One message rendered in the chat thread."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    role: Literal["user", "assistant"]
    content: str
    model: Literal["claude", "codex"]
    # Stage-3 prep: which workspace section the message belongs to
    # ("build" | "backtest" | "replay" | ...). Null for legacy single-
    # thread messages.
    section: str | None = None
    cli_session_id: str | None
    cost_usd: float | None
    created_at: datetime


class ChatTurnRequest(BaseModel):
    """POST body for a new chat turn."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1)
    model: Literal["claude", "codex"] = "claude"
    # Optional Stage-3 scope tag. When set, the message is recorded
    # against this workspace section so per-section agents can list
    # only their own thread. Backwards-compatible: omitting it keeps
    # the legacy single-thread behavior.
    section: str | None = Field(default=None, max_length=32)


class ChatTurnResponse(BaseModel):
    """Returns both new messages so the FE can append in order."""

    user: ChatMessageRead
    assistant: ChatMessageRead
