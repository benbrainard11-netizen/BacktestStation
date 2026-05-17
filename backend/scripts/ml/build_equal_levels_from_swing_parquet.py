"""Build equal-level artifacts directly from expanded swing parquet.

The original equal-level detector reads parent `swing_pivot` rows from SQLite.
Expanded-universe research events are shared as parquet, so this script builds
equal levels from `data/ml/features/swing.parquet` without requiring a 4M-row
SQLite import.

Important scope: the detector tolerances are absolute price points inherited
from the original index workflow. By default this script only builds equity
index symbols where those tolerances are meaningful enough to compare with the
existing core dataset. Asset-normalized equal levels for FX/energy/rates should
be a separate v2 design.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(r"C:\Users\benbr\BacktestStation")
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.data.reader import read_bars  # noqa: E402
from app.services.research_events import make_event_id  # noqa: E402

UTC = timezone.utc
FEATURES_DIR = ROOT / "data" / "ml" / "features"
RESEARCH_EVENTS_DIR = ROOT / "data" / "research_events"

DEFAULT_SWING_FEATURES = FEATURES_DIR / "swing.parquet"
DEFAULT_FEATURE_OUTPUT = FEATURES_DIR / "eql.parquet"
DEFAULT_RESEARCH_OUTPUT = RESEARCH_EVENTS_DIR
DEFAULT_MANIFEST = RESEARCH_EVENTS_DIR / "manifest.json"
DEFAULT_DOC = ROOT / "docs" / "ML_EQUAL_LEVELS_EXPANDED_BUILD.md"
DEFAULT_REMOTE_DOWNLOAD_SUMMARY = ROOT / "data" / "ml" / "logs" / "r2_artifact_download_last.json"
DEFAULT_SYMBOLS = ("ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0")

MODE_CONFIG: dict[str, dict[str, Any]] = {
    "eq_pivot_5_1h_5pts": {"parent": "pivot_5_1h", "tol_pts": 5.0},
    "eq_pivot_5_1h_15pts": {"parent": "pivot_5_1h", "tol_pts": 15.0},
    "eq_pivot_5_4h_15pts": {"parent": "pivot_5_4h", "tol_pts": 15.0},
    "eq_pivot_5_daily_30pts": {"parent": "pivot_5_daily", "tol_pts": 30.0},
    "eq_pivot_3_1h_5pts": {"parent": "pivot_3_1h", "tol_pts": 5.0},
    "eq_pivot_3_1h_15pts": {"parent": "pivot_3_1h", "tol_pts": 15.0},
    "eq_pivot_3_4h_15pts": {"parent": "pivot_3_4h", "tol_pts": 15.0},
}
FORWARD_WINDOWS = (5, 25, 100, 250)
MAX_FORWARD_BARS = 250
PAD_FORWARD_BARS = 25
CROSS_DETECTOR_WINDOW_HOURS = 24
DETECTOR_SHORT_TO_FEATURE = {
    "smt": "smt_htf_reference_divergence",
    "psp": "psp_candle_divergence",
    "fvg": "fvg_formation",
    "ob": "order_block",
    "sweep": "liquidity_sweep",
    "disp": "displacement_candle",
    "swing": "swing_pivot",
    "ft": "first_third_range",
    "orb": "opening_range_breakout",
    "eql": "equal_levels",
    "tp": "time_profile",
    "vp": "volume_profile",
    "fvp": "forming_volume_profile",
    "ogap": "opening_gap_levels",
    "itr": "interval_true_range",
    "macro": "macro_event_anchor",
}


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _to_utc(ts: Any) -> pd.Timestamp:
    return pd.Timestamp(ts).tz_convert("UTC") if pd.Timestamp(ts).tzinfo else pd.Timestamp(ts).tz_localize("UTC")


def _flatten(obj: Any, prefix: str = "", out: dict[str, Any] | None = None) -> dict[str, Any]:
    if out is None:
        out = {}
    if obj is None:
        return out
    if isinstance(obj, (int, float, bool, str)):
        out[prefix.rstrip(".")] = obj
        return out
    if isinstance(obj, dict):
        for key, value in obj.items():
            _flatten(value, f"{prefix}{key}.", out)
        return out
    if isinstance(obj, list):
        out[prefix.rstrip(".") + "__len"] = len(obj)
        return out
    return out


def _safe_part(value: Any) -> str:
    text = str(value or "unknown")
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, "_")
    return text.replace(" ", "_")


def _load_swing_features(path: Path, symbols: list[str]) -> pd.DataFrame:
    columns = [
        "event_id",
        "event_type",
        "primary_symbol",
        "side",
        "bar_end_utc",
        "year",
        "ed.n",
        "ed.pivot_price",
    ]
    df = pd.read_parquet(path, columns=[c for c in columns if c in pd.read_parquet(path, columns=[]).columns])
    # The pyarrow metadata path above is not reliable with all engines; reread
    # explicitly if pandas returned no columns.
    if df.empty and path.exists():
        all_cols = pq.ParquetFile(path).schema.names
        df = pd.read_parquet(path, columns=[c for c in columns if c in all_cols])
    df = df[df["primary_symbol"].isin(symbols)].copy()
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    df["ed.pivot_price"] = pd.to_numeric(df["ed.pivot_price"], errors="coerce")
    df = df[df["ed.pivot_price"].notna()]
    return df.sort_values(["primary_symbol", "event_type", "side", "bar_end_utc"]).reset_index(drop=True)


def _load_swing_features_fast(path: Path, symbols: list[str]) -> pd.DataFrame:
    all_cols = pq.ParquetFile(path).schema.names
    cols = [
        c
        for c in [
            "event_id",
            "event_type",
            "primary_symbol",
            "side",
            "bar_end_utc",
            "ed.n",
            "ed.pivot_price",
        ]
        if c in all_cols
    ]
    df = pd.read_parquet(path, columns=cols)
    df = df[df["primary_symbol"].isin(symbols)].copy()
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    df["ed.pivot_price"] = pd.to_numeric(df["ed.pivot_price"], errors="coerce")
    df = df[df["ed.pivot_price"].notna()]
    return df.sort_values(["primary_symbol", "event_type", "side", "bar_end_utc"]).reset_index(drop=True)


def _find_equal_clusters(
    pivots: pd.DataFrame,
    *,
    side: str,
    mode: str,
    parent_mode: str,
    tolerance_pts: float,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    max_lookback = 10
    records = pivots.to_dict(orient="records")
    for idx, pivot in enumerate(records):
        pivot_price = float(pivot["ed.pivot_price"])
        cluster = []
        for prev in records[max(0, idx - max_lookback):idx]:
            prev_price = float(prev["ed.pivot_price"])
            if abs(pivot_price - prev_price) <= tolerance_pts:
                cluster.append(prev)
        if not cluster:
            continue
        cluster.append(pivot)
        prices = [float(item["ed.pivot_price"]) for item in cluster]
        ts = _to_utc(pivot["bar_end_utc"]).to_pydatetime()
        symbol = str(pivot["primary_symbol"])
        members = [
            {
                "ts_utc": _to_utc(item["bar_end_utc"]).isoformat(),
                "price": float(item["ed.pivot_price"]),
                "pivot_event_id": str(item.get("event_id")),
                "pivot_n": int(item.get("ed.n")) if pd.notna(item.get("ed.n")) else None,
            }
            for item in cluster
        ]
        level_price = max(prices) if side == "high" else min(prices)
        event_data = {
            "schema_version": 1,
            "detector_version": "v1",
            "mode": mode,
            "side": side,
            "tolerance_pts": float(tolerance_pts),
            "parent_pivot_mode": parent_mode,
            "n_members": len(cluster),
            "members": members,
            "level_price": level_price,
            "cluster_mid": (max(prices) + min(prices)) / 2.0,
            "cluster_spread_pts": max(prices) - min(prices),
            "cluster_min_price": min(prices),
            "cluster_max_price": max(prices),
        }
        context = {
            "day_of_week_et": pd.Timestamp(ts).tz_convert("America/New_York").weekday(),
            "hour_of_day_et": pd.Timestamp(ts).tz_convert("America/New_York").hour,
            "n_members": len(cluster),
            "tolerance_pts": float(tolerance_pts),
            "build_scope": "equity_index_absolute_points",
        }
        event_id = make_event_id("equal_levels", symbol, ts, mode)
        events.append(
            {
                "id": event_id,
                "event_id": event_id,
                "knowledge_card_id": None,
                "feature_name": "equal_levels",
                "event_type": mode,
                "side": side,
                "primary_symbol": symbol,
                "symbols": json.dumps([symbol]),
                "related_symbols": json.dumps([symbol]),
                "timeframe": "LEVEL",
                "bar_start_utc": None,
                "bar_end_utc": ts.isoformat(),
                "event_data": event_data,
                "context": context,
                "outcomes": None,
                "replay_pointer": {
                    "primary_symbol": symbol,
                    "ts_utc": ts.isoformat(),
                    "level_price": level_price,
                    "side": side,
                },
                "source_dataset": "expanded_swing_parquet",
                "source_run_id": None,
                "detector_version": "v1",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
    return events


def build_events(swing: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    all_events: list[dict[str, Any]] = []
    for mode, cfg in MODE_CONFIG.items():
        parent = str(cfg["parent"])
        tolerance = float(cfg["tol_pts"])
        parent_df = swing[swing["event_type"].eq(parent)]
        for symbol in symbols:
            for side in ("high", "low"):
                pivots = parent_df[
                    parent_df["primary_symbol"].eq(symbol)
                    & parent_df["side"].eq(side)
                ].copy()
                if len(pivots) < 2:
                    continue
                all_events.extend(
                    _find_equal_clusters(
                        pivots,
                        side=side,
                        mode=mode,
                        parent_mode=parent,
                        tolerance_pts=tolerance,
                    )
                )
    out = pd.DataFrame(all_events)
    if out.empty:
        return out
    out = out.drop_duplicates("event_id").sort_values(["bar_end_utc", "primary_symbol", "event_type"]).reset_index(drop=True)
    return out


def _load_bars_for_symbol(symbol: str, events: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(events["bar_end_utc"], utc=True)
    start = (ts.min() - pd.Timedelta(days=1)).date().isoformat()
    end = (ts.max() + pd.Timedelta(days=14)).date().isoformat()
    bars = read_bars(symbol=symbol, timeframe="1h", start=start, end=end)
    if bars is None or len(bars) == 0:
        return pd.DataFrame()
    bars = bars.copy()
    bars["ts_event"] = pd.to_datetime(bars["ts_event"], utc=True)
    return bars.sort_values("ts_event").reset_index(drop=True)


def _compute_take(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    open_: np.ndarray,
    *,
    level_price: float,
    side: str,
) -> dict[str, Any]:
    bars_to_wick = None
    bars_to_close = None
    deepest = 0.0
    same_bar_reversal = None
    for idx in range(len(high)):
        if side == "high":
            wicked = high[idx] > level_price
            closed_past = close[idx] > level_price
            depth = max(0.0, high[idx] - level_price)
            reversal = bool(wicked and not closed_past)
        else:
            wicked = low[idx] < level_price
            closed_past = close[idx] < level_price
            depth = max(0.0, level_price - low[idx])
            reversal = bool(wicked and not closed_past)
        if wicked:
            if bars_to_wick is None:
                bars_to_wick = idx + 1
                same_bar_reversal = reversal
            deepest = max(deepest, float(depth))
        if closed_past and bars_to_close is None:
            bars_to_close = idx + 1
        if bars_to_wick is not None and bars_to_close is not None:
            break
    return {
        "wick_taken": bars_to_wick is not None,
        "close_past": bars_to_close is not None,
        "bars_to_wick": bars_to_wick,
        "bars_to_close": bars_to_close,
        "deepest_pts_past": float(deepest),
        "first_take_was_reversal": same_bar_reversal,
    }


def _empty_excursion() -> dict[str, Any]:
    return {
        "n_bars": 0,
        "reference_close": None,
        "window_high": None,
        "window_low": None,
        "last_close": None,
        "mfe_pts_in_thesis": None,
        "mae_pts_against_thesis": None,
    }


def _excursion(after: pd.DataFrame, *, reference_close: float, side: str) -> dict[str, Any]:
    if after.empty:
        return _empty_excursion()
    win_high = float(after["high"].max())
    win_low = float(after["low"].min())
    last_close = float(after["close"].iloc[-1])
    if side == "high":
        mfe = reference_close - win_low
        mae = win_high - reference_close
    else:
        mfe = win_high - reference_close
        mae = reference_close - win_low
    return {
        "n_bars": int(len(after)),
        "reference_close": float(reference_close),
        "window_high": win_high,
        "window_low": win_low,
        "last_close": last_close,
        "mfe_pts_in_thesis": float(mfe),
        "mae_pts_against_thesis": float(mae),
    }


def _compute_outcome_for_event(event: pd.Series, bars: pd.DataFrame) -> dict[str, Any] | None:
    event_ts = _to_utc(event["bar_end_utc"])
    start_ts = event_ts + pd.Timedelta(hours=1)
    start_idx = int(np.searchsorted(bars["_ts_ns"].to_numpy(), start_ts.value, side="left"))
    forward = bars.iloc[start_idx:start_idx + MAX_FORWARD_BARS]
    if forward.empty:
        return None
    side = str(event["side"])
    level_price = float(event["event_data"]["level_price"])
    take = _compute_take(
        forward["high"].to_numpy(dtype=float),
        forward["low"].to_numpy(dtype=float),
        forward["close"].to_numpy(dtype=float),
        forward["open"].to_numpy(dtype=float),
        level_price=level_price,
        side=side,
    )
    if take["bars_to_wick"] is not None:
        tap_idx = int(take["bars_to_wick"]) - 1
        tap_close = float(forward["close"].iloc[tap_idx])
        after = forward.iloc[tap_idx + 1:]
        post = {"tap_bar_close": tap_close}
        for n in FORWARD_WINDOWS:
            post[f"forward_{n}_after_take"] = _excursion(
                after.iloc[:n],
                reference_close=tap_close,
                side=side,
            )
    else:
        post = None
    return {
        "schema_version": 1,
        "outcome_version": "v1",
        "level_price": level_price,
        "side": side,
        "thesis_direction": "down" if side == "high" else "up",
        "take": take,
        "post_take_reaction": post,
        "horizon_bars": int(len(forward)),
    }


def compute_outcomes(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    out = events.copy()
    outcomes: list[dict[str, Any] | None] = [None] * len(out)
    for symbol, sub in out.groupby("primary_symbol", sort=True):
        print(f"loading 1h bars for {symbol} ({len(sub):,} equal-level events)")
        bars = _load_bars_for_symbol(str(symbol), sub)
        if bars.empty:
            print(f"  no bars for {symbol}; leaving outcomes empty")
            continue
        bars["_ts_ns"] = bars["ts_event"].astype("int64")
        for idx, row in sub.iterrows():
            outcomes[idx] = _compute_outcome_for_event(row, bars)
    out["outcomes"] = outcomes
    return out[out["outcomes"].notna()].reset_index(drop=True)


def _load_cross_detector_times() -> dict[str, dict[str, np.ndarray]]:
    out: dict[str, dict[str, np.ndarray]] = {}
    for short in DETECTOR_SHORT_TO_FEATURE:
        if short == "eql":
            continue
        path = FEATURES_DIR / f"{short}.parquet"
        if not path.exists():
            out[short] = {}
            continue
        try:
            df = pd.read_parquet(path, columns=["primary_symbol", "bar_end_utc"])
        except Exception:
            out[short] = {}
            continue
        df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
        by_sym = {}
        for symbol, sub in df.groupby("primary_symbol"):
            arr = sub["bar_end_utc"].astype("int64").to_numpy()
            arr.sort()
            by_sym[str(symbol)] = arr
        out[short] = by_sym
    return out


def build_feature_matrix(events: pd.DataFrame, *, include_xd: bool = True) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in events.itertuples(index=False):
        ts = _to_utc(row.bar_end_utc)
        event_data = row.event_data if isinstance(row.event_data, dict) else {}
        outcomes = row.outcomes if isinstance(row.outcomes, dict) else {}
        context = row.context if isinstance(row.context, dict) else {}
        rows.append(
            {
                "event_id": row.event_id,
                "bar_end_utc": ts,
                "year": int(ts.year),
                "month": int(ts.month),
                "day_of_week": int(ts.dayofweek),
                "hour_of_day_utc": int(ts.hour),
                "event_type": row.event_type,
                "side": row.side,
                "primary_symbol": row.primary_symbol,
                **_flatten(event_data, prefix="ed."),
                **_flatten(outcomes, prefix="oc."),
                **_flatten(context, prefix="ctx."),
            }
        )
    features = pd.DataFrame(rows)
    if features.empty or not include_xd:
        return features

    event_ns = features["bar_end_utc"].astype("int64").to_numpy()
    primary = features["primary_symbol"].to_numpy()
    window_ns = CROSS_DETECTOR_WINDOW_HOURS * 3600 * 10**9
    other_times = _load_cross_detector_times()
    for short, by_symbol in other_times.items():
        flag = np.zeros(len(features), dtype=bool)
        for symbol in pd.unique(primary):
            arr = by_symbol.get(str(symbol))
            if arr is None or len(arr) == 0:
                continue
            idx = np.where(primary == symbol)[0]
            ts = event_ns[idx]
            left = np.searchsorted(arr, ts - window_ns, side="left")
            right = np.searchsorted(arr, ts, side="left")
            flag[idx] = right > left
        features[f"xd.has_{short}_in_{CROSS_DETECTOR_WINDOW_HOURS}h"] = flag
    return features


def _write_research_events(events: pd.DataFrame, output_dir: Path) -> list[dict[str, Any]]:
    output_dir = output_dir.resolve()
    target = output_dir / "feature_name=equal_levels"
    if target.exists():
        for path in target.rglob("*.parquet"):
            path.unlink()
    files: list[dict[str, Any]] = []
    work = events.copy()
    work["event_year"] = pd.to_datetime(work["bar_end_utc"], utc=True).dt.year.astype("int16")
    serial = work.copy()
    for col in ("event_data", "context", "outcomes", "replay_pointer"):
        serial[col] = serial[col].map(lambda value: json.dumps(value) if value is not None else None)
    for year, sub in serial.groupby("event_year", sort=True):
        path = target / f"event_year={int(year)}" / f"part-eql-{int(year)}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(sub.drop(columns=["event_year"]), preserve_index=False)
        pq.write_table(table, path, compression="zstd")
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "feature_name": "equal_levels",
                "event_year": int(year),
                "rows": int(len(sub)),
                "size_bytes": int(path.stat().st_size),
            }
        )
    return files


def _remote_research_event_paths(download_summary: Path) -> set[str]:
    if not download_summary.exists():
        return set()
    payload = json.loads(download_summary.read_text(encoding="utf-8"))
    paths: set[str] = set()
    for item in payload.get("selected_artifacts", []):
        if item.get("group") != "research_events":
            continue
        local_path = str(item.get("local_path", "")).replace("\\", "/")
        if local_path.endswith(".parquet"):
            paths.add(local_path)
    return paths


def _existing_equal_research_files(research_dir: Path) -> list[dict[str, Any]]:
    target = research_dir.resolve() / "feature_name=equal_levels"
    files: list[dict[str, Any]] = []
    for path in sorted(target.glob("event_year=*/*.parquet")):
        year = int(path.parent.name.split("=", 1)[-1])
        rows = int(pq.ParquetFile(path).metadata.num_rows)
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "feature_name": "equal_levels",
                "event_year": year,
                "rows": rows,
                "size_bytes": int(path.stat().st_size),
            }
        )
    return files


def _refresh_research_manifest(
    manifest_path: Path,
    research_dir: Path,
    *,
    include_paths: set[str] | None = None,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    research_dir = research_dir.resolve()
    files: list[dict[str, Any]] = []
    for path in sorted(research_dir.glob("feature_name=*/event_year=*/*.parquet")):
        rel_path = path.relative_to(ROOT).as_posix()
        if include_paths is not None and rel_path not in include_paths:
            continue
        feature = path.parent.parent.name.split("=", 1)[-1]
        year = int(path.parent.name.split("=", 1)[-1])
        rows = int(pq.ParquetFile(path).metadata.num_rows)
        files.append(
            {
                "path": rel_path,
                "feature_name": feature,
                "event_year": year,
                "rows": rows,
                "size_bytes": int(path.stat().st_size),
            }
        )
    by_feature: dict[str, int] = defaultdict(int)
    by_year: dict[str, int] = defaultdict(int)
    for item in files:
        by_feature[item["feature_name"]] += item["rows"]
        by_year[str(item["event_year"])] += item["rows"]
    manifest = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "source_db": "mixed: expanded parquet plus generated equal_levels",
        "output": str(research_dir),
        "rows": int(sum(item["rows"] for item in files)),
        "files": len(files),
        "partitioning": ["feature_name", "event_year"],
        "by_feature": dict(sorted(by_feature.items())),
        "by_year": dict(sorted(by_year.items())),
        "parquet_files": files,
        "note": (
            "Shareable research_events parquet snapshot. equal_levels may be "
            "generated from expanded swing parquet on this machine. When an "
            "R2 download summary is available, stale local-only partitions are "
            "excluded from this manifest."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _write_doc(path: Path, *, args: argparse.Namespace, events: pd.DataFrame, features: pd.DataFrame, manifest: dict[str, Any]) -> None:
    count_rows = []
    if not events.empty:
        counts = events.groupby(["primary_symbol", "event_type", "side"]).size().reset_index(name="rows")
        for _, row in counts.iterrows():
            count_rows.append(
                [
                    f"`{row['primary_symbol']}`",
                    f"`{row['event_type']}`",
                    f"`{row['side']}`",
                    f"{int(row['rows']):,}",
                ]
            )
    text = [
        "# Expanded Equal Levels Build",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This builds equal-high/equal-low events from expanded swing-pivot parquet without importing the full expanded lake into SQLite.",
        "",
        f"- Symbols: `{', '.join(args.symbols)}`",
        f"- Scope: `{args.scope_note}`",
        f"- Events with outcomes: `{len(events):,}`",
        f"- Feature matrix: `{args.feature_output}`",
        f"- Feature rows/columns: `{len(features):,}` x `{len(features.columns):,}`",
        f"- Research manifest rows after merge: `{manifest['rows']:,}`",
        "",
        "## Counts",
        "",
        _md_table(["Symbol", "Mode", "Side", "Rows"], count_rows[:80]),
        "",
        "## Caveat",
        "",
        "- Current equal-level tolerances are absolute price points inherited from the index workflow.",
        "- This build intentionally defaults to equity-index symbols only.",
        "- FX, energy, grains, and rates need an asset-normalized tolerance model before broad equal-level expansion.",
        "- The manifest is filtered to the latest R2 artifact download plus generated equal-level partitions, so stale local-only parquet does not inflate shared counts.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text), encoding="utf-8")


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_None._"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swing-features", type=Path, default=DEFAULT_SWING_FEATURES)
    parser.add_argument("--feature-output", type=Path, default=DEFAULT_FEATURE_OUTPUT)
    parser.add_argument("--research-output", type=Path, default=DEFAULT_RESEARCH_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--remote-download-summary", type=Path, default=DEFAULT_REMOTE_DOWNLOAD_SUMMARY)
    parser.add_argument("--symbols", type=_parse_csv, default=list(DEFAULT_SYMBOLS))
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Refresh manifest/doc from existing eql.parquet and equal_levels partitions without recomputing outcomes.",
    )
    parser.add_argument("--no-xd", action="store_true")
    parser.add_argument(
        "--scope-note",
        default="equity index symbols only; absolute point tolerances are not asset-normalized",
    )
    args = parser.parse_args()

    remote_paths = _remote_research_event_paths(args.remote_download_summary)
    if args.manifest_only:
        if not args.feature_output.exists():
            raise FileNotFoundError(args.feature_output)
        features = pd.read_parquet(args.feature_output)
        equal_files = _existing_equal_research_files(args.research_output)
        include_paths = set(remote_paths)
        include_paths.update(str(item["path"]) for item in equal_files)
        manifest = _refresh_research_manifest(args.manifest, args.research_output, include_paths=include_paths or None)
        events = features[["primary_symbol", "event_type", "side"]].copy()
        _write_doc(args.doc, args=args, events=events, features=features, manifest=manifest)
        print(f"loaded existing {args.feature_output}: {len(features):,} rows x {len(features.columns):,} cols")
        print(f"loaded {len(equal_files):,} equal_levels research_events partitions")
        print(f"remote research_events filter paths: {len(remote_paths):,}")
        print(f"wrote {args.manifest}: {manifest['rows']:,} rows, {manifest['files']:,} files")
        print(f"wrote {args.doc}")
        return 0

    print(f"loading swing features: {args.swing_features}")
    swing = _load_swing_features_fast(args.swing_features, args.symbols)
    print(f"loaded {len(swing):,} swing rows for {len(args.symbols)} symbols")
    events = build_events(swing, args.symbols)
    print(f"detected {len(events):,} equal-level events before outcomes")
    events = compute_outcomes(events)
    print(f"kept {len(events):,} equal-level events with outcomes")
    features = build_feature_matrix(events, include_xd=not args.no_xd)
    args.feature_output.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(args.feature_output, index=False)
    equal_files = _write_research_events(events, args.research_output)
    include_paths = set(remote_paths)
    include_paths.update(str(item["path"]) for item in equal_files)
    manifest = _refresh_research_manifest(args.manifest, args.research_output, include_paths=include_paths or None)
    _write_doc(args.doc, args=args, events=events, features=features, manifest=manifest)
    print(f"wrote {args.feature_output}: {len(features):,} rows x {len(features.columns):,} cols")
    print(f"wrote equal_levels research_events partitions under {args.research_output}")
    print(f"remote research_events filter paths: {len(remote_paths):,}")
    print(f"wrote {args.manifest}: {manifest['rows']:,} rows, {manifest['files']:,} files")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
