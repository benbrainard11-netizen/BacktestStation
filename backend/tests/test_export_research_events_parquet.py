"""Tests for research_events parquet export."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd

from scripts.ml.export_research_events_parquet import export


def _make_db(path: Path) -> None:
    with sqlite3.connect(path) as con:
        con.execute(
            """
            CREATE TABLE research_events (
                id INTEGER PRIMARY KEY,
                event_id TEXT,
                knowledge_card_id TEXT,
                feature_name TEXT,
                event_type TEXT,
                side TEXT,
                primary_symbol TEXT,
                related_symbols TEXT,
                timeframe TEXT,
                bar_start_utc TEXT,
                bar_end_utc TEXT,
                event_data TEXT,
                outcomes TEXT,
                source_run_id TEXT,
                detector_version TEXT,
                created_at TEXT
            )
            """
        )
        con.executemany(
            """
            INSERT INTO research_events VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                (
                    1,
                    "evt1",
                    "kc",
                    "order_block",
                    "swept_pdh_1h",
                    "bullish",
                    "ES.c.0",
                    "[]",
                    "1h",
                    "2025-01-02T00:00:00+00:00",
                    "2025-01-02T01:00:00+00:00",
                    "{}",
                    "{}",
                    "run",
                    "v1",
                    "2025-01-02T01:00:01+00:00",
                ),
                (
                    2,
                    "evt2",
                    "kc",
                    "fvg_formation",
                    "bullish_1h",
                    "bullish",
                    "NQ.c.0",
                    "[]",
                    "1h",
                    "2026-01-02T00:00:00+00:00",
                    "2026-01-02T01:00:00+00:00",
                    "{}",
                    None,
                    "run",
                    "v1",
                    "2026-01-02T01:00:01+00:00",
                ),
            ],
        )


def _make_current_schema_db(path: Path) -> None:
    with sqlite3.connect(path) as con:
        con.execute(
            """
            CREATE TABLE research_events (
                id INTEGER PRIMARY KEY,
                event_id TEXT,
                feature_name TEXT,
                knowledge_card_id TEXT,
                event_type TEXT,
                bar_end_utc TEXT,
                primary_symbol TEXT,
                symbols TEXT,
                timeframe TEXT,
                side TEXT,
                event_data TEXT,
                context TEXT,
                outcomes TEXT,
                replay_pointer TEXT,
                source_dataset TEXT,
                source_run_id TEXT,
                detector_version TEXT,
                created_at TEXT
            )
            """
        )
        con.execute(
            """
            INSERT INTO research_events VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                1,
                "evt-current",
                "liquidity_sweep",
                "kc",
                "sweep_high",
                "2026-01-03T15:30:00+00:00",
                "ES.c.0",
                '["NQ.c.0"]',
                "1m",
                "high",
                '{"level": 100.0}',
                '{"session": "am"}',
                '{"next_60m": true}',
                '{"chart": "ptr"}',
                "local",
                "run",
                "v2",
                "2026-01-03T15:31:00+00:00",
            ),
        )


def test_export_research_events_partitioned_parquet(tmp_path: Path) -> None:
    db = tmp_path / "meta.sqlite"
    out = tmp_path / "research_events"
    manifest_path = out / "manifest.json"
    _make_db(db)

    manifest = export(
        argparse.Namespace(
            db=db,
            output=out,
            manifest=manifest_path,
            chunk_size=1,
            force=True,
        )
    )

    assert manifest["rows"] == 2
    assert manifest["files"] == 2
    assert manifest_path.exists()
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["by_feature"] == {"fvg_formation": 1, "order_block": 1}

    files = sorted(out.rglob("*.parquet"))
    assert len(files) == 2
    df = pd.concat(pd.read_parquet(path) for path in files)
    assert sorted(df["event_id"].tolist()) == ["evt1", "evt2"]


def test_export_research_events_accepts_current_schema(tmp_path: Path) -> None:
    db = tmp_path / "meta.sqlite"
    out = tmp_path / "research_events"
    manifest_path = out / "manifest.json"
    _make_current_schema_db(db)

    manifest = export(
        argparse.Namespace(
            db=db,
            output=out,
            manifest=manifest_path,
            chunk_size=10,
            force=True,
        )
    )

    assert manifest["rows"] == 1
    assert manifest["by_feature"] == {"liquidity_sweep": 1}
    df = pd.read_parquet(next(out.rglob("*.parquet")))
    row = df.iloc[0]
    assert row["symbols"] == '["NQ.c.0"]'
    assert row["related_symbols"] == '["NQ.c.0"]'
    assert pd.isna(row["bar_start_utc"])
    assert row["context"] == '{"session": "am"}'
    assert row["source_dataset"] == "local"
