"""Schemas for the read-only Memory Health endpoint.

Memory Health is a quick visibility check the user can scan before
trusting the knowledge memory database for AI context. It surfaces
weak/stale/unproven cards and entries so the user notices rot before
the assistant relies on it. Read-only — never mutates data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


KnowledgeHealthSeverity = Literal["info", "warn", "error"]


class KnowledgeHealthCounts(BaseModel):
    """Aggregate counts over the full population of knowledge cards
    plus a few cross-table signals (entries with multiple linked cards).
    """

    model_config = ConfigDict(extra="forbid")

    total_cards: int
    trusted_cards: int
    needs_testing_cards: int
    draft_cards: int
    rejected_cards: int
    archived_cards: int
    trusted_without_evidence: int
    needs_testing_without_run: int
    stale_drafts: int
    promoted_entries_with_multiple_cards: int


class KnowledgeHealthIssue(BaseModel):
    """One actionable health observation. Each issue points at the row
    the user should look at — `card_id` for card-level issues,
    `research_entry_id` for entry-level issues. `strategy_id` is set
    when the offending row is strategy-scoped, so the UI can group."""

    model_config = ConfigDict(extra="forbid")

    code: str
    severity: KnowledgeHealthSeverity
    title: str
    detail: str
    card_id: int | None = None
    research_entry_id: int | None = None
    strategy_id: int | None = None


class KnowledgeHealthRead(BaseModel):
    """Top-level response from GET /api/knowledge/health."""

    model_config = ConfigDict(extra="forbid")

    counts: KnowledgeHealthCounts
    issues: list[KnowledgeHealthIssue]
    generated_at: datetime
