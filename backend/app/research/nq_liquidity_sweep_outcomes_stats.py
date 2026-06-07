"""Statistical evidence tables for the NQ liquidity sweep outcome study."""

from __future__ import annotations

from typing import Any

import pandas as pd
from scipy import stats

from app.research.nq_liquidity_sweep_outcomes_feature_defs import feature_metadata
from app.research.nq_liquidity_sweep_outcomes_stats_metrics import (
    auc,
    bootstrap_auc_ci,
    cliffs_delta,
    cohens_d,
    effect_direction,
    monthly_auc_string,
    monthly_direction_string,
    permutation_p,
    rank_score,
    ranking_reason,
    stability,
)
from app.research.nq_liquidity_sweep_outcomes_stats_outputs import (
    examples,
    summary,
)
from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig

CONT = "continuation_breakout"
REV = "failed_breakout_reversal"
AMB = "ambiguous"


def analyze_sweep_features(
    *,
    events: pd.DataFrame,
    features: pd.DataFrame,
    config: LiquiditySweepStudyConfig,
) -> dict[str, Any]:
    metadata = feature_metadata()
    merged = _merge(events, features)
    rankings = _feature_rankings(merged, metadata, config)
    top5 = rankings.head(5).copy()
    distributions = _feature_distributions(merged, metadata)
    monthly = _monthly_stability(merged, metadata)
    return {
        "feature_metadata": metadata,
        "feature_rankings": rankings,
        "top5_features": top5,
        "feature_distributions": distributions,
        "monthly_stability": monthly,
        "examples": examples(merged, top5),
        "summary": summary(events, rankings, monthly, config),
    }


def _feature_rankings(
    merged: pd.DataFrame,
    metadata: pd.DataFrame,
    config: LiquiditySweepStudyConfig,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for meta in metadata.itertuples(index=False):
        feature = meta.feature_name
        if feature not in merged.columns or not bool(meta.knowable_before_entry):
            continue
        row = _rank_feature(merged, feature, meta, config)
        if row is not None:
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["rank_score", "sample_size_total"],
        ascending=[False, False],
    ).reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def _rank_feature(
    merged: pd.DataFrame,
    feature: str,
    meta,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object] | None:
    labeled = _labeled_feature_frame(merged, feature)
    if labeled.empty:
        return None
    cont = labeled.loc[labeled["outcome_label"] == CONT, feature].astype(float)
    rev = labeled.loc[labeled["outcome_label"] == REV, feature].astype(float)
    if cont.empty or rev.empty:
        return None
    feature_auc = auc(cont.to_numpy(), rev.to_numpy())
    med_diff = float(cont.median() - rev.median())
    cliff = cliffs_delta(cont.to_numpy(), rev.to_numpy())
    monthly = _monthly_rows_for_feature(labeled, feature)
    stable = stability(monthly, med_diff)
    ci_low, ci_high = bootstrap_auc_ci(labeled, feature, config)
    ks = stats.ks_2samp(cont, rev).statistic
    row = {
        "feature_name": feature,
        "feature_group": meta.feature_group,
        "feature_window": meta.feature_window,
        "timing_class": meta.timing_class,
        "knowable_before_entry": True,
        "sample_size_total": int(len(labeled)),
        "sample_size_continuation": int(len(cont)),
        "sample_size_reversal": int(len(rev)),
        "sample_size_ambiguous_excluded": int(
            merged.loc[merged["outcome_label"] == AMB, feature].notna().sum()
        ),
        "continuation_median": float(cont.median()),
        "reversal_median": float(rev.median()),
        "median_difference": med_diff,
        "standardized_effect_size": cohens_d(cont.to_numpy(), rev.to_numpy()),
        "cliffs_delta": cliff,
        "auc": feature_auc,
        "separation_auc": max(feature_auc, 1.0 - feature_auc),
        "auc_bootstrap_ci_low": ci_low,
        "auc_bootstrap_ci_high": ci_high,
        "ks_stat": float(ks),
        "permutation_p_value": permutation_p(labeled, feature, config),
        "monthly_auc_values": monthly_auc_string(monthly),
        "monthly_effect_direction": monthly_direction_string(monthly),
        "months_with_same_effect_direction": stable["same_direction_months"],
        "worst_month_auc": stable["worst_month_auc"],
        "best_month_auc": stable["best_month_auc"],
        "stability_score": stable["stability_score"],
        "evidence_quality": _evidence_quality(labeled),
    }
    row["rank_score"] = rank_score(row)
    row["ranking_reason"] = ranking_reason(row)
    return row


