// Convert a backend preset / profile to the richer FirmRuleProfile
// shape the frontend Firm Rules page + wizard expect. Two helpers:
//
// - presetToFirmProfile() — for the legacy `/api/prop-firm/presets`
//   endpoint shape. Used by the deterministic single-path checker
//   embedded on /backtests/[id].
// - profileToFirmProfile() — for the new `/api/prop-firm/profiles`
//   endpoint shape. Used by /prop-simulator/firms (editable) and the
//   /prop-simulator/new wizard (live data).
//
// Both mirror backend/app/api/prop_firm.py :: _preset_to_firm_rule_
// profile / _row_to_firm_rule_profile.

import type { components } from "@/lib/api/generated";
import type {
  FirmRuleProfile,
  TrailingDrawdownType,
} from "@/lib/prop-simulator/types";

type Preset = components["schemas"]["PropFirmPresetRead"];
type ProfileRead = components["schemas"]["FirmRuleProfileRead"];

const VALID_TRAILING: ReadonlyArray<TrailingDrawdownType> = [
  "intraday",
  "end_of_day",
  "static",
  "none",
];

function resolveTrailing(preset: Preset): TrailingDrawdownType {
  const raw = (preset.trailing_drawdown_type ?? "none") as TrailingDrawdownType;
  const valid = VALID_TRAILING.includes(raw) ? raw : "none";
  // Backwards-compat: legacy presets that don't set trailing_drawdown_type
  // but do set trailing_drawdown=true should default to intraday.
  if (preset.trailing_drawdown && valid === "none") return "intraday";
  return valid;
}

export function presetToFirmProfile(preset: Preset): FirmRuleProfile {
  const firmName = preset.name.split(" ")[0] || preset.name;
  return {
    profile_id: preset.key,
    firm_name: firmName,
    account_name: preset.name,
    account_size: preset.starting_balance,
    phase_type: "evaluation",
    profit_target: preset.profit_target,
    max_drawdown: preset.max_drawdown,
    daily_loss_limit: preset.daily_loss_limit,
    trailing_drawdown_enabled: preset.trailing_drawdown,
    trailing_drawdown_type: resolveTrailing(preset),
    trailing_drawdown_stop_level: null,
    minimum_trading_days: preset.minimum_trading_days ?? null,
    maximum_trading_days: null,
    max_contracts: preset.max_trades_per_day,
    scaling_plan_enabled: false,
    scaling_plan_rules: [],
    consistency_rule_enabled: preset.consistency_pct !== null,
    consistency_rule_type:
      preset.consistency_pct !== null ? "best_day_pct_of_total" : "none",
    consistency_rule_value: preset.consistency_pct,
    news_trading_allowed: true,
    overnight_holding_allowed: false,
    weekend_holding_allowed: false,
    copy_trading_allowed: true,
    payout_min_days: preset.payout_min_days ?? null,
    payout_min_profit: preset.payout_min_profit ?? null,
    payout_cap: null,
    payout_split: preset.payout_split ?? 0.9,
    first_payout_rules: null,
    recurring_payout_rules: null,
    eval_fee: preset.eval_fee ?? 0,
    activation_fee: preset.activation_fee ?? 0,
    reset_fee: preset.reset_fee ?? 0,
    monthly_fee: preset.monthly_fee ?? 0,
    refund_rules: null,
    rule_source_url: preset.source_url ?? null,
    rule_last_verified_at: preset.last_known_at ?? null,
    // Every backend-seeded preset is an honest approximation, never verified.
    verification_status: "unverified",
    notes: preset.notes,
    version: 1,
    active: true,
  };
}

const VALID_VERIFY_STATUS: ReadonlyArray<FirmRuleProfile["verification_status"]> =
  ["verified", "unverified", "demo"];

function resolveProfileTrailing(
  enabled: boolean,
  raw: string | null | undefined,
): TrailingDrawdownType {
  const cast = (raw ?? "none") as TrailingDrawdownType;
  const valid = VALID_TRAILING.includes(cast) ? cast : "none";
  if (enabled && valid === "none") return "intraday";
  return valid;
}

export function profileToFirmProfile(p: ProfileRead): FirmRuleProfile {
  // verified_at (datetime) wins over last_known_at (date) for the
  // displayed verification timestamp — that's the rule_last_verified_at
  // contract on the frontend type.
  const verifiedAt = p.verified_at ?? p.last_known_at ?? null;
  const status = (
    VALID_VERIFY_STATUS.includes(
      p.verification_status as FirmRuleProfile["verification_status"],
    )
      ? p.verification_status
      : "unverified"
  ) as FirmRuleProfile["verification_status"];
  return {
    profile_id: p.profile_id,
    firm_name: p.firm_name,
    account_name: p.account_name,
    account_size: p.account_size,
    phase_type: (p.phase_type as FirmRuleProfile["phase_type"]) ?? "evaluation",
    profit_target: p.profit_target,
    max_drawdown: p.max_drawdown,
    daily_loss_limit: p.daily_loss_limit,
    trailing_drawdown_enabled: p.trailing_drawdown_enabled,
    trailing_drawdown_type: resolveProfileTrailing(
      p.trailing_drawdown_enabled,
      p.trailing_drawdown_type,
    ),
    trailing_drawdown_stop_level: null,
    minimum_trading_days: p.minimum_trading_days ?? null,
    maximum_trading_days: null,
    max_contracts: p.max_trades_per_day ?? null,
    scaling_plan_enabled: false,
    scaling_plan_rules: [],
    consistency_rule_enabled: p.consistency_pct !== null,
    consistency_rule_type:
      (p.consistency_rule_type as FirmRuleProfile["consistency_rule_type"]) ??
      "none",
    consistency_rule_value: p.consistency_pct ?? null,
    news_trading_allowed: true,
    overnight_holding_allowed: false,
    weekend_holding_allowed: false,
    copy_trading_allowed: true,
    payout_min_days: p.payout_min_days ?? null,
    payout_min_profit: p.payout_min_profit ?? null,
    payout_cap: null,
    payout_split: p.payout_split ?? 0.9,
    first_payout_rules: null,
    recurring_payout_rules: null,
    eval_fee: p.eval_fee ?? 0,
    activation_fee: p.activation_fee ?? 0,
    reset_fee: p.reset_fee ?? 0,
    monthly_fee: p.monthly_fee ?? 0,
    refund_rules: null,
    rule_source_url: p.source_url ?? null,
    rule_last_verified_at: verifiedAt,
    verification_status: status,
    notes: p.notes ?? "",
    version: 1,
    active: !p.is_archived,
  };
}
