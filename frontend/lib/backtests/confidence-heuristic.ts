// Heuristic placeholder for a backtest's "confidence score".
//
// This is NOT the real confidence computation — it exists so the Backtest
// Confidence panel has something varied to show across different runs. The
// real scorer lands when the engine + OOS + walk-forward + cost-sensitivity
// signals are actually tracked.
//
// All subscores returned here are 0-100. Weights are aligned with
// `docs/ROADMAP` Phase 4 + CLAUDE.md design.

import type {
  BacktestConfidenceScore,
  BacktestConfidenceSubscores,
  QualitativeLabel,
} from "@/lib/prop-simulator/types";
import { confidenceLabel } from "@/lib/prop-simulator/format";

export interface HeuristicInputs {
  tradeCount: number;
  startIso: string | null;
  endIso: string | null;
  dataQualityScore: number | null;
  hasConfigSnapshot: boolean;
}

const WEIGHTS: BacktestConfidenceSubscores = {
  sample_size: 0.2,
  data_quality: 0.15,
  execution_realism: 0.2,
  regime_coverage: 0.15,
  out_of_sample: 0.2,
  cost_sensitivity: 0.1,
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function sampleSizeScore(tradeCount: number): number {
  if (tradeCount <= 0) return 0;
  if (tradeCount >= 1000) return 92;
  if (tradeCount >= 500) return 82;
  if (tradeCount >= 200) return 65;
  if (tradeCount >= 100) return 50;
  if (tradeCount >= 50) return 35;
  return 15;
}

function regimeCoverageScore(startIso: string | null, endIso: string | null): number {
  if (!startIso || !endIso) return 30;
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end <= start) return 30;
  const months = (end - start) / (1000 * 60 * 60 * 24 * 30.44);
  if (months >= 36) return 82;
  if (months >= 24) return 72;
  if (months >= 12) return 60;
  if (months >= 6) return 45;
  return 25;
}

function overfitRiskLabel(tradeCount: number, months: number): QualitativeLabel {
  if (tradeCount >= 500 && months >= 24) return "low";
  if (tradeCount >= 100 && months >= 6) return "medium";
  return "high";
}

function monthsBetween(startIso: string | null, endIso: string | null): number {
  if (!startIso || !endIso) return 0;
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end <= start) return 0;
  return (end - start) / (1000 * 60 * 60 * 24 * 30.44);
}

export function computeHeuristicConfidence(
  inputs: HeuristicInputs,
): BacktestConfidenceScore {
  const subscores: BacktestConfidenceSubscores = {
    sample_size: sampleSizeScore(inputs.tradeCount),
    data_quality: inputs.dataQualityScore !== null
      ? clamp(inputs.dataQualityScore, 0, 100)
      : 55,
    // Placeholders until the engine exposes these signals.
    execution_realism: 55,
    regime_coverage: regimeCoverageScore(inputs.startIso, inputs.endIso),
    out_of_sample: 30,
    cost_sensitivity: inputs.hasConfigSnapshot ? 55 : 40,
  };

  const overallRaw =
    subscores.sample_size * WEIGHTS.sample_size +
    subscores.data_quality * WEIGHTS.data_quality +
    subscores.execution_realism * WEIGHTS.execution_realism +
    subscores.regime_coverage * WEIGHTS.regime_coverage +
    subscores.out_of_sample * WEIGHTS.out_of_sample +
    subscores.cost_sensitivity * WEIGHTS.cost_sensitivity;

  const overall = Math.round(clamp(overallRaw, 0, 100));
  const months = monthsBetween(inputs.startIso, inputs.endIso);

  const weaknesses: string[] = [];
  if (subscores.out_of_sample < 50) {
    weaknesses.push(
      "No out-of-sample / walk-forward signal yet — scored as placeholder.",
    );
  }
  if (inputs.tradeCount < 100) {
    weaknesses.push(
      `Sample size (${inputs.tradeCount} trades) is small — estimates have wide CIs.`,
    );
  }
  if (subscores.regime_coverage < 50) {
    weaknesses.push(
      "Date range under 12 months — limited regime coverage (single volatility era).",
    );
  }
  if (inputs.dataQualityScore !== null && inputs.dataQualityScore < 60) {
    weaknesses.push(
      "Data-quality report flagged issues — check gaps / duplicates / halts.",
    );
  }

  return {
    overall,
    label: confidenceLabel(overall),
    subscores,
    overfit_risk: overfitRiskLabel(inputs.tradeCount, months),
    cost_sensitivity: subscores.cost_sensitivity < 50 ? "high" : "medium",
    weaknesses,
  };
}
