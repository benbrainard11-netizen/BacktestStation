// Confidence scoring types — used by both the backtest panel and the
// prop simulator result page.

export type ConfidenceLabel = "low" | "moderate" | "high" | "very_high";
export type QualitativeLabel = "low" | "medium" | "high";

export interface BacktestConfidenceSubscores {
  sample_size: number;
  data_quality: number;
  execution_realism: number;
  regime_coverage: number;
  out_of_sample: number;
  cost_sensitivity: number;
}

export interface BacktestConfidenceScore {
  overall: number;
  label: ConfidenceLabel;
  subscores: BacktestConfidenceSubscores;
  overfit_risk: QualitativeLabel;
  cost_sensitivity: QualitativeLabel;
  weaknesses: string[];
}

export interface SimulatorConfidenceSubscores {
  monte_carlo_stability: number;
  trade_pool_quality: number;
  day_pool_quality: number;
  firm_rule_accuracy: number;
  risk_model_accuracy: number;
  sampling_method_quality: number;
  backtest_input_quality: number;
}

export interface SimulatorConfidenceScore {
  overall: number;
  label: ConfidenceLabel;
  subscores: SimulatorConfidenceSubscores;
  weaknesses: string[];
  sequence_count: number;
  convergence_stability: number;
}
