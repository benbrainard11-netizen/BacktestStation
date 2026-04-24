"""Pydantic schemas for the AI Prompt Generator.

The Prompt Generator bundles strategy context (versions, recent notes,
recent experiments, latest run + metrics, latest autopsy) into a
single markdown blob the user copies into Claude or GPT externally.
There is no LLM call from inside the app — model-agnostic by design.

Mode selects a system-style preamble (researcher / critic / etc.) and
controls which sections the bundler emphasizes. Vocabulary surfaced
at GET /api/prompts/modes, mirroring STRATEGY_STAGES / NOTE_TYPES /
EXPERIMENT_DECISIONS.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROMPT_MODES: tuple[str, ...] = (
    "researcher",
    "critic",
    "statistician",
    "risk_manager",
    "engineer",
    "live_monitor",
)


class PromptModesRead(BaseModel):
    """GET /api/prompts/modes body."""

    modes: list[str] = Field(default_factory=lambda: list(PROMPT_MODES))


class PromptGenerateRequest(BaseModel):
    """POST /api/prompts/generate body."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: int
    mode: str = Field(default="researcher")
    focus_question: str | None = None

    @field_validator("mode", mode="after")
    @classmethod
    def _valid_mode(cls, value: str) -> str:
        if value not in PROMPT_MODES:
            raise ValueError(
                f"mode must be one of {PROMPT_MODES}, got {value!r}"
            )
        return value

    @field_validator("focus_question", mode="after")
    @classmethod
    def _trim_focus(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class PromptGenerateResponse(BaseModel):
    """POST /api/prompts/generate response.

    `prompt_text` is the full markdown blob ready to paste.
    `bundled_context_summary` lists which sections were included so the
    UI can show the user what got packaged (e.g., "3 versions, 12 notes,
    2 experiments, latest run, autopsy"). It's diagnostic, not load-bearing.
    """

    prompt_text: str
    mode: str
    strategy_id: int
    bundled_context_summary: list[str]
    char_count: int
