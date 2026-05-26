"""Append developing-VWAP/SD1 context columns to a snapshot matrix.

For each anchor row, computes VWAP and 1st-standard-deviation bands
over the active session, Globex day, and Globex week as of
`asof.feature_cutoff_ts`, using only 1m bars strictly before the
cutoff. No lookahead.

Pattern mirrors build_cross_concept_context.py. Output columns are
prefixed `fsd1.` (registered in snapshot_feature_registry.py with
family="developing_vwap_sd1").

Usage:
    python build_developing_vwap_sd1_context.py \\
        --matrix data/ml/anchors/sweep_snapshots.parquet \\
        --schema data/ml/anchors/sweep_snapshots.schema.json \\
        --output data/ml/anchors/sweep_snapshots_fsd1.parquet \\
        --schema-output data/ml/anchors/sweep_snapshots_fsd1.schema.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from snapshot_feature_registry import registry_as_dict  # noqa: E402

# Imports from the backtest app: these only resolve when the script is
# run from inside services/backtest (where pyproject pins the package
# root). Same constraint the existing ML scripts rely on.
sys.path.insert(0, str(THIS_DIR.parent.parent))

from app.core.paths import warehouse_root  # noqa: E402
from app.data.reader import read_bars  # noqa: E402
from app.research.developing_vwap_sd1 import (  # noqa: E402
    ALL_PERIODS,
    DevelopingSD1,
    PeriodKind,
)
from app.research.sessions import globex_day_for, globex_week_for, session_for  # noqa: E402

UTC = timezone.utc

# Default sample window for batch bar loads. Keeps each read_bars call
# bounded so memory stays manageable for very long anchor matrices.
BAR_LOAD_PADDING_DAYS = 8  # 1 globex week + 1 day cushion

PERIOD_SHORT: dict[PeriodKind, str] = {
    "session_asia": "asia",
    "session_london": "london",
    "session_ny": "ny",
    "globex_day": "day",
    "globex_week": "week",
}

ANCHOR_PRICE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "smt": ("smt.ed.first_break_price",),
    "fvg": ("fvg.ed.candle_3.close", "fvg.ed.fvg_mid"),
    "sweep": ("sweep.ed.manipulation_candle.close", "sweep.ed.swept_reference.level_price"),
    "ob": ("ob.ed.confirmation_candle.close", "ob.ed.ob_body_mid"),
    "tp": ("tp.ed.parent_close",),
    "vp": ("vp.ed.period_close", "vp.ed.vwap"),
    "fvp": ("fvp.ed.asof_close", "fvp.ed.vwap"),
    "ogap": ("ogap.ed.current_open_price", "ogap.ed.gap_mid"),
}

GENERIC_PRICE_CANDIDATES: tuple[str, ...] = (
    "anchor.close_price",
    "anchor.bar_close",
    "anchor.price",
)


def _column_prefix(period: PeriodKind) -> str:
    return f"fsd1.{PERIOD_SHORT[period]}"


def fsd1_columns(periods: tuple[PeriodKind, ...] = ALL_PERIODS) -> list[str]:
    cols: list[str] = []
    for p in periods:
        prefix = _column_prefix(p)
        cols.extend(
            [
                f"{prefix}.vwap_pts",
                f"{prefix}.sd_pts",
                f"{prefix}.sd1_high_pts",
                f"{prefix}.sd1_low_pts",
                f"{prefix}.n_bars",
                f"{prefix}.close_dist_vwap_pts",
                f"{prefix}.close_dist_sd_units",
                f"{prefix}.above_sd1",
                f"{prefix}.below_sd1",
                f"{prefix}.inside_band",
            ]
        )
    return cols


def _infer_anchor_short(matrix: pd.DataFrame, schema: dict[str, object] | None = None) -> str | None:
    if "anchor.short_name" in matrix.columns:
        vals = matrix["anchor.short_name"].dropna().unique()
        if len(vals) == 1:
            return str(vals[0])
    anchor = (schema or {}).get("anchor")
    if isinstance(anchor, dict):
        short = anchor.get("short_name")
        if short:
            return str(short)
    return None


def infer_anchor_price_col(
    matrix: pd.DataFrame,
    *,
    schema: dict[str, object] | None = None,
    explicit: str | None = None,
) -> str | None:
    """Pick the best legal row price for distance-to-VWAP features.

    The absolute VWAP/SD levels do not need an anchor price, but
    `close_dist_*` and band flags do. Matrices use concept-specific
    event-data columns rather than a shared `anchor.close_price`, so
    infer by anchor short name before falling back to generic columns.
    """
    if explicit:
        if explicit not in matrix.columns:
            raise KeyError(f"--anchor-price-col not in matrix: {explicit}")
        return explicit
    short = _infer_anchor_short(matrix, schema)
    for col in ANCHOR_PRICE_CANDIDATES.get(short or "", ()):
        if col in matrix.columns:
            return col
    for col in GENERIC_PRICE_CANDIDATES:
        if col in matrix.columns:
            return col
    return None


def _row_features(
    snap: DevelopingSD1,
    *,
    anchor_close_price: float | None,
    period: PeriodKind,
) -> dict[str, float | int | None]:
    """Build the column values for one anchor row × period."""
    prefix = _column_prefix(period)
    if snap.is_empty:
        return {
            f"{prefix}.vwap_pts": np.nan,
            f"{prefix}.sd_pts": np.nan,
            f"{prefix}.sd1_high_pts": np.nan,
            f"{prefix}.sd1_low_pts": np.nan,
            f"{prefix}.n_bars": 0,
            f"{prefix}.close_dist_vwap_pts": np.nan,
            f"{prefix}.close_dist_sd_units": np.nan,
            f"{prefix}.above_sd1": False,
            f"{prefix}.below_sd1": False,
            f"{prefix}.inside_band": False,
        }
    close_dist_vwap = (
        float(anchor_close_price) - snap.vwap
        if anchor_close_price is not None
        else np.nan
    )
    close_dist_sd_units = (
        close_dist_vwap / snap.sd
        if (anchor_close_price is not None and snap.sd > 0)
        else np.nan
    )
    above = (
        anchor_close_price is not None and float(anchor_close_price) > snap.sd1_high
    )
    below = (
        anchor_close_price is not None and float(anchor_close_price) < snap.sd1_low
    )
    inside = anchor_close_price is not None and not above and not below
    return {
        f"{prefix}.vwap_pts": snap.vwap,
        f"{prefix}.sd_pts": snap.sd,
        f"{prefix}.sd1_high_pts": snap.sd1_high,
        f"{prefix}.sd1_low_pts": snap.sd1_low,
        f"{prefix}.n_bars": snap.n_bars,
        f"{prefix}.close_dist_vwap_pts": close_dist_vwap,
        f"{prefix}.close_dist_sd_units": close_dist_sd_units,
        f"{prefix}.above_sd1": bool(above),
        f"{prefix}.below_sd1": bool(below),
        f"{prefix}.inside_band": bool(inside),
    }


def _load_bars_for_symbol(
    symbol: str,
    *,
    start_utc: datetime,
    end_utc: datetime,
    bar_loader=read_bars,
) -> pd.DataFrame:
    """Load 1m bars for one symbol across a date range. Pads the range
    by BAR_LOAD_PADDING_DAYS on the lower bound so any open Globex
    week containing the earliest anchor still has its start covered.
    """
    pad_start = start_utc - timedelta(days=BAR_LOAD_PADDING_DAYS)
    df = bar_loader(
        symbol=symbol,
        timeframe="1m",
        start=pad_start.date(),
        end=(end_utc + timedelta(days=1)).date(),
    )
    if df is None or df.empty:
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
            index=pd.DatetimeIndex([], tz="UTC", name="ts_event"),
        )
    # Reader returns whatever sort key exists; normalize to a tz-aware
    # UTC DatetimeIndex.
    if "ts_event" in df.columns:
        df = df.set_index("ts_event")
    if df.index.tz is None:
        df.index = df.index.tz_localize(UTC)
    else:
        df.index = df.index.tz_convert(UTC)
    return df.sort_index()


def _period_for(period: PeriodKind, as_of_ts: datetime):
    if period == "globex_day":
        return globex_day_for(as_of_ts)
    if period == "globex_week":
        return globex_week_for(as_of_ts)
    if period == "session_asia":
        return session_for(as_of_ts, "asia")
    if period == "session_london":
        return session_for(as_of_ts, "london")
    if period == "session_ny":
        return session_for(as_of_ts, "ny")
    raise ValueError(f"unknown period kind: {period!r}")


def _prepare_fast_bars(bars: pd.DataFrame) -> dict[str, np.ndarray]:
    if bars.empty:
        return {
            "index_ns": np.array([], dtype="int64"),
            "cum_volume": np.array([0.0], dtype="float64"),
            "cum_wx": np.array([0.0], dtype="float64"),
            "cum_wx2": np.array([0.0], dtype="float64"),
        }
    typical = (
        pd.to_numeric(bars["open"], errors="coerce")
        + pd.to_numeric(bars["high"], errors="coerce")
        + pd.to_numeric(bars["low"], errors="coerce")
        + pd.to_numeric(bars["close"], errors="coerce")
    ).to_numpy(dtype="float64") / 4.0
    volume = pd.to_numeric(bars["volume"], errors="coerce").fillna(0.0).to_numpy(dtype="float64")
    valid = np.isfinite(typical) & np.isfinite(volume) & (volume > 0)
    typical = np.where(valid, typical, 0.0)
    volume = np.where(valid, volume, 0.0)
    wx = typical * volume
    wx2 = typical * typical * volume
    return {
        "index_ns": bars.index.to_numpy("datetime64[ns]").astype("int64"),
        "cum_volume": np.concatenate(([0.0], np.cumsum(volume))),
        "cum_wx": np.concatenate(([0.0], np.cumsum(wx))),
        "cum_wx2": np.concatenate(([0.0], np.cumsum(wx2))),
    }


def _fast_developing_vwap_sd1_at(
    prepared: dict[str, np.ndarray],
    *,
    as_of_ts: datetime,
    period_kind: PeriodKind,
) -> DevelopingSD1:
    if as_of_ts.tzinfo is None:
        as_of_ts = as_of_ts.replace(tzinfo=UTC)
    else:
        as_of_ts = as_of_ts.astimezone(UTC)
    period = _period_for(period_kind, as_of_ts)
    effective_cutoff = min(as_of_ts, period.end_utc)

    index_ns = prepared["index_ns"]
    if len(index_ns) == 0 or effective_cutoff <= period.start_utc:
        return _empty_snapshot(period_kind, period.start_utc, period.end_utc, as_of_ts)

    start_ns = pd.Timestamp(period.start_utc).value
    cutoff_ns = pd.Timestamp(effective_cutoff).value
    left = int(np.searchsorted(index_ns, start_ns, side="left"))
    right = int(np.searchsorted(index_ns, cutoff_ns, side="left"))
    n_bars = max(right - left, 0)
    if n_bars <= 0:
        return _empty_snapshot(period_kind, period.start_utc, period.end_utc, as_of_ts)

    cum_volume = prepared["cum_volume"]
    cum_wx = prepared["cum_wx"]
    cum_wx2 = prepared["cum_wx2"]
    total_volume = float(cum_volume[right] - cum_volume[left])
    if total_volume <= 0.0:
        return _empty_snapshot(period_kind, period.start_utc, period.end_utc, as_of_ts)

    sum_wx = float(cum_wx[right] - cum_wx[left])
    sum_wx2 = float(cum_wx2[right] - cum_wx2[left])
    vwap = sum_wx / total_volume
    var = max((sum_wx2 / total_volume) - (vwap * vwap), 0.0)
    sd = math.sqrt(var) if var > 0.0 else 0.0
    return DevelopingSD1(
        period_kind=period_kind,
        period_start_utc=period.start_utc,
        period_end_utc=period.end_utc,
        as_of_ts=as_of_ts,
        n_bars=n_bars,
        total_volume=total_volume,
        vwap=vwap,
        sd=sd,
        sd1_high=vwap + sd,
        sd1_low=vwap - sd,
    )


def _empty_snapshot(
    period_kind: PeriodKind,
    period_start_utc: datetime,
    period_end_utc: datetime,
    as_of_ts: datetime,
) -> DevelopingSD1:
    return DevelopingSD1(
        period_kind=period_kind,
        period_start_utc=period_start_utc,
        period_end_utc=period_end_utc,
        as_of_ts=as_of_ts,
        n_bars=0,
        total_volume=0.0,
        vwap=0.0,
        sd=0.0,
        sd1_high=0.0,
        sd1_low=0.0,
    )


def build_context(
    matrix: pd.DataFrame,
    *,
    periods: tuple[PeriodKind, ...] = ALL_PERIODS,
    anchor_price_col: str | None = None,
    bar_loader=read_bars,
) -> pd.DataFrame:
    """Build the fsd1.* context columns for every anchor row.

    Returns a frame keyed on `anchor.event_id` + `asof.snapshot` with
    one column per (period, metric).
    """
    required = ["anchor.event_id", "asof.snapshot", "anchor.primary_symbol", "asof.feature_cutoff_ts"]
    missing = [c for c in required if c not in matrix.columns]
    if missing:
        raise KeyError(f"matrix missing required columns: {missing}")

    cutoff_series = pd.to_datetime(matrix["asof.feature_cutoff_ts"], utc=True)
    close_col = infer_anchor_price_col(matrix, explicit=anchor_price_col)

    # Group by symbol to load bars once per symbol.
    by_symbol: dict[str, list[int]] = defaultdict(list)
    for idx, sym in enumerate(matrix["anchor.primary_symbol"]):
        by_symbol[str(sym)].append(idx)

    output_rows: list[dict[str, object]] = [{} for _ in range(len(matrix))]
    for symbol, indices in by_symbol.items():
        cutoffs = cutoff_series.iloc[indices]
        bars = _load_bars_for_symbol(
            symbol,
            start_utc=cutoffs.min().to_pydatetime(),
            end_utc=cutoffs.max().to_pydatetime(),
            bar_loader=bar_loader,
        )
        prepared = _prepare_fast_bars(bars)
        for row_idx in indices:
            cutoff = cutoff_series.iloc[row_idx].to_pydatetime()
            close_price = (
                float(matrix.iloc[row_idx][close_col])
                if close_col is not None and pd.notna(matrix.iloc[row_idx][close_col])
                else None
            )
            row_features: dict[str, object] = {}
            for period in periods:
                snap = _fast_developing_vwap_sd1_at(
                    prepared,
                    as_of_ts=cutoff,
                    period_kind=period,
                )
                row_features.update(
                    _row_features(
                        snap, anchor_close_price=close_price, period=period
                    )
                )
            output_rows[row_idx] = row_features

    context_df = pd.DataFrame(output_rows)
    context_df.insert(0, "anchor.event_id", matrix["anchor.event_id"].to_numpy())
    context_df.insert(1, "asof.snapshot", matrix["asof.snapshot"].to_numpy())
    return context_df


def _write_schema(
    schema_output: Path,
    *,
    source_schema: Path,
    matrix: pd.DataFrame,
    context_cols: list[str],
    args: argparse.Namespace,
) -> None:
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    old_features = list(schema.get("feature_columns", []))
    merged_features = [*old_features, *[c for c in context_cols if c not in old_features]]
    schema.update(
        {
            "generated_utc": datetime.now(UTC).isoformat(),
            "builder": "backend/scripts/ml/build_developing_vwap_sd1_context.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(matrix)),
            "feature_columns": merged_features,
            "registry": registry_as_dict(),
            "developing_vwap_sd1": {
                "periods": list(args.periods),
                "warehouse_root": str(warehouse_root()),
                "context_columns": context_cols,
                "anchor_price_col": args.anchor_price_col,
            },
            "notes": [
                *schema.get("notes", []),
                "fsd1.* features are developing VWAP and 1st-SD bands computed "
                "from 1m bars strictly before asof.feature_cutoff_ts. No lookahead.",
            ],
        }
    )
    schema_output.parent.mkdir(parents=True, exist_ok=True)
    schema_output.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[Path, Path, pd.DataFrame]:
    matrix = pd.read_parquet(args.matrix)
    if matrix.empty:
        raise ValueError("anchor matrix is empty")
    source_schema = json.loads(args.schema.read_text(encoding="utf-8"))
    anchor_price_col = infer_anchor_price_col(
        matrix,
        schema=source_schema,
        explicit=args.anchor_price_col,
    )
    args.anchor_price_col = anchor_price_col
    context = build_context(
        matrix,
        periods=args.periods,
        anchor_price_col=anchor_price_col,
    )
    context_cols = [c for c in context.columns if c.startswith("fsd1.")]
    merged = matrix.merge(
        context,
        on=["anchor.event_id", "asof.snapshot"],
        how="left",
        validate="one_to_one",
    )
    if merged[context_cols].isna().all(axis=None):
        raise ValueError("all generated fsd1 columns are null")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(args.output, index=False)
    _write_schema(
        args.schema_output,
        source_schema=args.schema,
        matrix=merged,
        context_cols=context_cols,
        args=args,
    )
    return args.output, args.schema_output, merged


def _parse_periods(value: str) -> tuple[PeriodKind, ...]:
    if not value or value == "all":
        return ALL_PERIODS
    parts = [p.strip() for p in value.split(",") if p.strip()]
    unknown = sorted(set(parts) - set(ALL_PERIODS))
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown periods: {unknown}; choices={list(ALL_PERIODS)}"
        )
    return tuple(parts)  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--schema-output", type=Path, required=True)
    parser.add_argument(
        "--anchor-price-col",
        default=None,
        help=(
            "Optional matrix column used for distance-to-VWAP features. "
            "Defaults to concept-aware inference."
        ),
    )
    parser.add_argument(
        "--periods",
        type=_parse_periods,
        default=ALL_PERIODS,
        help=(
            "Comma-separated list of period kinds, or 'all'. "
            f"Choices: {list(ALL_PERIODS)}"
        ),
    )
    args = parser.parse_args()
    out_path, schema_path, merged = build(args)
    n_fsd1 = sum(c.startswith("fsd1.") for c in merged.columns)
    print(f"wrote {out_path}: {len(merged):,} rows x {len(merged.columns):,} cols")
    print(f"wrote {schema_path}")
    print(f"  fsd1 columns added: {n_fsd1}")
    print(f"  anchor price column: {args.anchor_price_col or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
