"""Middle-third opening-range MBP/event-level execution study."""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from app.core.paths import warehouse_root
from app.research.nq_liquidity_sweep_outcomes_sessions import et_datetime, normalize_mbp1
from app.research.nq_opening_range_mbp_execution_fills import simulate_entry_style
from app.research.nq_opening_range_mbp_execution_sequence import build_mbp_event
from app.research.nq_opening_range_mbp_execution_stats import (
    json_safe,
    monthly_summary,
    outcome_summary,
    stability_summary,
    study_summary,
    variant_summary,
    walk_forward_summary,
)
from app.research.nq_opening_range_mbp_execution_types import (
    ENTRY_STYLES,
    OpeningRangeMbpExecutionConfig,
)

MBP_COLUMNS = ["ts_event", "action", "price", "bid_px", "ask_px", "sequence"]


def run_opening_range_mbp_execution_study(
    *,
    events_path: Path,
    config: OpeningRangeMbpExecutionConfig | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, object]:
    cfg = config or OpeningRangeMbpExecutionConfig()
    source_events = load_middle_third_events(events_path, cfg, start=start, end=end)
    loader = MbpWindowLoader(cfg.symbol)
    mbp_events: list[dict[str, object]] = []
    attempts: list[dict[str, object]] = []
    for event in source_events.itertuples(index=False):
        event_series = pd.Series(event._asdict())
        mbp1 = loader.load_rth_window(str(event_series["session_date"]))
        mbp_event = build_mbp_event(event_series, mbp1)
        mbp_events.append(mbp_event)
        mbp_event_series = pd.Series(mbp_event)
        for entry_style in ENTRY_STYLES:
            attempts.append(simulate_entry_style(mbp_event_series, mbp1, entry_style, cfg))
    events = pd.DataFrame(mbp_events)
    attempts_df = pd.DataFrame(attempts)
    trades = attempts_df.loc[attempts_df["status"] == "filled"].copy()
    outcomes = outcome_summary(events)
    variants = variant_summary(attempts_df)
    monthly = monthly_summary(attempts_df)
    walk = walk_forward_summary(attempts_df, cfg)
    stability = stability_summary(variants, walk)
    return {
        "source_events": source_events,
        "mbp_events": events,
        "attempts": attempts_df,
        "trades": trades,
        "outcome_summary": outcomes,
        "variant_summary": variants,
        "monthly_summary": monthly,
        "walk_forward": walk,
        "stability_summary": stability,
        "summary": study_summary(events, attempts_df, outcomes, stability, cfg),
        "config": asdict(cfg),
    }


def write_opening_range_mbp_execution_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "source_events": "or_middle_third_source_events.csv",
        "mbp_events": "or_middle_third_mbp_events.csv",
        "attempts": "or_middle_third_mbp_attempts.csv",
        "trades": "or_middle_third_mbp_trades.csv",
        "outcome_summary": "or_middle_third_mbp_outcomes.csv",
        "variant_summary": "or_middle_third_mbp_variant_summary.csv",
        "monthly_summary": "or_middle_third_mbp_monthly.csv",
        "walk_forward": "or_middle_third_mbp_walk_forward.csv",
        "stability_summary": "or_middle_third_mbp_stability.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "or_middle_third_mbp_summary.json").write_text(
        json.dumps(json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )
    (output_dir / "or_middle_third_mbp_config.json").write_text(
        json.dumps(json_safe(result["config"]), indent=2),
        encoding="utf-8",
    )


def load_middle_third_events(
    events_path: Path,
    config: OpeningRangeMbpExecutionConfig,
    *,
    start: str | None,
    end: str | None,
) -> pd.DataFrame:
    df = pd.read_csv(events_path)
    df = df.loc[df["opening_drive_close_bucket"] == config.context_bucket].copy()
    dates = pd.to_datetime(df["session_date"])
    if start is not None:
        df = df.loc[dates >= pd.Timestamp(start)].copy()
        dates = pd.to_datetime(df["session_date"])
    if end is not None:
        df = df.loc[dates < pd.Timestamp(end)].copy()
    df["is_holdout"] = pd.to_datetime(df["session_date"]) >= pd.Timestamp(config.holdout_start)
    df["month"] = pd.to_datetime(df["session_date"]).dt.to_period("M").astype(str)
    return df.sort_values("session_date").reset_index(drop=True)


class MbpWindowLoader:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.backend = os.environ.get("BS_DATA_BACKEND", "local").lower()
        self.fs = self._filesystem()

    def load_rth_window(self, session_date: str) -> pd.DataFrame:
        date_value = dt.date.fromisoformat(session_date)
        start = et_datetime(date_value, dt.time(10, 0))
        end = et_datetime(date_value, dt.time(16, 0))
        return self.load_window(date_value, start, end)

    def load_window(
        self,
        date_value: dt.date,
        start: dt.datetime,
        end: dt.datetime,
    ) -> pd.DataFrame:
        table = self._read_window(date_value, start, end)
        if table.num_rows == 0:
            return empty_mbp_frame()
        return normalize_mbp1(table.to_pandas())

    def _read_window(
        self,
        date_value: dt.date,
        start: dt.datetime,
        end: dt.datetime,
    ) -> pa.Table:
        path = self._partition_path(date_value)
        if path is None:
            return empty_table()
        dataset = ds.dataset([path], filesystem=self.fs, format="parquet")
        ts_type = pa.timestamp("ns", tz="UTC")
        filtered = dataset.to_table(
            columns=MBP_COLUMNS,
            filter=(
                (ds.field("ts_event") >= pa.scalar(start, type=ts_type))
                & (ds.field("ts_event") < pa.scalar(end, type=ts_type))
            ),
        )
        return filtered

    def _partition_path(self, date_value: dt.date) -> str | Path | None:
        key = (
            f"raw/databento/mbp-1/symbol={self.symbol}/"
            f"date={date_value.isoformat()}/part-000.parquet"
        )
        if self.backend == "r2":
            bucket = os.environ.get("BS_R2_BUCKET", "bsdata-prod")
            path = f"{bucket}/{key}"
            from pyarrow.fs import FileType

            return path if self.fs.get_file_info(path).type == FileType.File else None
        path = warehouse_root() / key
        return path if path.exists() else None

    def _filesystem(self):
        if self.backend != "r2":
            return None
        from pyarrow.fs import S3FileSystem

        endpoint = os.environ["BS_R2_ENDPOINT"].removeprefix("https://")
        endpoint = endpoint.removeprefix("http://").rstrip("/")
        return S3FileSystem(
            access_key=os.environ["BS_R2_ACCESS_KEY"],
            secret_key=os.environ["BS_R2_SECRET"],
            endpoint_override=endpoint,
            scheme="https",
        )


def empty_table() -> pa.Table:
    return pa.table({col: [] for col in MBP_COLUMNS})


def empty_mbp_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=MBP_COLUMNS).set_index(pd.DatetimeIndex([], tz="UTC"))
