"""Knowledge Library API.

Cards store reusable quant memory: market concepts, orderflow formulas,
setup archetypes, research playbooks, and risk/execution rules. This is
the backend foundation for "teach the app my formulas and workflow"
without pretending the model itself has been trained.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    KnowledgeCard,
    ResearchEntry,
    Strategy,
    StrategyVersion,
)
from app.db.session import get_session
from app.schemas import (
    KNOWLEDGE_CARD_KINDS,
    KNOWLEDGE_CARD_STATUSES,
    KnowledgeCardCreate,
    KnowledgeCardKindsRead,
    KnowledgeCardRead,
    KnowledgeCardStatusesRead,
    KnowledgeCardUpdate,
    KnowledgeHealthCounts,
    KnowledgeHealthIssue,
    KnowledgeHealthRead,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# A draft card untouched for this many days is "stale" — long enough
# to outlive a normal "drafted but haven't gotten back to it" window
# but short enough that it surfaces stuff Ben has actually forgotten.
_STALE_DRAFT_DAYS = 30

# Severity ranking for deterministic sort order in /health responses.
# Higher number = louder; we list error first, then warn, then info.
_SEVERITY_ORDER: dict[str, int] = {"error": 0, "warn": 1, "info": 2}


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


def _validate_evidence_links(
    *,
    db: Session,
    card_strategy_id: int | None,
    linked_run_id: int | None,
    linked_version_id: int | None,
    linked_research_entry_id: int | None,
) -> None:
    """Confirm each non-None evidence pointer exists, and — when the card
    is strategy-scoped — that each link belongs to the same strategy.

    Global cards (card_strategy_id is None) skip the scope check: a
    cross-strategy concept can legitimately cite evidence from any
    strategy that tested it.
    """
    if linked_version_id is not None:
        version = db.get(StrategyVersion, linked_version_id)
        if version is None:
            raise HTTPException(
                status_code=422,
                detail=f"linked_version_id {linked_version_id} not found",
            )
        if (
            card_strategy_id is not None
            and version.strategy_id != card_strategy_id
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"linked_version_id {linked_version_id} belongs to a "
                    f"different strategy ({version.strategy_id})"
                ),
            )

    if linked_run_id is not None:
        run = db.get(BacktestRun, linked_run_id)
        if run is None:
            raise HTTPException(
                status_code=422,
                detail=f"linked_run_id {linked_run_id} not found",
            )
        if card_strategy_id is not None:
            run_strategy_id = (
                run.strategy_version.strategy_id
                if run.strategy_version is not None
                else None
            )
            if run_strategy_id != card_strategy_id:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"linked_run_id {linked_run_id} belongs to a "
                        f"different strategy ({run_strategy_id})"
                    ),
                )

    if linked_research_entry_id is not None:
        entry = db.get(ResearchEntry, linked_research_entry_id)
        if entry is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    "linked_research_entry_id "
                    f"{linked_research_entry_id} not found"
                ),
            )
        if (
            card_strategy_id is not None
            and entry.strategy_id != card_strategy_id
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"linked_research_entry_id {linked_research_entry_id} "
                    f"belongs to a different strategy ({entry.strategy_id})"
                ),
            )


@router.get("/health", response_model=KnowledgeHealthRead)
def knowledge_health(
    db: Session = Depends(get_session),
) -> KnowledgeHealthRead:
    """Read-only health check over the knowledge memory database.

    Surfaces weak/stale/unproven cards so the user notices rot before
    the assistant relies on this memory. Never mutates state — counts +
    issues only. Cheap enough to call on every Library page load.
    """
    cards = list(db.scalars(select(KnowledgeCard)).all())
    entries = list(db.scalars(select(ResearchEntry)).all())

    counts_by_status: dict[str, int] = {
        "trusted": 0,
        "needs_testing": 0,
        "draft": 0,
        "rejected": 0,
        "archived": 0,
    }
    trusted_without_evidence = 0
    needs_testing_without_run = 0
    stale_drafts = 0

    issues: list[KnowledgeHealthIssue] = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stale_threshold = now - timedelta(days=_STALE_DRAFT_DAYS)

    for card in cards:
        if card.status in counts_by_status:
            counts_by_status[card.status] += 1

        # Archived and rejected cards are by definition not active
        # memory; the user has explicitly de-staged them, so they don't
        # generate hygiene issues even if their links are missing.
        if card.status in ("archived", "rejected"):
            continue

        if card.status == "trusted" and (
            card.linked_run_id is None
            and card.linked_version_id is None
            and card.linked_research_entry_id is None
        ):
            trusted_without_evidence += 1
            issues.append(
                KnowledgeHealthIssue(
                    code="trusted_without_evidence",
                    severity="warn",
                    title="Trusted card has no evidence link",
                    detail=(
                        f"Card #{card.id} \"{card.name}\" is marked trusted "
                        "but has no linked run, version, or research entry. "
                        "Wire up the evidence behind it or downgrade to "
                        "needs_testing."
                    ),
                    card_id=card.id,
                    strategy_id=card.strategy_id,
                )
            )

        if card.status == "needs_testing" and card.linked_run_id is None:
            needs_testing_without_run += 1
            issues.append(
                KnowledgeHealthIssue(
                    code="needs_testing_without_run",
                    severity="info",
                    title="needs_testing card has no linked run",
                    detail=(
                        f"Card #{card.id} \"{card.name}\" is queued for "
                        "testing but no backtest run is linked. The whole "
                        "point of needs_testing is to evaluate it against "
                        "a run."
                    ),
                    card_id=card.id,
                    strategy_id=card.strategy_id,
                )
            )

        if card.status == "draft" and card.created_at < stale_threshold:
            stale_drafts += 1
            age_days = (now - card.created_at).days
            issues.append(
                KnowledgeHealthIssue(
                    code="stale_draft",
                    severity="info",
                    title="Draft card has been sitting",
                    detail=(
                        f"Card #{card.id} \"{card.name}\" has been a draft "
                        f"for {age_days} days. Promote, reject, or archive "
                        "it so it doesn't pollute the memory feed."
                    ),
                    card_id=card.id,
                    strategy_id=card.strategy_id,
                )
            )

    promoted_entries_with_multiple_cards = 0
    for entry in entries:
        card_ids = entry.knowledge_card_ids or []
        if len(card_ids) > 1:
            promoted_entries_with_multiple_cards += 1
            issues.append(
                KnowledgeHealthIssue(
                    code="promoted_entry_with_multiple_cards",
                    severity="info",
                    title="Research entry promoted to multiple cards",
                    detail=(
                        f"Entry #{entry.id} \"{entry.title}\" is linked to "
                        f"{len(card_ids)} knowledge cards "
                        f"({', '.join(f'#{cid}' for cid in card_ids)}). "
                        "Confirm the duplication is intentional."
                    ),
                    research_entry_id=entry.id,
                    strategy_id=entry.strategy_id,
                )
            )

    issues.sort(
        key=lambda i: (
            _SEVERITY_ORDER.get(i.severity, 99),
            i.code,
            i.card_id if i.card_id is not None else 0,
            i.research_entry_id if i.research_entry_id is not None else 0,
        )
    )

    counts = KnowledgeHealthCounts(
        total_cards=len(cards),
        trusted_cards=counts_by_status["trusted"],
        needs_testing_cards=counts_by_status["needs_testing"],
        draft_cards=counts_by_status["draft"],
        rejected_cards=counts_by_status["rejected"],
        archived_cards=counts_by_status["archived"],
        trusted_without_evidence=trusted_without_evidence,
        needs_testing_without_run=needs_testing_without_run,
        stale_drafts=stale_drafts,
        promoted_entries_with_multiple_cards=(
            promoted_entries_with_multiple_cards
        ),
    )
    return KnowledgeHealthRead(
        counts=counts,
        issues=issues,
        generated_at=now,
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
    _validate_evidence_links(
        db=db,
        card_strategy_id=payload.strategy_id,
        linked_run_id=payload.linked_run_id,
        linked_version_id=payload.linked_version_id,
        linked_research_entry_id=payload.linked_research_entry_id,
    )
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
        linked_run_id=payload.linked_run_id,
        linked_version_id=payload.linked_version_id,
        linked_research_entry_id=payload.linked_research_entry_id,
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

    # Compute the post-patch (strategy, run, version, entry) tuple and
    # validate up-front so a stale link can't slip through when the card
    # changes scope. Mirrors how research.update_research_entry
    # revalidates linked_run/version on PATCH.
    link_fields = {
        "linked_run_id",
        "linked_version_id",
        "linked_research_entry_id",
    }
    if "strategy_id" in touched or link_fields & touched:
        next_strategy_id = (
            payload.strategy_id if "strategy_id" in touched else card.strategy_id
        )
        next_run_id = (
            payload.linked_run_id
            if "linked_run_id" in touched
            else card.linked_run_id
        )
        next_version_id = (
            payload.linked_version_id
            if "linked_version_id" in touched
            else card.linked_version_id
        )
        next_entry_id = (
            payload.linked_research_entry_id
            if "linked_research_entry_id" in touched
            else card.linked_research_entry_id
        )
        _validate_evidence_links(
            db=db,
            card_strategy_id=next_strategy_id,
            linked_run_id=next_run_id,
            linked_version_id=next_version_id,
            linked_research_entry_id=next_entry_id,
        )

    if "strategy_id" in touched:
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
    if "linked_run_id" in touched:
        card.linked_run_id = payload.linked_run_id
    if "linked_version_id" in touched:
        card.linked_version_id = payload.linked_version_id
    if "linked_research_entry_id" in touched:
        card.linked_research_entry_id = payload.linked_research_entry_id
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
