"""Schemas for inspecting the AI memory context bundle."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


MemorySource = Literal["research_entry", "knowledge_card"]


class AiContextMemoryItem(BaseModel):
    """One saved memory item eligible for an AI context bundle."""

    id: int
    source: MemorySource
    kind: str
    status: str
    title: str
    body: str | None = None
    scope: str
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AiContextPreviewRead(BaseModel):
    """GET /strategies/{id}/ai-context response."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: int
    strategy_name: str
    item_count: int
    research_entry_count: int
    knowledge_card_count: int
    items: list[AiContextMemoryItem]
    prompt_preview: str
