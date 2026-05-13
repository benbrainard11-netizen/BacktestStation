"""Opening-gap age decay report for NDOG/NWOG levels."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DEFAULT_FEATURES = ROOT / "data" / "ml" / "features" / "ogap.parquet"
DEFAULT_DOC = ROOT / "docs" / "ML_OPENING_GAP_AGE_DECAY.md"
DEFAULT_CSV = ROOT / "data" / "ml" / "anchors" / "opening_gap_age_decay.csv"

HORIZONS = ("next_60m", "next_240m", "next_1d", "next_5d", "next_20d")
AGE_BINS_MIN = [
    0,
    60,
    240,
    24 * 60,
    3 * 24 * 60,
    7 * 24 * 60,
    14 * 24 * 60,
    20 * 24 * 60 + 1,
]
AGE_LABELS = ("0-1h", "1-4h", "4h-1d", "1-3d", "3-7d", "1-2w", "2-20d")


def _pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{100 * float(value):.1f}%"


def _rate(series: pd.Series) -> float:
    if series.empty:
        return float("nan")
    return float(series.fillna(False).astype(bool).mean())


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return df[df["event_type"].isin(("ndog", "nwog"))].copy()


def _coverage_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    groups = [("all", df), *list(df.groupby("event_type")), *[(f"{a}/{b}", g) for (a, b), g in df.groupby(["event_type", "side"])]]
    for name, sub in groups:
        row = {"group": name, "rows": len(sub)}
        for horizon in HORIZONS:
            row[f"{horizon}_touch_rate"] = _rate(sub.get(f"oc.{horizon}.touched_gap", pd.Series(dtype=bool)))
            row[f"{horizon}_mid_rate"] = _rate(sub.get(f"oc.{horizon}.touched_midpoint", pd.Series(dtype=bool)))
            row[f"{horizon}_fill_rate"] = _rate(sub.get(f"oc.{horizon}.fully_filled", pd.Series(dtype=bool)))
            row[f"{horizon}_through_rate"] = _rate(sub.get(f"oc.{horizon}.closed_through", pd.Series(dtype=bool)))
        rows.append(row)
    return rows


def _age_bucket_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    work = df.copy()
    work["touch_bucket"] = pd.cut(
        pd.to_numeric(work.get("oc.full_horizon.first_touch_minutes"), errors="coerce"),
        bins=AGE_BINS_MIN,
        labels=AGE_LABELS,
        right=False,
    )
    work["fill_bucket"] = pd.cut(
        pd.to_numeric(work.get("oc.full_horizon.first_full_fill_minutes"), errors="coerce"),
        bins=AGE_BINS_MIN,
        labels=AGE_LABELS,
        right=False,
    )
    for event_type, sub in work.groupby("event_type"):
        for bucket in AGE_LABELS:
            touched = sub[sub["touch_bucket"].astype(str).eq(bucket)]
            filled = sub[sub["fill_bucket"].astype(str).eq(bucket)]
            rows.append(
                {
                    "event_type": event_type,
                    "age_bucket": bucket,
                    "touch_count": len(touched),
                    "touch_share_of_all": len(touched) / len(sub) if len(sub) else np.nan,
                    "fill_count": len(filled),
                    "fill_share_of_all": len(filled) / len(sub) if len(sub) else np.nan,
                    "support_rejection_rate_after_touch": _rate(touched.get("oc.full_horizon.support_rejection_3bar", pd.Series(dtype=bool))),
                    "resistance_rejection_rate_after_touch": _rate(touched.get("oc.full_horizon.resistance_rejection_3bar", pd.Series(dtype=bool))),
                    "support_break_acceptance_rate_after_touch": _rate(touched.get("oc.full_horizon.support_break_acceptance_3bar", pd.Series(dtype=bool))),
                    "resistance_break_acceptance_rate_after_touch": _rate(touched.get("oc.full_horizon.resistance_break_acceptance_3bar", pd.Series(dtype=bool))),
                }
            )
    return rows


def _write_doc(path: Path, *, features: Path, coverage: pd.DataFrame, age: pd.DataFrame) -> None:
    lines = [
        "# Opening Gap Age Decay",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        f"- Source: `{features}`",
        "- Gap types: `ndog`, `nwog`",
        "- Age buckets use first touch / first full fill inside the 20-day horizon.",
        "",
        "## Fill / Touch Rates",
        "",
        "| group | rows | 1h touch | 4h touch | 1d touch | 5d touch | 20d touch | 1h fill | 4h fill | 1d fill | 5d fill | 20d fill |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in coverage.head(20).itertuples(index=False):
        d = row._asdict()
        lines.append(
            "| {group} | {rows:,} | {t1} | {t4} | {td} | {t5} | {t20} | {f1} | {f4} | {fd} | {f5} | {f20} |".format(
                group=d["group"],
                rows=int(d["rows"]),
                t1=_pct(d["next_60m_touch_rate"]),
                t4=_pct(d["next_240m_touch_rate"]),
                td=_pct(d["next_1d_touch_rate"]),
                t5=_pct(d["next_5d_touch_rate"]),
                t20=_pct(d["next_20d_touch_rate"]),
                f1=_pct(d["next_60m_fill_rate"]),
                f4=_pct(d["next_240m_fill_rate"]),
                fd=_pct(d["next_1d_fill_rate"]),
                f5=_pct(d["next_5d_fill_rate"]),
                f20=_pct(d["next_20d_fill_rate"]),
            )
        )
    lines.extend(
        [
            "",
            "## Age Bucket Reaction",
            "",
            "| event_type | age_bucket | touches | touch_share | fills | fill_share | support_rej | resistance_rej | support_break | resistance_break |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in age.itertuples(index=False):
        d = row._asdict()
        lines.append(
            "| {event_type} | {age_bucket} | {touch_count:,} | {touch_share} | {fill_count:,} | {fill_share} | {support_rej} | {resistance_rej} | {support_break} | {resistance_break} |".format(
                event_type=d["event_type"],
                age_bucket=d["age_bucket"],
                touch_count=int(d["touch_count"]),
                touch_share=_pct(d["touch_share_of_all"]),
                fill_count=int(d["fill_count"]),
                fill_share=_pct(d["fill_share_of_all"]),
                support_rej=_pct(d["support_rejection_rate_after_touch"]),
                resistance_rej=_pct(d["resistance_rejection_rate_after_touch"]),
                support_break=_pct(d["support_break_acceptance_rate_after_touch"]),
                resistance_break=_pct(d["resistance_break_acceptance_rate_after_touch"]),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Higher early touch/fill rates mean the gap is mostly short-lived.",
            "- Later age buckets show whether old gaps keep attracting price.",
            "- Reaction rates are conditional on first touch occurring in that bucket.",
            "- This is descriptive research, not an entry/exit rule.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    df = _load(args.features)
    coverage = pd.DataFrame(_coverage_rows(df))
    age = pd.DataFrame(_age_bucket_rows(df))
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(
        [
            coverage.assign(section="coverage"),
            age.assign(section="age_bucket"),
        ],
        ignore_index=True,
        sort=False,
    ).to_csv(args.csv_output, index=False)
    _write_doc(args.doc, features=args.features, coverage=coverage, age=age)
    print(f"wrote {args.doc}")
    print(f"wrote {args.csv_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
