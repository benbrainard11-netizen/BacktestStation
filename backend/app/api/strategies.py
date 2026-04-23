"""Strategy read endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Strategy
from app.db.session import get_session
from app.schemas import StrategyRead

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyRead])
def list_strategies(db: Session = Depends(get_session)) -> list[Strategy]:
    statement = (
        select(Strategy)
        .options(selectinload(Strategy.versions))
        .order_by(Strategy.created_at.desc(), Strategy.id.desc())
    )
    return list(db.scalars(statement).all())


@router.get("/{strategy_id}", response_model=StrategyRead)
def get_strategy(strategy_id: int, db: Session = Depends(get_session)) -> Strategy:
    statement = (
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .options(selectinload(Strategy.versions))
    )
    strategy = db.scalars(statement).first()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy
