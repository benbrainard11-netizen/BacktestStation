// Number / label formatters shared across the Prop Firm Simulator pages.

import type {
  ConfidenceLabel,
  FailureReason,
  SamplingMode,
} from "./types";

export function formatPercent(value: number, digits: number = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatCurrencySigned(value: number): string {
  const sign = value < 0 ? "-" : value > 0 ? "+" : "";
  return `${sign}$${Math.abs(value).toLocaleString("en-US", {
    maximumFractionDigits: 0,
  })}`;
}

export function formatCurrencyUnsigned(value: number): string {
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

export function formatDays(value: number, digits: number = 1): string {
  return `${value.toFixed(digits)}d`;
}

export function confidenceLabel(score: number): ConfidenceLabel {
  if (score >= 85) return "very_high";
  if (score >= 70) return "high";
  if (score >= 40) return "moderate";
  return "low";
}

export function confidenceLabelText(label: ConfidenceLabel): string {
  switch (label) {
    case "very_high":
      return "Very high confidence";
    case "high":
      return "High confidence";
    case "moderate":
      return "Moderate confidence";
    case "low":
      return "Low confidence";
  }
}

export function samplingModeLabel(mode: SamplingMode): string {
  switch (mode) {
    case "trade_bootstrap":
      return "Trade bootstrap";
    case "day_bootstrap":
      return "Day bootstrap";
    case "regime_bootstrap":
      return "Regime bootstrap";
  }
}

export function failureReasonLabel(reason: FailureReason): string {
  if (reason === null) return "—";
  switch (reason) {
    case "daily_loss_limit":
      return "Daily loss limit";
    case "trailing_drawdown":
      return "Trailing drawdown";
    case "max_drawdown":
      return "Max drawdown";
    case "consistency_rule":
      return "Consistency rule";
    case "payout_blocked":
      return "Payout blocked";
    case "min_days_not_met":
      return "Min days not met";
    case "account_expired":
      return "Account expired";
    case "max_trades_reached":
      return "Max trades reached";
    case "other":
      return "Other";
  }
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}
