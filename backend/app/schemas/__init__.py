"""Pydantic schemas.

After the backend-only refactor (2026-06-08) the web API was removed, so the
former request/response schemas are gone. Only the research-event schema
remains -- the research detectors emit ``ResearchEventCreate``.
"""

from app.schemas.research_events import ResearchEventCreate

__all__ = ["ResearchEventCreate"]