def _monthly_stability(
    merged: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for meta in metadata.itertuples(index=False):
        feature = meta.feature_name
        if feature not in merged.columns:
            continue
        labeled = _labeled_feature_frame(merged, feature)
        for row in _monthly_rows_for_feature(labeled, feature):
            rows.append(
                {
                    **row,
                    "feature_group": meta.feature_group,
                    "feature_window": meta.feature_window,
                    "timing_class": meta.timing_class,
                    "knowable_before_entry": bool(meta.knowable_before_entry),
                }
            )
    return pd.DataFrame(rows)


def _feature_distributions(
    merged: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labels = [CONT, REV, AMB]
    for meta in metadata.itertuples(index=False):
        feature = meta.feature_name
        if feature not in merged.columns:
            continue
        for label in labels:
            values = pd.to_numeric(
                merged.loc[merged["outcome_label"] == label, feature],
                errors="coerce",
            ).dropna()
            if values.empty:
                continue
            rows.append(
                {
                    "feature_name": feature,
                    "feature_group": meta.feature_group,
                    "feature_window": meta.feature_window,
                    "outcome_label": label,
                    "sample_size": int(len(values)),
                    "mean": float(values.mean()),
                    "median": float(values.median()),
                    "std": float(values.std()) if len(values) > 1 else 0.0,
                    "p10": float(values.quantile(0.10)),
                    "p25": float(values.quantile(0.25)),
                    "p75": float(values.quantile(0.75)),
                    "p90": float(values.quantile(0.90)),
                }
            )
    return pd.DataFrame(rows)


def _merge(events: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    if events.empty or features.empty:
        return pd.DataFrame()
    return events.merge(features, on=["event_id", "session_date", "level_type", "sweep_side"])


def _labeled_feature_frame(merged: pd.DataFrame, feature: str) -> pd.DataFrame:
    if merged.empty or "outcome_label" not in merged.columns:
        return pd.DataFrame()
    out = merged.loc[merged["outcome_label"].isin([CONT, REV])].copy()
    out[feature] = pd.to_numeric(out[feature], errors="coerce")
    out = out.loc[out[feature].notna()].copy()
    out["month"] = pd.to_datetime(out["session_date"]).dt.to_period("M").astype(str)
    return out


def _monthly_rows_for_feature(labeled: pd.DataFrame, feature: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if labeled.empty:
        return rows
    for month, group in labeled.groupby("month"):
        cont = group.loc[group["outcome_label"] == CONT, feature].astype(float)
        rev = group.loc[group["outcome_label"] == REV, feature].astype(float)
        if cont.empty or rev.empty:
            continue
        diff = float(cont.median() - rev.median())
        feature_auc = auc(cont.to_numpy(), rev.to_numpy())
        rows.append(
            {
                "feature_name": feature,
                "month": month,
                "sample_size": int(len(group)),
                "continuation_count": int(len(cont)),
                "reversal_count": int(len(rev)),
                "monthly_auc": feature_auc,
                "monthly_separation_auc": max(feature_auc, 1.0 - feature_auc),
                "monthly_median_difference": diff,
                "monthly_cliffs_delta": cliffs_delta(cont.to_numpy(), rev.to_numpy()),
                "effect_direction": effect_direction(diff),
            }
        )
    return rows


def _evidence_quality(labeled: pd.DataFrame) -> str:
    cont = int((labeled["outcome_label"] == CONT).sum())
    rev = int((labeled["outcome_label"] == REV).sum())
    months = int(labeled["month"].nunique())
    if len(labeled) >= 100 and cont >= 30 and rev >= 30 and months >= 3:
        return "meets_minimum_sample_guideline"
    return "early_evidence_only"
