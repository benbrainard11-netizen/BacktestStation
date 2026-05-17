"""Build overnight database hardening reports.

This script does not train models. It turns the current research lake into
operator-readable reports:

- master database overview
- ML feature/label safety audit
- universal level-reaction scoreboard
- 2025 regime diagnostic

The outputs are small JSON/CSV/Markdown files intended for Git docs and R2.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import pyarrow.parquet as pq
except Exception:  # pragma: no cover - fallback exists for thin envs.
    pq = None

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DATA_ML = ROOT / "data" / "ml"
FEATURES_DIR = DATA_ML / "features"
ANCHORS_DIR = DATA_ML / "anchors"
LEVELS_DIR = DATA_ML / "levels"
CATALOG_DIR = DATA_ML / "catalog"
DOCS_DIR = ROOT / "docs"

ML_CATALOG = CATALOG_DIR / "ml_dataset_catalog.json"
FEATURE_DICTIONARY = CATALOG_DIR / "feature_dictionary.json"
ASSET_MANIFEST = CATALOG_DIR / "asset_universe_manifest.json"
R2_RUN_LOG = DATA_ML / "logs" / "r2_artifact_upload_runs.json"
ALL_LEVELS = LEVELS_DIR / "all_level_reactions.parquet"
LEVEL_LEADERBOARD = LEVELS_DIR / "level_reaction_leaderboard.csv"

DEFAULT_OVERVIEW_JSON = CATALOG_DIR / "database_overview.json"
DEFAULT_SAFETY_JSON = CATALOG_DIR / "ml_safety_audit.json"
DEFAULT_SCOREBOARD_CSV = LEVELS_DIR / "level_reaction_scoreboard.csv"
DEFAULT_SCOREBOARD_JSON = LEVELS_DIR / "level_reaction_scoreboard.json"
DEFAULT_REGIME_JSON = CATALOG_DIR / "regime_2025_diagnostic.json"

DEFAULT_OVERVIEW_DOC = DOCS_DIR / "ML_DATABASE_OVERVIEW.md"
DEFAULT_SAFETY_DOC = DOCS_DIR / "ML_SAFETY_AUDIT.md"
DEFAULT_SCOREBOARD_DOC = DOCS_DIR / "ML_LEVEL_REACTION_SCOREBOARD.md"
DEFAULT_REGIME_DOC = DOCS_DIR / "ML_2025_REGIME_DIAGNOSTIC.md"

FORBIDDEN_MODEL_PREFIXES = ("oc.", "label.", "lr.")
SAFE_CONTEXT_PREFIXES = (
    "asof.",
    "anchor.",
    "ts.",
    "xctx.",
    "xd.",
    "gapctx.",
    "fvggeom.",
    "obgeom.",
    "liqgeom.",
    "regime.",
    "macroctx.",
    "level.",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_json_list(path: Path) -> list[Any]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)):
            return None
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return str(value)


def _fmt_int(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{int(value):,}"


def _fmt_bytes(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def _fmt_pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{100.0 * float(value):.1f}%"


def _fmt_float(value: Any, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.3f}{suffix}"


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_None._"
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def _parquet_meta(path: Path) -> tuple[int | None, list[str]]:
    if pq is not None:
        try:
            pf = pq.ParquetFile(path)
            return int(pf.metadata.num_rows), list(pf.schema.names)
        except Exception:
            pass
    try:
        df = pd.read_parquet(path)
        return int(len(df)), list(df.columns)
    except Exception:
        return None, []


def _file_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "bytes": int(stat.st_size),
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def _dataset_record(path: Path, dataset_type: str) -> dict[str, Any]:
    rows, columns = _parquet_meta(path)
    prefixes = Counter(_column_prefix(c) for c in columns)
    return {
        **_file_record(path),
        "dataset_type": dataset_type,
        "stem": path.stem,
        "rows": rows,
        "columns": len(columns),
        "prefix_counts": dict(sorted(prefixes.items())),
        "forbidden_column_count": sum(1 for c in columns if c.startswith(FORBIDDEN_MODEL_PREFIXES)),
        "forbidden_column_examples": [c for c in columns if c.startswith(FORBIDDEN_MODEL_PREFIXES)][:20],
    }


def _column_prefix(col: str) -> str:
    if "." not in col:
        return "(root)"
    return col.split(".", 1)[0] + "."


def build_database_overview(args: argparse.Namespace) -> dict[str, Any]:
    catalog = _load_json(ML_CATALOG)
    dictionary = _load_json(FEATURE_DICTIONARY)
    manifest = _load_json(ASSET_MANIFEST)
    r2_runs = _load_json_list(R2_RUN_LOG)

    features = [_dataset_record(p, "phase1_feature_matrix") for p in sorted(FEATURES_DIR.glob("*.parquet"))]
    anchors = [_dataset_record(p, "snapshot_or_model_artifact") for p in sorted(ANCHORS_DIR.glob("*.parquet"))]
    levels = [_dataset_record(p, "level_reaction_artifact") for p in sorted(LEVELS_DIR.glob("*.parquet"))]

    payload = {
        "generated_utc": _now(),
        "builder": "backend/scripts/ml/build_overnight_database_reports.py",
        "catalog": {
            "database_events": catalog.get("database", {}).get("total_events") or catalog.get("database_events"),
            "feature_matrix_count": catalog.get("feature_matrix_count") or len(features),
            "anchor_artifact_count": catalog.get("anchor_artifact_count"),
            "generated_utc": catalog.get("generated_utc"),
        },
        "asset_manifest": {
            "universe_id": manifest.get("universe_id"),
            "dataset_fingerprint": manifest.get("dataset_fingerprint"),
            "active_symbols": manifest.get("active_universe", {}).get("symbols", []),
            "research_events": manifest.get("research_events", {}).get("total_events"),
            "generated_utc": manifest.get("generated_utc"),
            "warnings": manifest.get("warnings", []),
        },
        "r2_last_run": r2_runs[-1] if r2_runs else None,
        "feature_matrices": features,
        "anchor_artifacts": anchors,
        "level_artifacts": levels,
        "column_families": dictionary.get("column_families", {}),
        "totals": {
            "feature_matrix_rows": int(sum((d.get("rows") or 0) for d in features)),
            "feature_matrix_bytes": int(sum(d["bytes"] for d in features)),
            "anchor_artifact_bytes": int(sum(d["bytes"] for d in anchors)),
            "level_artifact_bytes": int(sum(d["bytes"] for d in levels)),
        },
    }
    _write_json(args.overview_json, payload)
    _write_database_overview_doc(args.overview_doc, payload)
    return payload


def _write_database_overview_doc(path: Path, payload: dict[str, Any]) -> None:
    feature_rows = [
        [
            f"`{d['stem']}`",
            _fmt_int(d["rows"]),
            _fmt_int(d["columns"]),
            _fmt_bytes(d["bytes"]),
            _fmt_int(d["forbidden_column_count"]),
        ]
        for d in sorted(payload["feature_matrices"], key=lambda x: str(x["stem"]))
    ]
    level_rows = [
        [
            f"`{d['stem']}`",
            _fmt_int(d["rows"]),
            _fmt_int(d["columns"]),
            _fmt_bytes(d["bytes"]),
        ]
        for d in sorted(payload["level_artifacts"], key=lambda x: str(x["stem"]))
    ]
    last_r2 = payload.get("r2_last_run") or {}
    lines = [
        "# ML Database Overview",
        "",
        f"_Generated `{payload['generated_utc']}`._",
        "",
        "This is the high-level map of the current BacktestStation research database.",
        "",
        "## Identity",
        "",
        _md_table(
            ["Field", "Value"],
            [
                ["Universe id", f"`{payload['asset_manifest'].get('universe_id')}`"],
                ["Dataset fingerprint", f"`{payload['asset_manifest'].get('dataset_fingerprint')}`"],
                ["Active symbols", ", ".join(f"`{s}`" for s in payload["asset_manifest"].get("active_symbols", []))],
                ["Research events", _fmt_int(payload["asset_manifest"].get("research_events") or payload["catalog"].get("database_events"))],
                ["Feature matrices", _fmt_int(payload["catalog"].get("feature_matrix_count"))],
                ["Anchor/model artifacts", _fmt_int(payload["catalog"].get("anchor_artifact_count"))],
            ],
        ),
        "",
        "## R2 Last Publish",
        "",
        _md_table(
            ["Field", "Value"],
            [
                ["Timestamp", f"`{last_r2.get('ts')}`"],
                ["Profile", f"`{last_r2.get('profile')}`"],
                ["Uploaded", _fmt_int(last_r2.get("uploaded"))],
                ["Skipped existing", _fmt_int(last_r2.get("skipped_existing"))],
                ["Bytes uploaded", _fmt_bytes(last_r2.get("bytes_uploaded"))],
                ["Errors", _fmt_int(len(last_r2.get("errors", [])))],
            ],
        ),
        "",
        "## Phase 1 Feature Matrices",
        "",
        _md_table(["Matrix", "Rows", "Columns", "Size", "Outcome/label cols"], feature_rows),
        "",
        "## Universal Level Artifacts",
        "",
        _md_table(["Artifact", "Rows", "Columns", "Size"], level_rows),
        "",
        "## Read This Correctly",
        "",
        "- Phase 1 feature matrices intentionally contain `oc.*` outcome columns for research, but those are not safe model inputs.",
        "- Snapshot matrices should use schema-declared feature columns only.",
        "- Level tables use `level.*` as known-at-creation descriptors and `lr.*` as future reaction labels.",
        "- R2 is the database transport; Git is for code, docs, and small metadata.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_safety_audit(args: argparse.Namespace) -> dict[str, Any]:
    datasets: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for path in sorted(FEATURES_DIR.glob("*.parquet")):
        rows, columns = _parquet_meta(path)
        forbidden = [c for c in columns if c.startswith(FORBIDDEN_MODEL_PREFIXES)]
        datasets.append(
            {
                "name": path.stem,
                "type": "phase1_feature_matrix",
                "rows": rows,
                "columns": len(columns),
                "safe_usage": "Use event-time columns only; exclude oc.* unless selecting labels.",
                "forbidden_columns": len(forbidden),
                "forbidden_examples": forbidden[:20],
            }
        )
        if forbidden:
            warnings.append(
                {
                    "dataset": path.stem,
                    "severity": "expected",
                    "message": "Phase 1 matrix contains outcome columns; exclude these from model features.",
                    "examples": forbidden[:10],
                }
            )

    for path in sorted(ANCHORS_DIR.glob("*.schema.json")):
        schema = _load_json(path)
        feature_cols = list(schema.get("feature_columns", []))
        label_cols = list(schema.get("label_columns", []))
        feature_forbidden = [c for c in feature_cols if c.startswith(FORBIDDEN_MODEL_PREFIXES)]
        overlap = sorted(set(feature_cols) & set(label_cols))
        record = {
            "name": path.name.replace(".schema.json", ""),
            "type": "snapshot_schema",
            "rows": schema.get("rows"),
            "feature_columns": len(feature_cols),
            "label_columns": len(label_cols),
            "feature_forbidden_columns": len(feature_forbidden),
            "feature_forbidden_examples": feature_forbidden[:20],
            "feature_label_overlap": len(overlap),
            "feature_label_overlap_examples": overlap[:20],
        }
        datasets.append(record)
        if feature_forbidden:
            issues.append(
                {
                    "dataset": record["name"],
                    "severity": "high",
                    "message": "Snapshot schema feature_columns includes forbidden future/label prefixes.",
                    "examples": feature_forbidden[:20],
                }
            )
        if overlap:
            issues.append(
                {
                    "dataset": record["name"],
                    "severity": "high",
                    "message": "Snapshot schema has columns listed as both features and labels.",
                    "examples": overlap[:20],
                }
            )

    for path in sorted(LEVELS_DIR.glob("*level_reactions.schema.json")):
        schema = _load_json(path)
        columns = list(schema.get("columns", []))
        lr_cols = [c for c in columns if c.startswith("lr.")]
        level_cols = [c for c in columns if c.startswith("level.")]
        datasets.append(
            {
                "name": path.name.replace(".schema.json", ""),
                "type": "level_reaction_schema",
                "rows": schema.get("rows"),
                "level_columns": len(level_cols),
                "label_columns": len(lr_cols),
                "safe_usage": "Use level.* for descriptors; use lr.* only as targets/outcomes.",
            }
        )

    payload = {
        "generated_utc": _now(),
        "builder": "backend/scripts/ml/build_overnight_database_reports.py",
        "status": "PASS" if not issues else "FAIL",
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "forbidden_model_prefixes": list(FORBIDDEN_MODEL_PREFIXES),
        "safe_context_prefixes": list(SAFE_CONTEXT_PREFIXES),
        "datasets": datasets,
        "issues": issues,
        "warnings": warnings,
    }
    _write_json(args.safety_json, payload)
    _write_safety_doc(args.safety_doc, payload)
    return payload


def _write_safety_doc(path: Path, payload: dict[str, Any]) -> None:
    issue_rows = [
        [i["severity"], f"`{i['dataset']}`", i["message"], ", ".join(f"`{x}`" for x in i.get("examples", [])[:5])]
        for i in payload["issues"]
    ]
    warning_rows = [
        [w["severity"], f"`{w['dataset']}`", w["message"], ", ".join(f"`{x}`" for x in w.get("examples", [])[:5])]
        for w in payload["warnings"][:80]
    ]
    snapshot_rows = [
        [
            f"`{d['name']}`",
            _fmt_int(d.get("rows")),
            _fmt_int(d.get("feature_columns")),
            _fmt_int(d.get("label_columns")),
            _fmt_int(d.get("feature_forbidden_columns", 0)),
            _fmt_int(d.get("feature_label_overlap", 0)),
        ]
        for d in payload["datasets"]
        if d["type"] == "snapshot_schema"
    ]
    lines = [
        "# ML Safety Audit",
        "",
        f"_Generated `{payload['generated_utc']}`._",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Rule",
        "",
        "- `oc.*`, `label.*`, and `lr.*` are future/outcome columns.",
        "- They can be used as target labels or diagnostics.",
        "- They must not be fed as normal model input features.",
        "",
        "## Snapshot Schema Checks",
        "",
        _md_table(["Schema", "Rows", "Features", "Labels", "Forbidden features", "Feature/label overlap"], snapshot_rows),
        "",
        "## Issues",
        "",
        _md_table(["Severity", "Dataset", "Message", "Examples"], issue_rows),
        "",
        "## Expected Warnings",
        "",
        "Phase 1 matrices store outcomes beside event-time fields. That is useful for research but unsafe unless model scripts exclude them.",
        "",
        _md_table(["Severity", "Dataset", "Message", "Examples"], warning_rows),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_level_scoreboard(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not LEVEL_LEADERBOARD.exists():
        raise FileNotFoundError(LEVEL_LEADERBOARD)
    leaderboard = pd.read_csv(LEVEL_LEADERBOARD)
    min_rows = int(args.min_scoreboard_rows)
    usable = leaderboard[leaderboard["rows_with_horizon"].ge(min_rows)].copy()
    usable["behavior_edge"] = (usable["reject_rate"] - usable["break_rate"]).abs()
    usable["touch_quality"] = usable["meaningful_rate"].fillna(0) * usable["behavior_edge"].fillna(0)

    cols = [
        "segment_level",
        "level_kind",
        "level_subtype",
        "level_side",
        "horizon",
        "rows_with_horizon",
        "dominant_behavior",
        "meaningful_rate",
        "reject_rate",
        "break_rate",
        "clean_through_rate",
        "avg_reaction_away_x_size",
        "clean_signal_score",
        "tier",
        "action_hint",
    ]
    ranked = usable.sort_values("clean_signal_score", ascending=False)[cols].reset_index(drop=True)
    ranked.insert(0, "scoreboard_rank", np.arange(1, len(ranked) + 1))
    args.scoreboard_csv.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(args.scoreboard_csv, index=False)

    payload = {
        "generated_utc": _now(),
        "builder": "backend/scripts/ml/build_overnight_database_reports.py",
        "source": str(LEVEL_LEADERBOARD),
        "min_rows": min_rows,
        "rows": int(len(ranked)),
        "top_overall": ranked.head(30).to_dict(orient="records"),
        "top_rejection": ranked[ranked["dominant_behavior"].eq("rejection")].head(30).to_dict(orient="records"),
        "top_break": ranked[ranked["dominant_behavior"].eq("break")].head(30).to_dict(orient="records"),
        "by_kind": _kind_score_summary(ranked),
    }
    _write_json(args.scoreboard_json, payload)
    _write_scoreboard_doc(args.scoreboard_doc, payload)
    return ranked, payload


def _kind_score_summary(ranked: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kind, sub in ranked.groupby("level_kind", dropna=False):
        rows.append(
            {
                "level_kind": str(kind),
                "rows": int(len(sub)),
                "best_score": float(sub["clean_signal_score"].max()),
                "best_horizon": str(sub.sort_values("clean_signal_score", ascending=False).iloc[0]["horizon"]),
                "best_behavior": str(sub.sort_values("clean_signal_score", ascending=False).iloc[0]["dominant_behavior"]),
                "median_score": float(sub["clean_signal_score"].median()),
            }
        )
    return sorted(rows, key=lambda r: r["best_score"], reverse=True)


def _score_rows(rows: list[dict[str, Any]], limit: int = 20) -> list[list[Any]]:
    out = []
    for r in rows[:limit]:
        out.append(
            [
                _fmt_int(r.get("scoreboard_rank")),
                f"`{r.get('level_kind')}`",
                "-" if pd.isna(r.get("level_subtype")) else f"`{r.get('level_subtype')}`",
                "-" if pd.isna(r.get("level_side")) else f"`{r.get('level_side')}`",
                f"`{r.get('horizon')}`",
                _fmt_int(r.get("rows_with_horizon")),
                f"`{r.get('dominant_behavior')}`",
                _fmt_pct(r.get("meaningful_rate")),
                _fmt_pct(r.get("reject_rate")),
                _fmt_pct(r.get("break_rate")),
                _fmt_float(r.get("clean_signal_score")),
                f"`{r.get('action_hint')}`",
            ]
        )
    return out


def _write_scoreboard_doc(path: Path, payload: dict[str, Any]) -> None:
    kind_rows = [
        [
            f"`{r['level_kind']}`",
            _fmt_float(r["best_score"]),
            f"`{r['best_horizon']}`",
            f"`{r['best_behavior']}`",
            _fmt_float(r["median_score"]),
        ]
        for r in payload["by_kind"]
    ]
    headers = ["Rank", "Kind", "Subtype", "Side", "Horizon", "Rows", "Dominant", "Touch", "Reject", "Break", "Score", "Hint"]
    lines = [
        "# Level Reaction Scoreboard",
        "",
        f"_Generated `{payload['generated_utc']}`._",
        "",
        "This is the plain-English ranking layer on top of `level_reaction_leaderboard.csv`.",
        "It ranks behavior clarity, not trade PnL.",
        "",
        f"- Source: `{payload['source']}`",
        f"- Minimum rows: `{payload['min_rows']:,}`",
        f"- Ranked rows: `{payload['rows']:,}`",
        "",
        "## Best Families",
        "",
        _md_table(["Kind", "Best score", "Best horizon", "Best behavior", "Median score"], kind_rows),
        "",
        "## Top Overall",
        "",
        _md_table(headers, _score_rows(payload["top_overall"])),
        "",
        "## Top Rejection",
        "",
        _md_table(headers, _score_rows(payload["top_rejection"])),
        "",
        "## Top Break / Continuation",
        "",
        _md_table(headers, _score_rows(payload["top_break"])),
        "",
        "## Practical Read",
        "",
        "- High `break` rows mean the level is usually not support/resistance; it is often a draw-through or continuation area.",
        "- High `rejection` rows mean the level more often acts as support/resistance.",
        "- `full_horizon` can overstate usefulness because it gives price more time; short horizons are cleaner for execution research.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_2025_regime_diagnostic(args: argparse.Namespace) -> dict[str, Any]:
    if not ALL_LEVELS.exists():
        raise FileNotFoundError(ALL_LEVELS)
    needed = [
        "level.kind",
        "level.subtype",
        "level.side",
        "source.year",
        "lr.next_3_bars.meaningful_touch",
        "lr.next_3_bars.directional_rejection",
        "lr.next_3_bars.directional_break_acceptance",
        "lr.next_5_bars.meaningful_touch",
        "lr.next_5_bars.directional_rejection",
        "lr.next_5_bars.directional_break_acceptance",
        "lr.next_60m.meaningful_touch",
        "lr.next_60m.directional_rejection",
        "lr.next_60m.directional_break_acceptance",
        "lr.full_horizon.meaningful_touch",
        "lr.full_horizon.directional_rejection",
        "lr.full_horizon.directional_break_acceptance",
    ]
    meta_rows, all_cols = _parquet_meta(ALL_LEVELS)
    cols = [c for c in needed if c in all_cols]
    levels = pd.read_parquet(ALL_LEVELS, columns=cols)
    levels["source.year"] = pd.to_numeric(levels["source.year"], errors="coerce").astype("Int64")
    levels = levels[levels["source.year"].isin([2023, 2024, 2025])].copy()

    rows: list[dict[str, Any]] = []
    horizon_map = {
        "opening_gap": "next_60m",
        "equal_levels": "next_5_bars",
    }
    for (kind, subtype, side), sub in levels.groupby(["level.kind", "level.subtype", "level.side"], dropna=False):
        horizon = horizon_map.get(str(kind), "next_3_bars")
        touch_col = f"lr.{horizon}.meaningful_touch"
        reject_col = f"lr.{horizon}.directional_rejection"
        break_col = f"lr.{horizon}.directional_break_acceptance"
        if touch_col not in sub.columns:
            continue
        for year, y in sub.groupby("source.year", dropna=False):
            rows.append(
                {
                    "level_kind": str(kind),
                    "level_subtype": str(subtype),
                    "level_side": str(side),
                    "year": int(year),
                    "horizon": horizon,
                    "rows": int(len(y)),
                    "meaningful_rate": _bool_rate(y[touch_col]),
                    "reject_rate": _bool_rate(y[reject_col]) if reject_col in y.columns else np.nan,
                    "break_rate": _bool_rate(y[break_col]) if break_col in y.columns else np.nan,
                }
            )
    yearly = pd.DataFrame(rows)
    drift = _regime_drift(yearly)
    feature_mix = _feature_year_mix()

    payload = {
        "generated_utc": _now(),
        "builder": "backend/scripts/ml/build_overnight_database_reports.py",
        "source": str(ALL_LEVELS),
        "rows_2023_2025": int(len(levels)),
        "yearly_rows": yearly.to_dict(orient="records"),
        "largest_2025_drift": drift.head(50).to_dict(orient="records"),
        "feature_year_mix": feature_mix,
        "interpretation": _regime_interpretation(drift),
    }
    _write_json(args.regime_json, payload)
    _write_regime_doc(args.regime_doc, payload)
    return payload


def _bool_rate(series: pd.Series) -> float:
    if series.empty:
        return float("nan")
    return float(series.astype("boolean").fillna(False).mean())


def _regime_drift(yearly: pd.DataFrame) -> pd.DataFrame:
    if yearly.empty:
        return pd.DataFrame()
    keys = ["level_kind", "level_subtype", "level_side", "horizon"]
    rows: list[dict[str, Any]] = []
    for key, sub in yearly.groupby(keys, dropna=False):
        prior = sub[sub["year"].isin([2023, 2024])]
        y2025 = sub[sub["year"].eq(2025)]
        if prior.empty or y2025.empty:
            continue
        prior_rows = int(prior["rows"].sum())
        rows_2025 = int(y2025["rows"].sum())
        if prior_rows < 100 or rows_2025 < 50:
            continue
        prior_touch = np.average(prior["meaningful_rate"], weights=prior["rows"])
        prior_reject = np.average(prior["reject_rate"], weights=prior["rows"])
        prior_break = np.average(prior["break_rate"], weights=prior["rows"])
        row_2025 = y2025.iloc[0]
        touch_delta = float(row_2025["meaningful_rate"] - prior_touch)
        reject_delta = float(row_2025["reject_rate"] - prior_reject)
        break_delta = float(row_2025["break_rate"] - prior_break)
        rows.append(
            {
                "level_kind": key[0],
                "level_subtype": key[1],
                "level_side": key[2],
                "horizon": key[3],
                "prior_rows_2023_2024": prior_rows,
                "rows_2025": rows_2025,
                "prior_touch_rate": float(prior_touch),
                "touch_rate_2025": float(row_2025["meaningful_rate"]),
                "touch_delta_2025": touch_delta,
                "prior_reject_rate": float(prior_reject),
                "reject_rate_2025": float(row_2025["reject_rate"]),
                "reject_delta_2025": reject_delta,
                "prior_break_rate": float(prior_break),
                "break_rate_2025": float(row_2025["break_rate"]),
                "break_delta_2025": break_delta,
                "max_abs_delta": max(abs(touch_delta), abs(reject_delta), abs(break_delta)),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("max_abs_delta", ascending=False).reset_index(drop=True)


def _feature_year_mix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(FEATURES_DIR.glob("*.parquet")):
        _, cols = _parquet_meta(path)
        if "year" not in cols:
            continue
        try:
            df = pd.read_parquet(path, columns=["year"])
        except Exception:
            continue
        counts = df["year"].value_counts(dropna=False).sort_index()
        total = int(counts.sum())
        rows.append(
            {
                "matrix": path.stem,
                "rows": total,
                "rows_2023": int(counts.get(2023, 0)),
                "rows_2024": int(counts.get(2024, 0)),
                "rows_2025": int(counts.get(2025, 0)),
                "share_2025": float(counts.get(2025, 0) / total) if total else None,
            }
        )
    return sorted(rows, key=lambda r: r["rows_2025"], reverse=True)


def _regime_interpretation(drift: pd.DataFrame) -> list[str]:
    if drift.empty:
        return ["No 2025 drift rows met the sample thresholds."]
    top = drift.head(10)
    kinds = Counter(str(x) for x in top["level_kind"])
    lines = [
        "This diagnostic compares 2025 level behavior against weighted 2023-2024 behavior.",
        "Large deltas mean a level family changed behavior; they do not prove a trading edge by themselves.",
        "Most affected families in the top drift rows: "
        + ", ".join(f"{k} ({v})" for k, v in kinds.most_common()),
    ]
    return lines


def _write_regime_doc(path: Path, payload: dict[str, Any]) -> None:
    drift_rows = []
    for r in payload["largest_2025_drift"][:30]:
        drift_rows.append(
            [
                f"`{r['level_kind']}`",
                f"`{r['level_subtype']}`",
                f"`{r['level_side']}`",
                f"`{r['horizon']}`",
                _fmt_int(r["prior_rows_2023_2024"]),
                _fmt_int(r["rows_2025"]),
                _fmt_pct(r["prior_touch_rate"]),
                _fmt_pct(r["touch_rate_2025"]),
                _fmt_pct(r["touch_delta_2025"]),
                _fmt_pct(r["reject_delta_2025"]),
                _fmt_pct(r["break_delta_2025"]),
            ]
        )
    mix_rows = [
        [
            f"`{r['matrix']}`",
            _fmt_int(r["rows"]),
            _fmt_int(r["rows_2023"]),
            _fmt_int(r["rows_2024"]),
            _fmt_int(r["rows_2025"]),
            _fmt_pct(r["share_2025"]),
        ]
        for r in payload["feature_year_mix"]
    ]
    lines = [
        "# 2025 Regime Diagnostic",
        "",
        f"_Generated `{payload['generated_utc']}`._",
        "",
        "This compares 2025 level behavior against 2023-2024 behavior.",
        "",
        "## Interpretation",
        "",
        *[f"- {line}" for line in payload["interpretation"]],
        "",
        "## Largest Level-Reaction Drifts",
        "",
        _md_table(
            [
                "Kind",
                "Subtype",
                "Side",
                "Horizon",
                "Prior rows",
                "2025 rows",
                "Prior touch",
                "2025 touch",
                "Touch delta",
                "Reject delta",
                "Break delta",
            ],
            drift_rows,
        ),
        "",
        "## Feature Matrix Year Mix",
        "",
        _md_table(["Matrix", "Rows", "2023", "2024", "2025", "2025 share"], mix_rows),
        "",
        "## How To Use",
        "",
        "- If a model works before 2025 and weakens in 2025, check whether its anchor family appears in the drift table.",
        "- A large positive break delta means price accepted through that level more often in 2025.",
        "- A large negative rejection delta means support/resistance behavior weakened in 2025.",
        "- This is a dataset diagnostic, not a strategy report.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overview-json", type=Path, default=DEFAULT_OVERVIEW_JSON)
    parser.add_argument("--safety-json", type=Path, default=DEFAULT_SAFETY_JSON)
    parser.add_argument("--scoreboard-csv", type=Path, default=DEFAULT_SCOREBOARD_CSV)
    parser.add_argument("--scoreboard-json", type=Path, default=DEFAULT_SCOREBOARD_JSON)
    parser.add_argument("--regime-json", type=Path, default=DEFAULT_REGIME_JSON)
    parser.add_argument("--overview-doc", type=Path, default=DEFAULT_OVERVIEW_DOC)
    parser.add_argument("--safety-doc", type=Path, default=DEFAULT_SAFETY_DOC)
    parser.add_argument("--scoreboard-doc", type=Path, default=DEFAULT_SCOREBOARD_DOC)
    parser.add_argument("--regime-doc", type=Path, default=DEFAULT_REGIME_DOC)
    parser.add_argument("--min-scoreboard-rows", type=int, default=500)
    args = parser.parse_args()

    overview = build_database_overview(args)
    safety = build_safety_audit(args)
    scoreboard, _score_payload = build_level_scoreboard(args)
    regime = build_2025_regime_diagnostic(args)

    print(f"wrote {args.overview_json}")
    print(f"wrote {args.overview_doc}")
    print(f"wrote {args.safety_json}: status={safety['status']} issues={safety['issue_count']}")
    print(f"wrote {args.safety_doc}")
    print(f"wrote {args.scoreboard_csv}: {len(scoreboard):,} rows")
    print(f"wrote {args.scoreboard_json}")
    print(f"wrote {args.scoreboard_doc}")
    print(f"wrote {args.regime_json}: {len(regime['largest_2025_drift']):,} drift rows")
    print(f"wrote {args.regime_doc}")
    print(
        "overview="
        + f"{len(overview['feature_matrices'])} feature matrices, "
        + f"{len(overview['level_artifacts'])} level artifacts"
    )
    return 0 if safety["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
