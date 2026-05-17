"""Build active SMT state timelines and as-of SMT-state context.

The timeline turns discrete SMT events into time intervals:

  - HTF reference SMT:
      forming   = first divergent break known -> period close or invalidation
      confirmed = period close -> next period TTL, if divergence survived close

  - Previous-candle MTF SMT:
      confirmed = candle close -> N tracking candles later

The generated `smtstate.*` context columns are joined to anchor snapshot rows
using `asof.feature_cutoff_ts`, so a row only sees SMT state that was active at
that timestamp.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from snapshot_feature_registry import SMT_LAG_MIN, SMT_MTF_LAG_MIN  # noqa: E402

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DB_PATH = ROOT / "data" / "meta.sqlite"
FEATURES_DIR = ROOT / "data" / "ml" / "features"
SMT_FEATURES_PATH = FEATURES_DIR / "smt.parquet"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CONTEXT_DIR = ROOT / "data" / "ml" / "context"
DOC_PATH = ROOT / "docs" / "ML_SMT_STATE_TIMELINE.md"
TIMELINE_PARQUET = CONTEXT_DIR / "smt_state_timeline.parquet"
TIMELINE_CSV = CONTEXT_DIR / "smt_state_timeline.csv"
SUMMARY_PARQUET = CONTEXT_DIR / "smt_state_context_summary.parquet"
SUMMARY_CSV = CONTEXT_DIR / "smt_state_context_summary.csv"

NS_PER_MIN = 60 * 1_000_000_000

HTF_CONFIRMED_TTL_MIN = {
    "previous_day_smt": 24 * 60,
    "weekly_smt": 7 * 24 * 60,
}

TF_MINUTES = {
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "90m": 90,
    "4h": 4 * 60,
    "6h": 6 * 60,
    "1d": 24 * 60,
    "weekly": 7 * 24 * 60,
}


@dataclass(frozen=True, slots=True)
class AnchorTarget:
    short_name: str
    matrix_path: Path
    schema_path: Path
    output_path: Path
    output_schema_path: Path
    context_path: Path


ANCHOR_TARGETS: dict[str, AnchorTarget] = {
    "disp": AnchorTarget(
        "disp",
        ANCHORS_DIR / "disp_snapshots.parquet",
        ANCHORS_DIR / "disp_snapshots.schema.json",
        ANCHORS_DIR / "disp_snapshots_smtstate.parquet",
        ANCHORS_DIR / "disp_snapshots_smtstate.schema.json",
        CONTEXT_DIR / "disp_smt_state_context.parquet",
    ),
    "psp": AnchorTarget(
        "psp",
        ANCHORS_DIR / "psp_snapshots.parquet",
        ANCHORS_DIR / "psp_snapshots.schema.json",
        ANCHORS_DIR / "psp_snapshots_smtstate.parquet",
        ANCHORS_DIR / "psp_snapshots_smtstate.schema.json",
        CONTEXT_DIR / "psp_smt_state_context.parquet",
    ),
    "fvg": AnchorTarget(
        "fvg",
        ANCHORS_DIR / "fvg_snapshots.parquet",
        ANCHORS_DIR / "fvg_snapshots.schema.json",
        ANCHORS_DIR / "fvg_snapshots_smtstate.parquet",
        ANCHORS_DIR / "fvg_snapshots_smtstate.schema.json",
        CONTEXT_DIR / "fvg_smt_state_context.parquet",
    ),
    "sweep": AnchorTarget(
        "sweep",
        ANCHORS_DIR / "sweep_snapshots.parquet",
        ANCHORS_DIR / "sweep_snapshots.schema.json",
        ANCHORS_DIR / "sweep_snapshots_smtstate.parquet",
        ANCHORS_DIR / "sweep_snapshots_smtstate.schema.json",
        CONTEXT_DIR / "sweep_smt_state_context.parquet",
    ),
    "ob": AnchorTarget(
        "ob",
        ANCHORS_DIR / "ob_snapshots.parquet",
        ANCHORS_DIR / "ob_snapshots.schema.json",
        ANCHORS_DIR / "ob_snapshots_smtstate.parquet",
        ANCHORS_DIR / "ob_snapshots_smtstate.schema.json",
        CONTEXT_DIR / "ob_smt_state_context.parquet",
    ),
}


def _parse_csv_arg(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _safe_json(value: Any, fallback: Any) -> Any:
    if value is None or value == "" or value == "null":
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return fallback
    return parsed


def _to_utc(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).tz_convert("UTC") if pd.Timestamp(value).tzinfo else pd.Timestamp(value, tz="UTC")


def _maybe_ts(value: Any) -> pd.Timestamp | None:
    if value is None or value == "" or pd.isna(value):
        return None
    try:
        return pd.to_datetime(value, utc=True)
    except (TypeError, ValueError):
        return None


def _safe_name(value: Any) -> str:
    text = str(value).strip().lower()
    for old, new in [(" ", "_"), (".", "_"), ("-", "_"), ("/", "_"), ("+", "plus")]:
        text = text.replace(old, new)
    return "".join(ch for ch in text if ch.isalnum() or ch == "_").strip("_")


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes"}:
            return True
        if text in {"0", "false", "no"}:
            return False
    return bool(value)


def _direction_from_side(side: Any) -> str | None:
    text = str(side).strip().lower()
    if text in {"low", "bullish", "up", "long"}:
        return "up"
    if text in {"high", "bearish", "down", "short"}:
        return "down"
    return None


def _tf_from_mtf_event_type(event_type: str) -> str | None:
    match = re.match(r"^(15m|30m|1h|90m|4h|6h)_prev_candle_smt_(high|low)$", event_type)
    return match.group(1) if match else None


def _load_smt_events(db_path: Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql_query(
            """
            SELECT id AS event_id, feature_name, event_type, side, primary_symbol,
                   symbols, bar_end_utc, event_data, outcomes, context
            FROM research_events
            WHERE feature_name IN (
                'smt_htf_reference_divergence',
                'smt_prev_candle_divergence'
            )
            ORDER BY bar_end_utc, id
            """,
            con,
        )
    if df.empty:
        return df
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    return df


def _load_smt_feature_events(path: Path) -> pd.DataFrame:
    """Load HTF SMT rows from the phase-1 feature matrix.

    This keeps the state timeline aligned with the feature artifacts even when
    local SQLite is not carrying every asset universe row yet.
    """
    df = pd.read_parquet(path)
    if df.empty:
        return pd.DataFrame()

    symbol_cols = sorted(
        {
            match.group(1)
            for col in df.columns
            if (match := re.match(r"^ed\.symbol_states\.(.+)\.reference_high$", col))
        }
    )
    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        side = str(row.get("side"))
        symbols = [
            symbol
            for symbol in symbol_cols
            if pd.notna(row.get(f"ed.symbol_states.{symbol}.reference_high"))
            or pd.notna(row.get(f"ed.symbol_states.{symbol}.reference_low"))
        ]
        if not symbols:
            symbols = [row.get("primary_symbol")]

        first_break_time = row.get("ed.first_break_time_utc") or row.get("bar_end_utc")
        first_break_symbol = row.get("ed.first_break_symbol") or row.get("primary_symbol")
        break_field = "high_break_time_utc" if side == "high" else "low_break_time_utc"
        break_times = {
            symbol: _maybe_ts(row.get(f"ed.symbol_states.{symbol}.{break_field}"))
            for symbol in symbols
        }
        first_break_ts = _maybe_ts(first_break_time)
        confirming = [
            symbol
            for symbol, ts in break_times.items()
            if symbol != first_break_symbol and ts is not None and first_break_ts is not None and ts == first_break_ts
        ]
        lagging = [
            symbol
            for symbol, ts in break_times.items()
            if ts is None or (first_break_ts is not None and ts > first_break_ts)
        ]
        did_all_confirm = _as_bool(row.get("ed.did_all_confirm_by_window_end"))
        all_confirmed_time = None
        if did_all_confirm and break_times and all(ts is not None for ts in break_times.values()):
            all_confirmed_time = max(ts for ts in break_times.values() if ts is not None)

        event_data = {
            "reference_type": row.get("ed.reference_type"),
            "first_break_symbol": first_break_symbol,
            "first_break_time_utc": str(first_break_time),
            "lagging_symbols_at_break": lagging,
            "confirming_symbols_at_break": confirming,
            "later_confirmations": [],
            "all_confirmed_time_utc": all_confirmed_time.isoformat() if all_confirmed_time is not None else None,
            "did_all_confirm_by_window_end": did_all_confirm,
        }
        outcomes = {
            "period_close": {
                "smt_active_for_side_at_close": _as_bool(
                    row.get("oc.period_close.smt_active_for_side_at_close")
                )
            }
        }
        context = {
            "current_period_start_utc": row.get("ctx.current_period_start_utc"),
            "current_period_end_utc": row.get("ctx.current_period_end_utc"),
        }
        records.append(
            {
                "event_id": int(row["event_id"]),
                "feature_name": "smt_htf_reference_divergence",
                "event_type": row["event_type"],
                "side": side,
                "primary_symbol": row["primary_symbol"],
                "symbols": symbols,
                "bar_end_utc": row["bar_end_utc"],
                "event_data": event_data,
                "outcomes": outcomes,
                "context": context,
            }
        )

    out = pd.DataFrame(records)
    out["bar_end_utc"] = pd.to_datetime(out["bar_end_utc"], utc=True)
    return out


def build_timeline(
    events: pd.DataFrame,
    *,
    include_mtf: bool = False,
    mtf_ttl_periods: int = 4,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in events.itertuples(index=False):
        ed = _safe_json(row.event_data, {})
        oc = _safe_json(row.outcomes, {})
        ctx = _safe_json(row.context, {})
        symbols = _safe_json(row.symbols, [])
        if not isinstance(symbols, list) or not symbols:
            symbols = [row.primary_symbol]

        if row.feature_name == "smt_htf_reference_divergence":
            rows.extend(_htf_state_rows(row, ed=ed, oc=oc, ctx=ctx, symbols=symbols))
        elif include_mtf and row.feature_name == "smt_prev_candle_divergence":
            rows.extend(_mtf_state_rows(row, ed=ed, symbols=symbols, mtf_ttl_periods=mtf_ttl_periods))

    timeline = pd.DataFrame(rows)
    if timeline.empty:
        return timeline
    timeline["state_start_ts"] = pd.to_datetime(timeline["state_start_ts"], utc=True)
    timeline["state_end_ts"] = pd.to_datetime(timeline["state_end_ts"], utc=True)
    for col in ("trigger_ts", "period_start_ts", "period_end_ts", "invalidated_ts"):
        timeline[col] = pd.to_datetime(timeline[col], utc=True, errors="coerce")
    timeline["state_duration_min"] = (
        timeline["state_end_ts"] - timeline["state_start_ts"]
    ).dt.total_seconds() / 60.0
    timeline = timeline[timeline["state_duration_min"] > 0].copy()
    timeline = timeline.sort_values(
        ["state_start_ts", "source_event_id", "stage", "member_symbol"]
    ).reset_index(drop=True)
    timeline["state_row_id"] = np.arange(1, len(timeline) + 1, dtype=np.int64)
    return timeline


def _htf_state_rows(row: Any, *, ed: dict[str, Any], oc: dict[str, Any], ctx: dict[str, Any], symbols: list[str]) -> list[dict[str, Any]]:
    event_type = str(row.event_type)
    lag_min = int(SMT_LAG_MIN.get(event_type, 0))
    trigger_raw = _maybe_ts(ed.get("first_break_time_utc")) or row.bar_end_utc
    trigger_known_ts = row.bar_end_utc + pd.Timedelta(minutes=lag_min)
    period_start = _maybe_ts(ctx.get("current_period_start_utc"))
    period_end = _maybe_ts(ctx.get("current_period_end_utc"))
    if period_end is None:
        return []

    later_confirmations = ed.get("later_confirmations") or []
    invalidated_ts = None
    if _as_bool(ed.get("did_all_confirm_by_window_end")) and isinstance(later_confirmations, list):
        confirm_times = [
            _maybe_ts(item.get("confirm_time_utc"))
            for item in later_confirmations
            if isinstance(item, dict)
        ]
        if ed.get("all_confirmed_time_utc"):
            confirm_times.append(_maybe_ts(ed.get("all_confirmed_time_utc")))
        confirm_times = [ts for ts in confirm_times if ts is not None]
        if confirm_times:
            invalidated_ts = max(confirm_times) + pd.Timedelta(minutes=lag_min)

    active_at_close = _period_close_active(oc)
    if active_at_close is None:
        active_at_close = invalidated_ts is None or invalidated_ts >= period_end

    forming_end = min(period_end, invalidated_ts) if invalidated_ts is not None else period_end
    rows: list[dict[str, Any]] = []
    if trigger_known_ts < forming_end:
        rows.extend(
            _explode_state_members(
                row,
                ed=ed,
                symbols=symbols,
                source_scope="htf_reference",
                stage="forming",
                state_timeframe=event_type.replace("_smt", ""),
                state_tf_min=_htf_state_tf_min(event_type),
                reference_type=ed.get("reference_type"),
                state_start_ts=trigger_known_ts,
                state_end_ts=forming_end,
                trigger_ts=trigger_raw,
                period_start_ts=period_start,
                period_end_ts=period_end,
                invalidated_ts=invalidated_ts,
                survived_to_period_close=bool(active_at_close),
                close_confirmed_at_close=None,
            )
        )

    if bool(active_at_close):
        confirmed_start = period_end
        confirmed_end = confirmed_start + pd.Timedelta(
            minutes=HTF_CONFIRMED_TTL_MIN.get(event_type, 24 * 60)
        )
        rows.extend(
            _explode_state_members(
                row,
                ed=ed,
                symbols=symbols,
                source_scope="htf_reference",
                stage="confirmed",
                state_timeframe=event_type.replace("_smt", ""),
                state_tf_min=_htf_state_tf_min(event_type),
                reference_type=ed.get("reference_type"),
                state_start_ts=confirmed_start,
                state_end_ts=confirmed_end,
                trigger_ts=trigger_raw,
                period_start_ts=period_start,
                period_end_ts=period_end,
                invalidated_ts=invalidated_ts,
                survived_to_period_close=True,
                close_confirmed_at_close=None,
            )
        )
    return rows


def _mtf_state_rows(row: Any, *, ed: dict[str, Any], symbols: list[str], mtf_ttl_periods: int) -> list[dict[str, Any]]:
    event_type = str(row.event_type)
    tf = str(ed.get("tracking_timeframe") or _tf_from_mtf_event_type(event_type) or "")
    tf_min = int(TF_MINUTES.get(tf, 0))
    if tf_min <= 0:
        return []
    lag_min = int(SMT_MTF_LAG_MIN.get(event_type, 0))
    start = row.bar_end_utc + pd.Timedelta(minutes=lag_min)
    end = start + pd.Timedelta(minutes=tf_min * mtf_ttl_periods)
    return _explode_state_members(
        row,
        ed=ed,
        symbols=symbols,
        source_scope="mtf_previous_candle",
        stage="confirmed",
        state_timeframe=tf,
        state_tf_min=tf_min,
        reference_type="previous_candle",
        state_start_ts=start,
        state_end_ts=end,
        trigger_ts=row.bar_end_utc,
        period_start_ts=_maybe_ts(ed.get("current_candle_start_utc")),
        period_end_ts=row.bar_end_utc,
        invalidated_ts=None,
        survived_to_period_close=True,
        close_confirmed_at_close=_as_bool(ed.get("close_confirmed_at_close")),
    )


def _period_close_active(outcomes: dict[str, Any]) -> bool | None:
    period_close = outcomes.get("period_close")
    if not isinstance(period_close, dict):
        return None
    value = period_close.get("smt_active_for_side_at_close")
    if value is None:
        return None
    return bool(value)


def _htf_state_tf_min(event_type: str) -> int:
    if event_type == "weekly_smt":
        return 7 * 24 * 60
    if event_type == "previous_day_smt":
        return 24 * 60
    return 0


def _explode_state_members(
    row: Any,
    *,
    ed: dict[str, Any],
    symbols: list[str],
    source_scope: str,
    stage: str,
    state_timeframe: str,
    state_tf_min: int,
    reference_type: Any,
    state_start_ts: pd.Timestamp,
    state_end_ts: pd.Timestamp,
    trigger_ts: pd.Timestamp | None,
    period_start_ts: pd.Timestamp | None,
    period_end_ts: pd.Timestamp | None,
    invalidated_ts: pd.Timestamp | None,
    survived_to_period_close: bool,
    close_confirmed_at_close: bool | None,
) -> list[dict[str, Any]]:
    side = str(row.side)
    thesis_direction = "down" if side == "high" else "up" if side == "low" else _direction_from_side(side)
    swept = set(ed.get("swept_symbols") or [])
    lagging = set(ed.get("lagging_symbols_at_break") or [])
    confirming = set(ed.get("confirming_symbols_at_break") or [])
    first_break = ed.get("first_break_symbol") or ed.get("primary_sweep_symbol") or row.primary_symbol
    n_symbols = len(symbols)
    n_swept = int(ed.get("n_swept_symbols") or len(swept) or (1 + len(confirming)))
    n_holding = int(ed.get("n_holding_symbols") or len(lagging) or max(n_symbols - n_swept, 0))

    rows: list[dict[str, Any]] = []
    for member in sorted(set(str(s) for s in symbols if s)):
        if member == first_break:
            role = "primary_breaker"
        elif member in confirming or member in swept:
            role = "co_breaker"
        elif member in lagging:
            role = "lagging_at_trigger"
        else:
            role = "member"
        rows.append(
            {
                "source_event_id": int(row.event_id),
                "source_feature_name": row.feature_name,
                "source_scope": source_scope,
                "source_event_type": row.event_type,
                "stage": stage,
                "side": side,
                "thesis_direction": thesis_direction,
                "state_timeframe": state_timeframe,
                "state_tf_min": int(state_tf_min),
                "reference_type": reference_type,
                "primary_symbol": row.primary_symbol,
                "member_symbol": member,
                "member_role": role,
                "state_start_ts": state_start_ts,
                "state_end_ts": state_end_ts,
                "trigger_ts": trigger_ts,
                "period_start_ts": period_start_ts,
                "period_end_ts": period_end_ts,
                "invalidated_ts": invalidated_ts,
                "survived_to_period_close": bool(survived_to_period_close),
                "close_confirmed_at_close": close_confirmed_at_close,
                "n_symbols": n_symbols,
                "n_swept_symbols": n_swept,
                "n_holding_symbols": n_holding,
            }
        )
    return rows


def build_state_context(anchors: pd.DataFrame, timeline: pd.DataFrame) -> pd.DataFrame:
    required = ["anchor.event_id", "asof.snapshot", "asof.feature_cutoff_ts", "anchor.primary_symbol", "anchor.side"]
    missing = [col for col in required if col not in anchors.columns]
    if missing:
        raise KeyError(f"anchor matrix missing required columns: {missing}")

    cutoff = pd.to_datetime(anchors["asof.feature_cutoff_ts"], utc=True)
    cutoff_ns = cutoff.to_numpy("datetime64[ns]").astype("int64")
    primary = anchors["anchor.primary_symbol"].astype(str).to_numpy()
    anchor_direction = anchors["anchor.side"].map(_direction_from_side).to_numpy()

    data: dict[str, Any] = {
        "anchor.event_id": anchors["anchor.event_id"].to_numpy(),
        "asof.snapshot": anchors["asof.snapshot"].to_numpy(),
    }

    counts_total, age_total = _active_counts_and_age(cutoff_ns, primary, timeline)
    data["smtstate.n_active_total"] = counts_total
    data["smtstate.has_active_total"] = counts_total > 0
    data["smtstate.minutes_since_latest_active_start"] = age_total

    for stage in ("forming", "confirmed"):
        counts, age = _active_counts_and_age(cutoff_ns, primary, timeline[timeline["stage"].eq(stage)])
        data[f"smtstate.n_active_{stage}"] = counts
        data[f"smtstate.has_active_{stage}"] = counts > 0
        data[f"smtstate.minutes_since_latest_{stage}_start"] = age

    for scope in ("htf_reference", "mtf_previous_candle"):
        counts, _age = _active_counts_and_age(cutoff_ns, primary, timeline[timeline["source_scope"].eq(scope)])
        data[f"smtstate.n_active_{_safe_name(scope)}"] = counts
        data[f"smtstate.has_active_{_safe_name(scope)}"] = counts > 0

    for direction in ("up", "down"):
        counts, age = _active_counts_and_age(
            cutoff_ns,
            primary,
            timeline[timeline["thesis_direction"].eq(direction)],
        )
        mask = anchor_direction == direction
        data[f"smtstate.n_active_{direction}_thesis"] = counts
        data[f"smtstate.has_active_{direction}_thesis"] = counts > 0
        data[f"smtstate.n_active_aligned_if_{direction}"] = np.where(mask, counts, 0)
        data[f"smtstate.minutes_since_latest_{direction}_thesis_start"] = age

    up_counts = np.asarray(data["smtstate.n_active_up_thesis"])
    down_counts = np.asarray(data["smtstate.n_active_down_thesis"])
    aligned = np.where(anchor_direction == "up", up_counts, np.where(anchor_direction == "down", down_counts, 0))
    opposed = np.where(anchor_direction == "up", down_counts, np.where(anchor_direction == "down", up_counts, 0))
    data["smtstate.n_active_aligned"] = aligned.astype(np.int16)
    data["smtstate.has_active_aligned"] = aligned > 0
    data["smtstate.n_active_opposed"] = opposed.astype(np.int16)
    data["smtstate.has_active_opposed"] = opposed > 0

    _assign_named_state_columns(data, cutoff_ns, primary, timeline)
    return pd.DataFrame(data)


def _assign_named_state_columns(
    data: dict[str, Any],
    cutoff_ns: np.ndarray,
    primary: np.ndarray,
    timeline: pd.DataFrame,
) -> None:
    htf_events = ["weekly_smt", "previous_day_smt"]
    for event_type in htf_events:
        for stage in ("forming", "confirmed"):
            for side in ("high", "low"):
                sub = timeline[
                    timeline["source_event_type"].eq(event_type)
                    & timeline["stage"].eq(stage)
                    & timeline["side"].eq(side)
                ]
                counts, age = _active_counts_and_age(cutoff_ns, primary, sub)
                stem = f"htf_{_safe_name(event_type)}_{stage}_{side}"
                data[f"smtstate.n_active_{stem}"] = counts
                data[f"smtstate.has_active_{stem}"] = counts > 0
                data[f"smtstate.minutes_since_latest_{stem}_start"] = age

    mtf = timeline[timeline["source_scope"].eq("mtf_previous_candle")]
    for tf in ("15m", "30m", "1h", "90m", "4h", "6h"):
        for side in ("high", "low"):
            sub = mtf[mtf["state_timeframe"].eq(tf) & mtf["side"].eq(side)]
            counts, age = _active_counts_and_age(cutoff_ns, primary, sub)
            stem = f"mtf_{_safe_name(tf)}_confirmed_{side}"
            data[f"smtstate.n_active_{stem}"] = counts
            data[f"smtstate.has_active_{stem}"] = counts > 0
            data[f"smtstate.minutes_since_latest_{stem}_start"] = age


def _active_counts_and_age(
    cutoff_ns: np.ndarray,
    primary: np.ndarray,
    states: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    counts = np.zeros(len(cutoff_ns), dtype=np.int16)
    ages = np.full(len(cutoff_ns), np.nan, dtype="float64")
    if states.empty:
        return counts, ages

    state = states[["member_symbol", "state_start_ts", "state_end_ts"]].copy()
    state["start_ns"] = state["state_start_ts"].to_numpy("datetime64[ns]").astype("int64")
    state["end_ns"] = state["state_end_ts"].to_numpy("datetime64[ns]").astype("int64")

    for symbol in pd.unique(primary):
        idx = np.where(primary == symbol)[0]
        if len(idx) == 0:
            continue
        sub = state[state["member_symbol"].eq(symbol)]
        if sub.empty:
            continue
        starts = np.sort(sub["start_ns"].to_numpy(dtype="int64"))
        ends = np.sort(sub["end_ns"].to_numpy(dtype="int64"))
        t = cutoff_ns[idx]
        active = np.searchsorted(starts, t, side="right") - np.searchsorted(ends, t, side="right")
        counts[idx] = np.maximum(active, 0).astype(np.int16)

        # Latest-start age is exact when same-category intervals do not overlap,
        # which is true for the intended per-state buckets.
        by_start = sub.sort_values("start_ns")
        starts_by_start = by_start["start_ns"].to_numpy(dtype="int64")
        ends_by_start = by_start["end_ns"].to_numpy(dtype="int64")
        last_idx = np.searchsorted(starts_by_start, t, side="right") - 1
        valid = (last_idx >= 0) & (counts[idx] > 0)
        if valid.any():
            row_idx = idx[valid]
            candidate_idx = last_idx[valid]
            still_active = ends_by_start[candidate_idx] > cutoff_ns[row_idx]
            if still_active.any():
                ok_rows = row_idx[still_active]
                ok_candidate = candidate_idx[still_active]
                ages[ok_rows] = (cutoff_ns[ok_rows] - starts_by_start[ok_candidate]) / NS_PER_MIN

    return counts, ages


def write_context_for_anchor(
    target: AnchorTarget,
    timeline: pd.DataFrame,
    *,
    merge: bool,
) -> dict[str, Any]:
    if not target.matrix_path.exists():
        return {"anchor": target.short_name, "status": "missing_matrix", "rows": 0}

    anchors = pd.read_parquet(target.matrix_path)
    context = build_state_context(anchors, timeline)
    target.context_path.parent.mkdir(parents=True, exist_ok=True)
    context.to_parquet(target.context_path, index=False)

    context_cols = [c for c in context.columns if c.startswith("smtstate.")]
    active_rate = float(context["smtstate.has_active_total"].mean()) if len(context) else float("nan")
    aligned_rate = float(context["smtstate.has_active_aligned"].mean()) if len(context) else float("nan")
    merged_cols = None
    if merge:
        merged = anchors.merge(context, on=["anchor.event_id", "asof.snapshot"], how="left")
        merged.to_parquet(target.output_path, index=False)
        merged_cols = len(merged.columns)
        _write_merged_schema(target, merged=merged, context_cols=context_cols)

    return {
        "anchor": target.short_name,
        "status": "ok",
        "rows": int(len(context)),
        "context_cols": len(context_cols),
        "active_rate": active_rate,
        "aligned_rate": aligned_rate,
        "context_path": str(target.context_path),
        "merged_path": str(target.output_path) if merge else None,
        "merged_cols": merged_cols,
    }


def _write_merged_schema(target: AnchorTarget, *, merged: pd.DataFrame, context_cols: list[str]) -> None:
    schema: dict[str, Any] = {}
    if target.schema_path.exists():
        schema = json.loads(target.schema_path.read_text(encoding="utf-8"))
    old_features = list(schema.get("feature_columns", []))
    feature_columns = [*old_features, *[c for c in context_cols if c not in old_features]]
    label_columns = [c for c in merged.columns if c.startswith("label.")]
    schema.update(
        {
            "generated_utc": datetime.now(UTC).isoformat(),
            "builder": "backend/scripts/ml/build_smt_state_timeline.py",
            "source_schema": str(target.schema_path),
            "source_matrix": str(target.matrix_path),
            "rows": int(len(merged)),
            "columns": int(len(merged.columns)),
            "feature_columns": feature_columns,
            "label_columns": label_columns,
            "smt_state_context": {
                "timeline": str(TIMELINE_PARQUET),
                "context_columns": context_cols,
                "timing_rule": "smtstate.* joined where state_start_ts <= asof.feature_cutoff_ts < state_end_ts for the anchor primary symbol.",
            },
        }
    )
    target.output_schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def write_outputs(timeline: pd.DataFrame, summaries: list[dict[str, Any]], *, args: argparse.Namespace) -> None:
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    timeline.to_parquet(TIMELINE_PARQUET, index=False)
    timeline.to_csv(TIMELINE_CSV, index=False)
    summary_df = pd.DataFrame(summaries)
    summary_df.to_parquet(SUMMARY_PARQUET, index=False)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    _write_doc(timeline, summary_df, args=args)


def _write_doc(timeline: pd.DataFrame, summary: pd.DataFrame, *, args: argparse.Namespace) -> None:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    lines: list[str] = [
        "# SMT State Timeline",
        "",
        f"_Generated `{generated}` by `backend/scripts/ml/build_smt_state_timeline.py`._",
        "",
        "## What This Is",
        "",
        "SMT state timeline converts SMT events into active intervals that can be joined to lower-timeframe events as-of their feature cutoff.",
        "",
        "- `forming`: HTF reference SMT was known before the HTF period closed.",
        "- `confirmed`: HTF SMT survived the period close. If `--include-mtf` is enabled, previous-candle MTF SMT closes are also represented as confirmed states.",
        "- Joins use `state_start_ts <= asof.feature_cutoff_ts < state_end_ts` for the same `member_symbol`.",
        "- `smtstate.*` columns are legal context features; they do not use future labels.",
        "",
        "## Timeline Counts",
        "",
        f"- Timeline rows: `{len(timeline):,}`",
        f"- Source events: `{timeline['source_event_id'].nunique():,}`",
        f"- Member symbols: `{timeline['member_symbol'].nunique():,}`",
        f"- Source mode: `{args.source}`",
        f"- SMT feature source: `{args.smt_features}`",
        f"- Include MTF previous-candle SMT: `{bool(args.include_mtf)}`",
        f"- MTF TTL periods: `{args.mtf_ttl_periods}`",
        "",
    ]
    by_scope = timeline.groupby(["source_scope", "stage"]).size().reset_index(name="rows")
    lines.append(_md_table(["scope", "stage", "rows"], by_scope.values.tolist()))
    lines.extend(["", "## By Event Type", ""])
    by_event = (
        timeline.groupby(["source_event_type", "stage", "side"])
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
    )
    lines.append(_md_table(["event_type", "stage", "side", "rows"], by_event.head(30).values.tolist()))
    lines.extend(["", "## Anchor Context Outputs", ""])
    if summary.empty:
        lines.append("_No anchor contexts were built._")
    else:
        table = []
        for r in summary.itertuples(index=False):
            table.append([
                r.anchor,
                r.status,
                f"{int(r.rows):,}",
                getattr(r, "context_cols", ""),
                _pct(getattr(r, "active_rate", np.nan)),
                _pct(getattr(r, "aligned_rate", np.nan)),
                getattr(r, "merged_path", None) or "",
            ])
        lines.append(
            _md_table(
                ["anchor", "status", "rows", "context cols", "active", "aligned", "merged path"],
                table,
            )
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Timeline parquet: `{TIMELINE_PARQUET}`",
            f"- Timeline CSV: `{TIMELINE_CSV}`",
            f"- Context summary: `{SUMMARY_CSV}`",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(_fmt_cell(x) for x in row) + " |")
    return "\n".join(out)


def _fmt_cell(value: Any) -> str:
    if isinstance(value, (np.integer, int)):
        return f"{int(value):,}"
    if isinstance(value, (np.floating, float)):
        if np.isnan(value):
            return "-"
        return f"{float(value):.4f}"
    return str(value)


def _pct(value: Any) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "-"
    if not np.isfinite(f):
        return "-"
    return f"{f * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--smt-features", type=Path, default=SMT_FEATURES_PATH)
    parser.add_argument(
        "--source",
        choices=("features", "db"),
        default="features",
        help="Use smt.parquet feature artifacts or raw SQLite research_events for HTF SMT state.",
    )
    parser.add_argument(
        "--anchors",
        type=_parse_csv_arg,
        default=list(ANCHOR_TARGETS),
        help=f"Comma-separated anchor shorts to context-join. Choices: {sorted(ANCHOR_TARGETS)}",
    )
    parser.add_argument("--mtf-ttl-periods", type=int, default=4)
    parser.add_argument(
        "--include-mtf",
        action="store_true",
        help="Also include previous-candle MTF SMT as short-lived confirmed states. Default is HTF reference SMT only.",
    )
    parser.add_argument("--no-merge", action="store_true", help="Only write context parquet files; do not write merged anchor matrices.")
    args = parser.parse_args()

    unknown = sorted(set(args.anchors) - set(ANCHOR_TARGETS))
    if unknown:
        raise KeyError(f"unknown anchors: {unknown}; choices={sorted(ANCHOR_TARGETS)}")
    if args.mtf_ttl_periods < 1:
        raise ValueError("--mtf-ttl-periods must be >= 1")

    if args.source == "features":
        events = _load_smt_feature_events(args.smt_features)
        if args.include_mtf:
            db_events = _load_smt_events(args.db)
            mtf = db_events[db_events["feature_name"].eq("smt_prev_candle_divergence")]
            events = pd.concat([events, mtf], ignore_index=True)
    else:
        events = _load_smt_events(args.db)
    timeline = build_timeline(
        events,
        include_mtf=args.include_mtf,
        mtf_ttl_periods=args.mtf_ttl_periods,
    )
    if timeline.empty:
        raise RuntimeError("no SMT state rows built")

    summaries = [
        write_context_for_anchor(ANCHOR_TARGETS[short], timeline, merge=not args.no_merge)
        for short in args.anchors
    ]
    write_outputs(timeline, summaries, args=args)

    print(f"timeline rows: {len(timeline):,}")
    print(f"wrote {TIMELINE_PARQUET}")
    for summary in summaries:
        if summary["status"] == "ok":
            print(
                f"{summary['anchor']}: {summary['rows']:,} rows, "
                f"{summary['context_cols']} smtstate cols, "
                f"active={summary['active_rate']:.1%}, aligned={summary['aligned_rate']:.1%}"
            )
        else:
            print(f"{summary['anchor']}: {summary['status']}")
    print(f"wrote {DOC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
