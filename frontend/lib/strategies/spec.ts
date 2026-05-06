/**
 * Composable strategy spec types — mirror of backend `ComposableSpec`
 * in `app.strategies.composable.config`. Imported by the build page and
 * by starter templates so changes to the spec shape land in one place.
 */

export type CallGate = {
  start_hour: number;
  end_hour: number;
  tz: string;
};

export type FeatureCall = {
  feature: string;
  params: Record<string, unknown>;
  gate?: CallGate | null;
};

export type StopType = "fixed_pts" | "fvg_buffer";
export type StopRule = {
  type: StopType;
  stop_pts?: number;
  buffer_pts?: number;
};

export type TargetType = "r_multiple" | "fixed_pts";
export type TargetRule = {
  type: TargetType;
  r?: number;
  target_pts?: number;
};

/** Tagged union for the per-direction setup-arming window. `null` means
 *  persistent (clears at trading-day rollover). */
export type WindowSpec =
  | { type: "bars"; n: number }
  | { type: "minutes"; n: number }
  | { type: "until_clock"; end_hour: number; tz: string };

export type SetupWindow = {
  long: WindowSpec | null;
  short: WindowSpec | null;
};

export type Spec = {
  setup_long: FeatureCall[];
  trigger_long: FeatureCall[];
  setup_short: FeatureCall[];
  trigger_short: FeatureCall[];
  filter: FeatureCall[];
  filter_long: FeatureCall[];
  filter_short: FeatureCall[];
  setup_window: SetupWindow;
  stop: StopRule;
  target: TargetRule;
  qty: number;
  max_trades_per_day: number;
  entry_dedup_minutes: number;
  max_hold_bars: number;
  max_risk_pts: number;
  min_risk_pts: number;
  aux_symbols: string[];
};

export const DEFAULT_SPEC: Spec = {
  setup_long: [],
  trigger_long: [],
  setup_short: [],
  trigger_short: [],
  filter: [],
  filter_long: [],
  filter_short: [],
  setup_window: { long: null, short: null },
  stop: { type: "fixed_pts", stop_pts: 10, buffer_pts: 5 },
  target: { type: "r_multiple", r: 3, target_pts: 30 },
  qty: 1,
  max_trades_per_day: 2,
  entry_dedup_minutes: 15,
  max_hold_bars: 120,
  max_risk_pts: 150,
  min_risk_pts: 0,
  aux_symbols: [],
};
