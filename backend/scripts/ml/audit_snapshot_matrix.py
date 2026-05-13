"""Audit an ML snapshot matrix for basic zero-look-ahead invariants."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from snapshot_feature_registry import allowed_snapshots_for_column  # noqa: E402

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DEFAULT_MATRIX = ROOT / "data" / "ml" / "anchors" / "smt_previous_day_snapshots.parquet"
DEFAULT_SCHEMA = ROOT / "data" / "ml" / "anchors" / "smt_previous_day_snapshots.schema.json"
DEFAULT_DOC = ROOT / "docs" / "ML_SNAPSHOT_AUDIT.md"


def _non_null_count(s: pd.Series) -> int:
    return int(s.notna().sum())


def _write_doc(
    path: Path,
    matrix_path: Path,
    schema_path: Path,
    summary: dict,
    issues: list[str],
    warnings: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ML snapshot matrix audit\n\n")
        f.write(f"_Generated `{datetime.now(UTC).isoformat()}`._\n\n")
        f.write(f"- Matrix: `{matrix_path}`\n")
        f.write(f"- Schema: `{schema_path}`\n")
        f.write(f"- Rows: `{summary['rows']}`\n")
        f.write(f"- Columns: `{summary['cols']}`\n")
        f.write(f"- Snapshots: `{', '.join(summary['snapshots'])}`\n\n")
        f.write("## Checks\n\n")
        for name, value in summary["checks"].items():
            f.write(f"- `{name}`: {value}\n")
        if issues:
            f.write("\n## Issues\n\n")
            for issue in issues:
                f.write(f"- {issue}\n")
        else:
            f.write("\n## Issues\n\nNone.\n")
        if warnings:
            f.write("\n## Warnings\n\n")
            for warning in warnings:
                f.write(f"- {warning}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()

    df = pd.read_parquet(args.matrix)
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    issues: list[str] = []
    warnings: list[str] = []
    checks: dict[str, str] = {}

    required = {
        "anchor.event_id", "asof.snapshot", "asof.snapshot_ts",
        "asof.feature_cutoff_ts", "asof.label_start_ts", "asof.label_end_ts",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        issues.append(f"missing required columns: {', '.join(missing)}")

    if not missing:
        for col in ("asof.snapshot_ts", "asof.feature_cutoff_ts",
                    "asof.label_start_ts", "asof.label_end_ts"):
            df[col] = pd.to_datetime(df[col], utc=True)

        bad_cutoff = df["asof.feature_cutoff_ts"] > df["asof.snapshot_ts"]
        checks["feature_cutoff_lte_snapshot"] = f"{int((~bad_cutoff).sum())}/{len(df)}"
        if bad_cutoff.any():
            issues.append(
                f"{int(bad_cutoff.sum())} rows have feature_cutoff_ts after snapshot_ts"
            )

        bad_label = df["asof.feature_cutoff_ts"] >= df["asof.label_start_ts"]
        checks["feature_cutoff_before_label_start"] = f"{int((~bad_label).sum())}/{len(df)}"
        if bad_label.any():
            issues.append(
                f"{int(bad_label.sum())} rows have feature_cutoff_ts >= label_start_ts"
            )

        duplicated = df.duplicated(["anchor.event_id", "asof.snapshot"])
        checks["unique_anchor_snapshot"] = f"{int((~duplicated).sum())}/{len(df)}"
        if duplicated.any():
            issues.append(
                f"{int(duplicated.sum())} duplicate (anchor.event_id, asof.snapshot) rows"
            )

    bad_prefixes = [
        c for c in df.columns
        if c.startswith("oc.") or c.startswith("ed.") or c.startswith("ctx.")
    ]
    checks["no_raw_oc_ed_ctx_columns"] = "OK" if not bad_prefixes else "FAIL"
    if bad_prefixes:
        issues.append(
            "raw Phase 1 columns leaked into snapshot matrix: "
            + ", ".join(bad_prefixes[:20])
        )

    feature_cols = schema.get("feature_columns", [])
    for col in feature_cols:
        allowed = allowed_snapshots_for_column(col)
        if allowed is None:
            warnings.append(f"feature column has no registry rule: {col}")
            continue
        disallowed_snapshots = sorted(set(df["asof.snapshot"].unique()) - set(allowed))
        for snapshot in disallowed_snapshots:
            sub = df[df["asof.snapshot"] == snapshot]
            if _non_null_count(sub[col]) > 0:
                issues.append(
                    f"{col} has values on disallowed snapshot {snapshot}"
                )

    pc_cols = [c for c in df.columns if c.startswith("pc.")]
    if pc_cols and "at_fire" in set(df["asof.snapshot"].unique()):
        fire = df[df["asof.snapshot"] == "at_fire"]
        pc_non_null = int(fire[pc_cols].notna().sum().sum())
        checks["pc_empty_on_at_fire"] = "OK" if pc_non_null == 0 else f"FAIL ({pc_non_null})"
        if pc_non_null:
            issues.append(f"{pc_non_null} pc.* values present on at_fire rows")

    summary = {
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "snapshots": sorted(str(s) for s in df["asof.snapshot"].unique()),
        "checks": checks,
    }
    _write_doc(args.doc, args.matrix, args.schema, summary, issues, warnings)
    print(f"audited {args.matrix}: {len(issues)} issue(s), {len(warnings)} warning(s)")
    print(f"wrote {args.doc}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
