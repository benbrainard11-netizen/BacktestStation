from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import ResearchEvent
from app.db.session import create_all, make_engine, make_session_factory
from app.research.detectors import get
from app.research.macro_events import MacroEventValidationError, parse_macro_events_csv
from app.research.outcomes import get as get_outcome
from app.research.outcomes.runner import run_outcomes
from app.research.scan import run_scan

UTC = timezone.utc
NQ = "NQ.c.0"


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'macro_event.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


class FakeBarReader:
    def __init__(self) -> None:
        self._frames: dict[tuple[str, str], pd.DataFrame] = {}

    def set(self, *, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        if df.index.tz is None:
            df = df.tz_localize(UTC)
        else:
            df = df.tz_convert(UTC)
        self._frames[(symbol, timeframe)] = df.sort_index()

    def __call__(self, *, symbol, timeframe, start, end, **kw):
        key = (symbol, timeframe)
        if key not in self._frames:
            raise FileNotFoundError(f"no bars for {symbol} {timeframe}")
        df = self._frames[key]
        s = pd.Timestamp(start)
        e = pd.Timestamp(end)
        if s.tz is None:
            s = s.tz_localize(UTC)
        if e.tz is None:
            e = e.tz_localize(UTC)
        return df.loc[(df.index >= s) & (df.index < e)].copy()


def _write_macro_csv(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "event_id,event_name,event_group,country,currency,impact,release_ts_et,actual,forecast,previous,source,notes",
                "2026_05_06_usd_cpi,CPI y/y,cpi,US,USD,high,2026-05-06 08:30:00,3.4%,3.2%,3.1%,forexfactory,test row",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _news_reaction_bars() -> pd.DataFrame:
    rows = []
    cur = datetime(2026, 5, 6, 11, 20, tzinfo=UTC)
    release = datetime(2026, 5, 6, 12, 30, tzinfo=UTC)
    while cur < datetime(2026, 5, 6, 13, 40, tzinfo=UTC):
        if cur < release:
            o, h, low, c = 100.0, 100.2, 99.8, 100.0
        else:
            minutes = int((cur - release).total_seconds() // 60)
            price = 101.0 + minutes * 0.5
            o, h, low, c = price, price + 1.5, 99.9 if minutes == 0 else price - 0.2, price + 1.0
        rows.append({"open": o, "high": h, "low": low, "close": c, "volume": 100})
        cur += timedelta(minutes=1)
    index = pd.date_range(
        datetime(2026, 5, 6, 11, 20, tzinfo=UTC),
        periods=len(rows),
        freq="1min",
    )
    return pd.DataFrame(rows, index=index)


def test_macro_detector_fires_pre_release_anchor_without_actual_leakage(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
):
    csv_path = _write_macro_csv(tmp_path / "macro_events.csv")
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_news_reaction_bars())

    with session_factory() as db:
        result = run_scan(
            detector_name="macro_event_anchor",
            symbols=[NQ],
            start=date(2026, 5, 6),
            end=date(2026, 5, 7),
            bar_reader=reader,
            db=db,
            mode="pre_release",
            params={"events_path": str(csv_path), "currencies": "USD", "impacts": "high"},
        )
        db.commit()
        row = db.scalar(select(ResearchEvent).where(ResearchEvent.feature_name == "macro_event_anchor"))

    assert result.n_errors == 0, result.error_messages
    assert result.n_inserted == 1
    assert row is not None
    assert row.event_type == "pre_cpi"
    assert row.side == "high"
    assert row.bar_end_utc.replace(tzinfo=UTC).isoformat() == "2026-05-06T12:29:00+00:00"
    assert row.event_data["release_ts_utc"] == "2026-05-06T12:30:00+00:00"
    assert row.event_data["forecast_value"] == 3.2
    assert "actual" not in row.event_data
    assert "actual_raw" not in row.event_data
    assert "actual_value" not in row.event_data
    assert row.event_data["pre_15m_range_pts"] > 0


def test_macro_outcome_labels_post_release_reaction(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
):
    csv_path = _write_macro_csv(tmp_path / "macro_events.csv")
    reader = FakeBarReader()
    reader.set(symbol=NQ, timeframe="1m", df=_news_reaction_bars())

    with session_factory() as db:
        scan = run_scan(
            detector_name="macro_event_anchor",
            symbols=[NQ],
            start=date(2026, 5, 6),
            end=date(2026, 5, 7),
            bar_reader=reader,
            db=db,
            mode="pre_release",
            params={"events_path": str(csv_path)},
        )
        assert scan.n_inserted == 1
        result = run_outcomes(
            computer=get_outcome("macro_event_reactions_v1"),
            bar_reader=reader,
            db=db,
            force=True,
        )
        db.commit()
        row = db.scalar(select(ResearchEvent).where(ResearchEvent.feature_name == "macro_event_anchor"))

    assert result.n_errors == 0, result.error_messages
    assert result.n_updated == 1
    assert row is not None
    assert row.outcomes["next_5m"]["direction"] == "up"
    assert row.outcomes["next_5m"]["took_pre_15m_high"] is True
    assert row.outcomes["next_5m"]["range_expanded_2x_pre_15m"] is True


def test_macro_csv_rejects_duplicate_natural_keys(tmp_path: Path):
    path = tmp_path / "macro_events.csv"
    path.write_text(
        "\n".join(
            [
                "event_id,event_name,event_group,country,currency,impact,release_ts_et,actual,forecast,previous,source,notes",
                "a,CPI y/y,cpi,US,USD,high,2026-05-06 08:30:00,,3.2%,3.1%,forexfactory,",
                "b,CPI m/m,cpi,US,USD,high,2026-05-06 08:30:00,,0.2%,0.1%,forexfactory,",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(MacroEventValidationError, match="duplicate release timestamp"):
        parse_macro_events_csv(path)


def test_macro_detector_is_registered():
    d = get("macro_event_anchor")
    assert d.feature_name == "macro_event_anchor"
    assert d.supported_modes == ("pre_release",)
