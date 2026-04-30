"""Knowledge Library API.

Cards store reusable quant memory: market concepts, orderflow formulas,
setup archetypes, research playbooks, and risk/execution rules. This is
the backend foundation for "teach the app my formulas and workflow"
without pretending the model itself has been trained.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeCard, ResearchEntry, Strategy
from app.db.session import get_session
from app.schemas import (
    KNOWLEDGE_CARD_KINDS,
    KNOWLEDGE_CARD_STATUSES,
    KnowledgeCardCreate,
    KnowledgeCardKindsRead,
    KnowledgeCardRead,
    KnowledgeCardStatusesRead,
    KnowledgeCardUpdate,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _require_card(db: Session, card_id: int) -> KnowledgeCard:
    card = db.get(KnowledgeCard, card_id)
    if card is None:
        raise HTTPException(
            status_code=404, detail=f"Knowledge card {card_id} not found"
        )
    return card


def _validate_strategy(db: Session, strategy_id: int | None) -> None:
    if strategy_id is None:
        return
    if db.get(Strategy, strategy_id) is None:
        raise HTTPException(
            status_code=422, detail=f"strategy_id {strategy_id} not found"
        )


@router.get("/kinds", response_model=KnowledgeCardKindsRead)
def list_knowledge_kinds() -> dict:
    return {"kinds": list(KNOWLEDGE_CARD_KINDS)}


@router.get("/statuses", response_model=KnowledgeCardStatusesRead)
def list_knowledge_statuses() -> dict:
    return {"statuses": list(KNOWLEDGE_CARD_STATUSES)}


@router.post("/cards", response_model=KnowledgeCardRead, status_code=201)
def create_knowledge_card(
    payload: KnowledgeCardCreate,
    db: Session = Depends(get_session),
) -> KnowledgeCard:
    _validate_strategy(db, payload.strategy_id)
    card = KnowledgeCard(
        strategy_id=payload.strategy_id,
        kind=payload.kind,
        name=payload.name,
        summary=payload.summary,
        body=payload.body,
        formula=payload.formula,
        inputs=payload.inputs,
        use_cases=payload.use_cases,
        failure_modes=payload.failure_modes,
        status=payload.status,
        source=payload.source,
        tags=payload.tags,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.get("/cards", response_model=list[KnowledgeCardRead])
def list_knowledge_cards(
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    strategy_id: int | None = Query(default=None),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[KnowledgeCard]:
    if kind is not None and kind not in KNOWLEDGE_CARD_KINDS:
        raise HTTPException(
            status_code=422,
            detail=f"kind must be one of {KNOWLEDGE_CARD_KINDS}, got {kind!r}",
        )
    if status is not None and status not in KNOWLEDGE_CARD_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"status must be one of {KNOWLEDGE_CARD_STATUSES}, "
                f"got {status!r}"
            ),
        )
    _validate_strategy(db, strategy_id)

    statement = select(KnowledgeCard)
    if kind is not None:
        statement = statement.where(KnowledgeCard.kind == kind)
    if status is not None:
        statement = statement.where(KnowledgeCard.status == status)
    if strategy_id is not None:
        statement = statement.where(KnowledgeCard.strategy_id == strategy_id)
    if q is not None and q.strip() != "":
        needle = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                KnowledgeCard.name.ilike(needle),
                KnowledgeCard.summary.ilike(needle),
                KnowledgeCard.body.ilike(needle),
                KnowledgeCard.formula.ilike(needle),
                KnowledgeCard.source.ilike(needle),
            )
        )
    statement = statement.order_by(
        KnowledgeCard.created_at.desc(), KnowledgeCard.id.desc()
    )
    rows = list(db.scalars(statement).all())
    if tag is not None:
        rows = [r for r in rows if r.tags is not None and tag in r.tags]
    return rows


@router.get("/cards/{card_id}", response_model=KnowledgeCardRead)
def get_knowledge_card(
    card_id: int, db: Session = Depends(get_session)
) -> KnowledgeCard:
    return _require_card(db, card_id)


@router.patch("/cards/{card_id}", response_model=KnowledgeCardRead)
def update_knowledge_card(
    card_id: int,
    payload: KnowledgeCardUpdate,
    db: Session = Depends(get_session),
) -> KnowledgeCard:
    card = _require_card(db, card_id)
    touched = payload.model_fields_set

    if "strategy_id" in touched:
        _validate_strategy(db, payload.strategy_id)
        card.strategy_id = payload.strategy_id
    if "kind" in touched and payload.kind is not None:
        card.kind = payload.kind
    if "name" in touched and payload.name is not None:
        card.name = payload.name
    if "summary" in touched:
        card.summary = payload.summary
    if "body" in touched:
        card.body = payload.body
    if "formula" in touched:
        card.formula = payload.formula
    if "inputs" in touched:
        card.inputs = payload.inputs
    if "use_cases" in touched:
        card.use_cases = payload.use_cases
    if "failure_modes" in touched:
        card.failure_modes = payload.failure_modes
    if "status" in touched and payload.status is not None:
        card.status = payload.status
    if "source" in touched:
        card.source = payload.source
    if "tags" in touched:
        card.tags = payload.tags

    card.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(card)
    return card


@router.delete("/cards/{card_id}", status_code=204)
def delete_knowledge_card(
    card_id: int, db: Session = Depends(get_session)
) -> None:
    card = _require_card(db, card_id)
    linked_entries = list(
        db.scalars(
            select(ResearchEntry).where(
                ResearchEntry.knowledge_card_ids.is_not(None)
            )
        ).all()
    )
    for entry in linked_entries:
        if entry.knowledge_card_ids is None:
            continue
        next_ids = [
            existing_id
            for existing_id in entry.knowledge_card_ids
            if existing_id != card.id
        ]
        if len(next_ids) != len(entry.knowledge_card_ids):
            entry.knowledge_card_ids = next_ids or None
    db.delete(card)
    db.commit()
    return None
