"""Tests for the composite query service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory
from app.services.event_composites import (
    find_co_occurring,
    find_thesis_aligned_psp_lookforward,
)
from app.services.research_events import make_event_id

UTC = timezone.utc


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'composites.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


def _evt(
    *,
    feature_name: str,
    event_type: str,
    side: str | None,
    primary: str,
    bar_end: datetime,
) -> models.ResearchEvent:
    return models.ResearchEvent(
        event_id=make_event_id(feature_name, primary, bar_end, event_type),
        feature_name=feature_name,
        event_type=event_type,
        bar_end_utc=bar_end.replace(tzinfo=None) if bar_end.tzinfo else bar_end,
        primary_symbol=primary,
        symbols=["NQ.c.0", "ES.c.0", "YM.c.0"],
        timeframe="4H",
        side=side,
        event_data={"schema_version": 1},
        detector_version="v1",
    )


def _utc(year, month, day, hour=12):
    return datetime(year, month, day, hour, 0, tzinfo=UTC)


def test_find_in_window_basic(session_factory: sessionmaker[Session]):
    anchor_ts = _utc(2026, 5, 4, 12)
    with session_factory() as db:
        anchor = _evt(
            feature_name="smt_htf_reference_divergence",
            event_type="previous_day_smt", side="low",
            primary="NQ.c.0", bar_end=anchor_ts,
        )
        within = _evt(
            feature_name="psp_candle_divergence",
            event_type="4h_psp", side="bullish",
            primary="NQ.c.0", bar_end=anchor_ts + timedelta(hours=2),
        )
        outside = _evt(
            feature_name="psp_candle_divergence",
            event_type="4h_psp", side="bullish",
            primary="ES.c.0", bar_end=anchor_ts + timedelta(hours=10),
        )
        db.add_all([anchor, within, outside])
        db.commit()
        db.refresh(anchor)

        rows = find_co_occurring(
            db, anchor, feature_name="psp_candle_divergence", window_hours=4.0,
        )
        ids = {r.id for r in rows}
        assert within.id in ids
        assert outside.id not in ids


def test_find_after_only(session_factory: sessionmaker[Session]):
    """direction='after' excludes events before the anchor."""
    anchor_ts = _utc(2026, 5, 4, 12)
    with session_factory() as db:
        anchor = _evt(
            feature_name="smt_htf_reference_divergence",
            event_type="previous_day_smt", side="low",
            primary="NQ.c.0", bar_end=anchor_ts,
        )
        before = _evt(
            feature_name="psp_candle_divergence",
            event_type="4h_psp", side="bullish",
            primary="NQ.c.0", bar_end=anchor_ts - timedelta(hours=2),
        )
        after = _evt(
            feature_name="psp_candle_divergence",
            event_type="4h_psp", side="bullish",
            primary="NQ.c.0", bar_end=anchor_ts + timedelta(hours=2),
        )
        db.add_all([anchor, before, after])
        db.commit()
        db.refresh(anchor)

        rows = find_co_occurring(
            db, anchor, feature_name="psp_candle_divergence",
            window_hours=4.0, direction="after",
        )
        ids = [r.id for r in rows]
        assert after.id in ids
        assert before.id not in ids


def test_thesis_alignment_filters(session_factory: sessionmaker[Session]):
    """For a low-side SMT (thesis = up = bullish PSP minority), the
    'thesis' alignment returns only bullish PSPs."""
    anchor_ts = _utc(2026, 5, 4, 12)
    with session_factory() as db:
        anchor = _evt(
            feature_name="smt_htf_reference_divergence",
            event_type="previous_day_smt", side="low",
            primary="NQ.c.0", bar_end=anchor_ts,
        )
        bullish_psp = _evt(
            feature_name="psp_candle_divergence",
            event_type="4h_psp", side="bullish",
            primary="NQ.c.0", bar_end=anchor_ts + timedelta(hours=1),
        )
        bearish_psp = _evt(
            feature_name="psp_candle_divergence",
            event_type="4h_psp", side="bearish",
            primary="NQ.c.0", bar_end=anchor_ts + timedelta(hours=2),
        )
        db.add_all([anchor, bullish_psp, bearish_psp])
        db.commit()
        db.refresh(anchor)

        rows = find_co_occurring(
            db, anchor, feature_name="psp_candle_divergence",
            window_hours=4.0, side_alignment="thesis",
        )
        ids = [r.id for r in rows]
        assert bullish_psp.id in ids
        assert bearish_psp.id not in ids


def test_high_side_smt_thesis_is_bearish(session_factory: sessionmaker[Session]):
    """High-side SMT thesis = expansion DOWN → aligned PSP minority = bearish."""
    anchor_ts = _utc(2026, 5, 4, 12)
    with session_factory() as db:
        anchor = _evt(
            feature_name="smt_htf_reference_divergence",
            event_type="previous_day_smt", side="high",
            primary="NQ.c.0", bar_end=anchor_ts,
        )
        bullish_psp = _evt(
            feature_name="psp_candle_divergence", event_type="4h_psp",
            side="bullish", primary="NQ.c.0",
            bar_end=anchor_ts + timedelta(hours=1),
        )
        bearish_psp = _evt(
            feature_name="psp_candle_divergence", event_type="4h_psp",
            side="bearish", primary="NQ.c.0",
            bar_end=anchor_ts + timedelta(hours=2),
        )
        db.add_all([anchor, bullish_psp, bearish_psp])
        db.commit()
        db.refresh(anchor)

        rows = find_co_occurring(
            db, anchor, feature_name="psp_candle_divergence",
            window_hours=4.0, side_alignment="thesis",
        )
        sides = {r.side for r in rows}
        assert sides == {"bearish"}


def test_thesis_alignment_rejects_bad_anchor(
    session_factory: sessionmaker[Session],
):
    """side_alignment='thesis' requires anchor.side in (high, low)."""
    anchor_ts = _utc(2026, 5, 4, 12)
    with session_factory() as db:
        anchor = _evt(
            feature_name="psp_candle_divergence", event_type="4h_psp",
            side="bullish", primary="NQ.c.0", bar_end=anchor_ts,
        )
        db.add(anchor)
        db.commit()
        db.refresh(anchor)
        with pytest.raises(ValueError, match="thesis"):
            find_co_occurring(
                db, anchor, side_alignment="thesis",
            )


def test_helper_function(session_factory: sessionmaker[Session]):
    """find_thesis_aligned_psp_lookforward applies all the right filters."""
    anchor_ts = _utc(2026, 5, 4, 12)
    with session_factory() as db:
        smt = _evt(
            feature_name="smt_htf_reference_divergence",
            event_type="previous_day_smt", side="low",
            primary="NQ.c.0", bar_end=anchor_ts,
        )
        # before & wrong direction
        before_aligned = _evt(
            feature_name="psp_candle_divergence", event_type="4h_psp",
            side="bullish", primary="NQ.c.0",
            bar_end=anchor_ts - timedelta(hours=1),
        )
        # after & wrong direction (bearish, not thesis-aligned for low SMT)
        after_unaligned = _evt(
            feature_name="psp_candle_divergence", event_type="4h_psp",
            side="bearish", primary="ES.c.0",
            bar_end=anchor_ts + timedelta(hours=1),
        )
        # after & aligned — should be the only hit
        after_aligned = _evt(
            feature_name="psp_candle_divergence", event_type="4h_psp",
            side="bullish", primary="NQ.c.0",
            bar_end=anchor_ts + timedelta(hours=2),
        )
        db.add_all([smt, before_aligned, after_unaligned, after_aligned])
        db.commit()
        db.refresh(smt)

        rows = find_thesis_aligned_psp_lookforward(
            db, smt, psp_event_type="4h_psp", window_hours=4.0,
        )
        ids = [r.id for r in rows]
        assert ids == [after_aligned.id]


def test_helper_rejects_non_smt_anchor(session_factory: sessionmaker[Session]):
    anchor_ts = _utc(2026, 5, 4, 12)
    with session_factory() as db:
        psp = _evt(
            feature_name="psp_candle_divergence", event_type="4h_psp",
            side="bullish", primary="NQ.c.0", bar_end=anchor_ts,
        )
        db.add(psp)
        db.commit()
        db.refresh(psp)
        with pytest.raises(ValueError, match="must be an SMT event"):
            find_thesis_aligned_psp_lookforward(db, psp)
