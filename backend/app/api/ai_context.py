"""Read-only preview of the AI memory context for a strategy."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeCard, ResearchEntry, Strategy
from app.db.session import get_session
from app.schemas import AiContextMemoryItem, AiContextPreviewRead

router = APIRouter(
    prefix="/strategies/{strategy_id}/ai-context",
    tags=["ai-context"],
)

BODY_CAP = 500


def _require_strategy(strategy_id: int, db: Session) -> Strategy:
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=404, detail=f"strategy {strategy_id} not found"
        )
    return strategy


@router.get("", response_model=AiContextPreviewRead)
def get_ai_context_preview(
    strategy_id: int,
    limit: int = Query(default=18, ge=1, le=50),
    db: Session = Depends(get_session),
) -> AiContextPreviewRead:
    """Show the local memory bundle available to the AI layer.

    This does not call an LLM. It makes retrieval visible so the user can
    spot stale drafts, missing formulas, or context bloat before starting
    a chat or generating a prompt.
    """
    strategy = _require_strategy(strategy_id, db)
    research_limit = max(1, limit // 2)
    knowledge_limit = max(1, limit - research_limit)

    research_entries = list(
        db.scalars(
            select(ResearchEntry)
            .where(ResearchEntry.strategy_id == strategy_id)
            .order_by(desc(ResearchEntry.updated_at), desc(ResearchEntry.created_at))
            .limit(research_limit)
        ).all()
    )
    knowledge_cards = list(
        db.scalars(
            select(KnowledgeCard)
            .where(
                or_(
                    KnowledgeCard.strategy_id.is_(None),
                    KnowledgeCard.strategy_id == strategy_id,
                ),
                KnowledgeCard.status != "archived",
            )
            .order_by(desc(KnowledgeCard.updated_at), desc(KnowledgeCard.created_at))
            .limit(knowledge_limit)
        ).all()
    )

    items: list[AiContextMemoryItem] = []
    for entry in research_entries:
        items.append(
            AiContextMemoryItem(
                id=entry.id,
                source="research_entry",
                kind=entry.kind,
                status=entry.status,
                title=entry.title,
                body=_cap(entry.body),
                scope="strategy",
                tags=entry.tags,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
        )
    for card in knowledge_cards:
        body_parts = [
            part
            for part in [
                card.summary,
                f"Formula: {card.formula}" if card.formula else None,
                card.body,
            ]
            if part
        ]
        items.append(
            AiContextMemoryItem(
                id=card.id,
                source="knowledge_card",
                kind=card.kind,
                status=card.status,
                title=card.name,
                body=_cap("\n".join(body_parts) if body_parts else None),
                scope="global" if card.strategy_id is None else "strategy",
                tags=card.tags,
                created_at=card.created_at,
                updated_at=card.updated_at,
            )
        )

    items.sort(
        key=lambda item: item.updated_at or item.created_at,
        reverse=True,
    )
    items = items[:limit]
    return AiContextPreviewRead(
        strategy_id=strategy.id,
        strategy_name=strategy.name,
        item_count=len(items),
        research_entry_count=len(research_entries),
        knowledge_card_count=len(knowledge_cards),
        items=items,
        prompt_preview=_render_prompt_preview(strategy, items),
    )


def _render_prompt_preview(
    strategy: Strategy, items: list[AiContextMemoryItem]
) -> str:
    lines = [
        f"# AI memory preview for {strategy.name}",
        "",
        "Use this local memory as context. Draft or needs_testing items are not proven facts.",
    ]
    if not items:
        lines.append("")
        lines.append("No saved research entries or knowledge cards are currently available.")
        return "\n".join(lines)

    lines.append("")
    lines.append("## Retrieved memory")
    for item in items:
        lines.append(
            f"- [{item.source} {item.kind}/{item.status}] {item.title} "
            f"({item.scope})"
        )
        if item.tags:
            lines.append(f"  tags={', '.join(item.tags)}")
        if item.body:
            lines.append(f"  {item.body}")
    return "\n".join(lines)


def _cap(text: str | None) -> str | None:
    if text is None:
        return None
    if len(text) <= BODY_CAP:
        return text
    omitted = len(text) - BODY_CAP
    return f"{text[:BODY_CAP]}\n[truncated, {omitted} chars omitted]"
