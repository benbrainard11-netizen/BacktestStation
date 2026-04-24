"""AI Prompt Generator endpoints.

Bundles strategy context into a copyable markdown prompt for the user
to paste into Claude or GPT externally. No LLM calls from inside the
app — model-agnostic by design.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Strategy
from app.db.session import get_session
from app.schemas import (
    PromptGenerateRequest,
    PromptGenerateResponse,
    PromptModesRead,
)
from app.schemas.prompts import PROMPT_MODES
from app.services import prompt_generator

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("/modes", response_model=PromptModesRead)
def list_modes() -> dict:
    """Vocabulary endpoint for the mode picker. Mirrors STRATEGY_STAGES."""
    return {"modes": list(PROMPT_MODES)}


@router.post("/generate", response_model=PromptGenerateResponse)
def generate_prompt(
    payload: PromptGenerateRequest,
    db: Session = Depends(get_session),
) -> PromptGenerateResponse:
    statement = (
        select(Strategy)
        .where(Strategy.id == payload.strategy_id)
        .options(selectinload(Strategy.versions))
    )
    strategy = db.scalars(statement).first()
    if strategy is None:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy {payload.strategy_id} not found",
        )

    bundle = prompt_generator.build_prompt(
        db=db,
        strategy=strategy,
        mode=payload.mode,
        focus_question=payload.focus_question,
    )
    return PromptGenerateResponse(
        prompt_text=bundle.text,
        mode=payload.mode,
        strategy_id=strategy.id,
        bundled_context_summary=bundle.summary,
        char_count=len(bundle.text),
    )
