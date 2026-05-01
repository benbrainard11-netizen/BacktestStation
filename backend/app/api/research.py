"""Per-strategy Research workspace — CRUD over hypotheses, decisions, questions.

The research tab on the strategy workspace is where the user does the
*before-you-build* and *while-you-tune* thinking: hypotheses they want
to test, decisions they made (with reasons), and parked questions. Each
entry can optionally link to a specific backtest run (the run that
tested the hypothesis) or strategy version (the version a decision
changed).

Endpoints:

  GET    /api/strategies/{id}/research            — list (filterable)
  POST   /api/strategies/{id}/research            — create
  GET    /api/strategies/{id}/research/{entry_id} — get one
  PATCH  /api/strategies/{id}/research/{entry_id} — update
  DELETE /api/strategies/{id}/research/{entry_id} — delete
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    Experiment,
    KnowledgeCard,
    ResearchEntry,
    Strategy,
    StrategyVersion,
)
from app.db.session import get_session
from app.schemas import (
    KNOWLEDGE_CARD_KINDS,
    KNOWLEDGE_CARD_STATUSES,
    RESEARCH_KINDS,
    RESEARCH_STATUSES,
    ExperimentRead,
    KnowledgeCardRead,
    ResearchEntryCreate,
    ResearchEntryPromoteRequest,
    ResearchEntryRead,
    ResearchEntryUpdate,
    ResearchExperimentCreate,
)
from app.schemas.research import validate_kind_status_pair


# Default knowledge-card status for each (entry kind, entry status) pair.
# Covers every combination allowed by ALLOWED_STATUSES_BY_KIND in
# app/schemas/research.py. Anything outside this map is a sign the
# research vocabulary changed without updating promote semantics — the
# endpoint 422s defensively rather than silently picking a status.
_PROMOTE_STATUS_BY_ENTRY: dict[tuple[str, str], str] = {
    ("hypothesis", "open"): "needs_testing",
    ("hypothesis", "running"): "needs_testing",
    ("hypothesis", "confirmed"): "trusted",
    ("hypothesis", "rejected"): "rejected",
    ("decision", "done"): "trusted",
    ("question", "open"): "draft",
    ("question", "done"): "trusted",
}

router = APIRouter(
    prefix="/strategies/{strategy_id}/research",
    tags=["research"],
)


def _require_strategy(strategy_id: int, db: Session) -> Strategy:
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=404, detail=f"strategy {strategy_id} not found"
        )
    return strategy


def _require_entry(
    strategy_id: int, entry_id: int, db: Session
) -> ResearchEntry:
    entry = db.get(ResearchEntry, entry_id)
    if entry is None or entry.strategy_id != strategy_id:
        raise HTTPException(
            status_code=404,
            detail=f"research entry {entry_id} not found",
        )
    return entry


def _validate_links(
    *,
    linked_run_id: int | None,
    linked_version_id: int | None,
    db: Session,
    strategy_id: int,
) -> None:
    """If linked_run_id or linked_version_id is set, confirm it exists
    AND belongs to the same strategy. Fails CLOSED if the run's parent
    version can't be resolved (defense in depth — codex 2026-04-30).

    Takes raw ids (not a payload object) so PATCH can call this without
    needing to materialize a full ResearchEntryCreate, which would
    trigger the kind/status validator on default values (codex re-review
    P1 fix)."""
    if linked_version_id is not None:
        version = db.get(StrategyVersion, linked_version_id)
        if version is None or version.strategy_id != strategy_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"linked_version_id {linked_version_id} doesn't "
                    "belong to this strategy"
                ),
            )
    if linked_run_id is not None:
        run = db.get(BacktestRun, linked_run_id)
        if run is None:
            raise HTTPException(
                status_code=422,
                detail=f"linked_run_id {linked_run_id} not found",
            )
        if (
            run.strategy_version is None
            or run.strategy_version.strategy_id != strategy_id
        ):
            run_strategy_id = (
                run.strategy_version.strategy_id
                if run.strategy_version is not None
                else None
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    f"linked_run_id {linked_run_id} belongs to a "
                    f"different strategy ({run_strategy_id})"
                ),
            )


def _clean_knowledge_card_ids(raw: list[int] | None) -> list[int] | None:
    if raw is None:
        return None
    cleaned: list[int] = []
    seen: set[int] = set()
    for card_id in raw:
        if card_id in seen:
            continue
        seen.add(card_id)
        cleaned.append(card_id)
    return cleaned or None


def _validate_knowledge_card_ids(
    *, card_ids: list[int] | None, db: Session, strategy_id: int
) -> list[int] | None:
    """Confirm linked cards exist and are either global or same-strategy."""
    cleaned = _clean_knowledge_card_ids(card_ids)
    if cleaned is None:
        return None
    cards = {
        card.id: card
        for card in db.scalars(
            select(KnowledgeCard).where(KnowledgeCard.id.in_(cleaned))
        ).all()
    }
    missing = [card_id for card_id in cleaned if card_id not in cards]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"knowledge_card_ids not found: {missing}",
        )
    wrong_scope = [
        card.id
        for card in cards.values()
        if card.strategy_id is not None and card.strategy_id != strategy_id
    ]
    if wrong_scope:
        raise HTTPException(
            status_code=422,
            detail=(
                "knowledge_card_ids must be global or belong to this "
                f"strategy; wrong scope: {wrong_scope}"
            ),
        )
    return cleaned


def _pick_experiment_version(
    *,
    db: Session,
    strategy_id: int,
    strategy_version_id: int | None,
) -> StrategyVersion:
    if strategy_version_id is not None:
        version = db.get(StrategyVersion, strategy_version_id)
        if version is None or version.strategy_id != strategy_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"strategy_version_id {strategy_version_id} doesn't "
                    "belong to this strategy"
                ),
            )
        return version

    version = db.scalar(
        select(StrategyVersion)
        .where(
            StrategyVersion.strategy_id == strategy_id,
            StrategyVersion.archived_at.is_(None),
        )
        .order_by(StrategyVersion.id.desc())
        .limit(1)
    )
    if version is None:
        raise HTTPException(
            status_code=422,
            detail="strategy has no active version to attach an experiment to",
        )
    return version


@router.get("", response_model=list[ResearchEntryRead])
def list_research_entries(
    strategy_id: int,
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[ResearchEntry]:
    """List entries for a strategy. Filter optionally by kind / status.

    Sort: newest first (created_at desc, id desc) so fresh hypotheses
    surface immediately.
    """
    _require_strategy(strategy_id, db)

    if kind is not None and kind not in RESEARCH_KINDS:
        raise HTTPException(
            status_code=422,
            detail=f"kind must be one of {RESEARCH_KINDS}, got {kind!r}",
        )
    if status is not None and status not in RESEARCH_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {RESEARCH_STATUSES}, got {status!r}",
        )

    statement = select(ResearchEntry).where(
        ResearchEntry.strategy_id == strategy_id
    )
    if kind is not None:
        statement = statement.where(ResearchEntry.kind == kind)
    if status is not None:
        statement = statement.where(ResearchEntry.status == status)
    statement = statement.order_by(
        ResearchEntry.created_at.desc(), ResearchEntry.id.desc()
    )
    return list(db.scalars(statement).all())


@router.post("", response_model=ResearchEntryRead, status_code=201)
def create_research_entry(
    strategy_id: int,
    payload: ResearchEntryCreate,
    db: Session = Depends(get_session),
) -> ResearchEntry:
    _require_strategy(strategy_id, db)
    _validate_links(
        linked_run_id=payload.linked_run_id,
        linked_version_id=payload.linked_version_id,
        db=db,
        strategy_id=strategy_id,
    )
    knowledge_card_ids = _validate_knowledge_card_ids(
        card_ids=payload.knowledge_card_ids,
        db=db,
        strategy_id=strategy_id,
    )

    entry = ResearchEntry(
        strategy_id=strategy_id,
        kind=payload.kind,
        title=payload.title,
        body=payload.body,
        status=payload.status,
        linked_run_id=payload.linked_run_id,
        linked_version_id=payload.linked_version_id,
        knowledge_card_ids=knowledge_card_ids,
        tags=payload.tags,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{entry_id}", response_model=ResearchEntryRead)
def get_research_entry(
    strategy_id: int, entry_id: int, db: Session = Depends(get_session)
) -> ResearchEntry:
    return _require_entry(strategy_id, entry_id, db)


@router.patch("/{entry_id}", response_model=ResearchEntryRead)
def update_research_entry(
    strategy_id: int,
    entry_id: int,
    payload: ResearchEntryUpdate,
    db: Session = Depends(get_session),
) -> ResearchEntry:
    entry = _require_entry(strategy_id, entry_id, db)

    fields_set = payload.model_fields_set

    # Compute the post-patch (kind, status) pair and validate up-front,
    # so PATCH can't slip through invalid combos like
    # decision=running. Codex re-review 2026-04-30: kind and status
    # update independently; the create-time validator only catches
    # bad pairs in fresh inserts.
    next_kind = payload.kind if "kind" in fields_set and payload.kind else entry.kind
    next_status = (
        payload.status if "status" in fields_set and payload.status else entry.status
    )
    if "kind" in fields_set or "status" in fields_set:
        try:
            validate_kind_status_pair(next_kind, next_status)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    if "kind" in fields_set and payload.kind is not None:
        entry.kind = payload.kind
    if "title" in fields_set and payload.title is not None:
        entry.title = payload.title
    if "body" in fields_set:
        entry.body = payload.body
    if "status" in fields_set and payload.status is not None:
        entry.status = payload.status
    if "linked_run_id" in fields_set or "linked_version_id" in fields_set:
        # Validate the (possibly new) link ids before mutating. Pass
        # raw ids — building a ResearchEntryCreate here would trigger
        # its kind/status post-init validator on default values, which
        # would 422 a decision edit even when status is fine (codex
        # re-review P1 caught this).
        next_run_id = (
            payload.linked_run_id
            if "linked_run_id" in fields_set
            else entry.linked_run_id
        )
        next_version_id = (
            payload.linked_version_id
            if "linked_version_id" in fields_set
            else entry.linked_version_id
        )
        _validate_links(
            linked_run_id=next_run_id,
            linked_version_id=next_version_id,
            db=db,
            strategy_id=strategy_id,
        )
        if "linked_run_id" in fields_set:
            entry.linked_run_id = payload.linked_run_id
        if "linked_version_id" in fields_set:
            entry.linked_version_id = payload.linked_version_id
    if "knowledge_card_ids" in fields_set:
        entry.knowledge_card_ids = _validate_knowledge_card_ids(
            card_ids=payload.knowledge_card_ids,
            db=db,
            strategy_id=strategy_id,
        )
    if "tags" in fields_set:
        entry.tags = payload.tags

    entry.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_research_entry(
    strategy_id: int, entry_id: int, db: Session = Depends(get_session)
) -> None:
    entry = _require_entry(strategy_id, entry_id, db)
    db.delete(entry)
    db.commit()
    return None


@router.post(
    "/{entry_id}/promote",
    response_model=KnowledgeCardRead,
    status_code=201,
)
def promote_research_entry_to_knowledge_card(
    strategy_id: int,
    entry_id: int,
    payload: ResearchEntryPromoteRequest,
    db: Session = Depends(get_session),
) -> KnowledgeCard:
    """Create a knowledge card from a research entry and link them.

    Default status is derived from the entry's (kind, status) so the new
    card honestly reflects how vetted the underlying research is. Tags,
    name, and body fall back to the entry; the payload can override
    each field, but values replace rather than merge. The created card's
    id is appended to entry.knowledge_card_ids; existing links are
    preserved (re-promote is intentional — the UI confirms before
    sending a second request).
    """
    entry = _require_entry(strategy_id, entry_id, db)
    fields_set = payload.model_fields_set

    kind = payload.kind or "research_playbook"
    name = (payload.name or entry.title).strip()
    body = payload.body if "body" in fields_set else entry.body
    tags = payload.tags if "tags" in fields_set else entry.tags
    summary = payload.summary
    formula = payload.formula
    target_strategy_id = (
        payload.strategy_id
        if "strategy_id" in fields_set
        else entry.strategy_id
    )

    if payload.status is not None:
        status = payload.status
    else:
        try:
            status = _PROMOTE_STATUS_BY_ENTRY[(entry.kind, entry.status)]
        except KeyError as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    "no default knowledge-card status for entry "
                    f"kind={entry.kind!r} status={entry.status!r}"
                ),
            ) from exc

    if kind not in KNOWLEDGE_CARD_KINDS:
        raise HTTPException(
            status_code=422,
            detail=f"kind must be one of {KNOWLEDGE_CARD_KINDS}, got {kind!r}",
        )
    if status not in KNOWLEDGE_CARD_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"status must be one of {KNOWLEDGE_CARD_STATUSES}, "
                f"got {status!r}"
            ),
        )

    if target_strategy_id is not None:
        if db.get(Strategy, target_strategy_id) is None:
            raise HTTPException(
                status_code=422,
                detail=f"strategy_id {target_strategy_id} not found",
            )

    card = KnowledgeCard(
        strategy_id=target_strategy_id,
        kind=kind,
        name=name,
        summary=summary,
        body=body,
        formula=formula,
        status=status,
        source=f"research_entry:{entry.id}",
        tags=tags,
    )
    db.add(card)
    db.flush()  # populate card.id without committing the transaction

    existing_ids = list(entry.knowledge_card_ids or [])
    existing_ids.append(card.id)
    entry.knowledge_card_ids = _clean_knowledge_card_ids(existing_ids)
    entry.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()
    db.refresh(card)
    return card


@router.post(
    "/{entry_id}/experiment",
    response_model=ExperimentRead,
    status_code=201,
)
def create_experiment_from_research_entry(
    strategy_id: int,
    entry_id: int,
    payload: ResearchExperimentCreate,
    db: Session = Depends(get_session),
) -> Experiment:
    entry = _require_entry(strategy_id, entry_id, db)
    if entry.kind != "hypothesis":
        raise HTTPException(
            status_code=422,
            detail="only hypothesis research entries can create experiments",
        )
    version = _pick_experiment_version(
        db=db,
        strategy_id=strategy_id,
        strategy_version_id=payload.strategy_version_id,
    )
    if payload.baseline_run_id is not None:
        _validate_links(
            linked_run_id=payload.baseline_run_id,
            linked_version_id=None,
            db=db,
            strategy_id=strategy_id,
        )
    if payload.variant_run_id is not None:
        _validate_links(
            linked_run_id=payload.variant_run_id,
            linked_version_id=None,
            db=db,
            strategy_id=strategy_id,
        )

    notes = payload.notes
    if notes is None and entry.body:
        notes = entry.body
    experiment = Experiment(
        strategy_version_id=version.id,
        hypothesis=entry.title,
        baseline_run_id=payload.baseline_run_id,
        variant_run_id=payload.variant_run_id,
        change_description=payload.change_description,
        decision="pending",
        notes=notes,
    )
    db.add(experiment)
    if entry.status == "open":
        entry.status = "running"
    if entry.linked_version_id is None:
        entry.linked_version_id = version.id
    if entry.linked_run_id is None:
        entry.linked_run_id = payload.variant_run_id or payload.baseline_run_id
    entry.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(experiment)
    return experiment
