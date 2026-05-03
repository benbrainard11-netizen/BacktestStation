/**
 * Starter strategy templates — surfaced by the build page's wizard so
 * a new user has an obvious first move (instead of staring at empty
 * pipelines). Each template is a complete `Spec` ready to drop into
 * `setSpec()`.
 *
 * Adding a template: define a complete `Spec` (start from
 * `DEFAULT_SPEC` and override). Keep templates honest — every feature
 * referenced must already exist in the backend `FEATURES` registry.
 */

import { DEFAULT_SPEC, type Spec } from "./spec";

export type StarterTemplate = {
  id: string;
  name: string;
  description: string;
  spec: Spec;
};

const AM_GATE = { start_hour: 8, end_hour: 10, tz: "America/New_York" };
const ARM_UNTIL_11 = {
  type: "until_clock" as const,
  end_hour: 11,
  tz: "America/New_York",
};

export const STARTER_TEMPLATES: StarterTemplate[] = [
  {
    id: "pdl_sweep_am_orderblock",
    name: "PDL/PDH sweep + 8-10am orderblock",
    description:
      "Long: sweep prior-day low between 8-10am ET, then wait for an engulfing orderblock candle that closes above the most recent down-close bar's open. Setup window expires at 11:00 ET. Short mirrors on PDH.",
    spec: {
      ...DEFAULT_SPEC,
      setup_long: [
        {
          feature: "prior_level_sweep",
          params: { level: "PDL", direction: "below" },
          gate: AM_GATE,
        },
      ],
      setup_short: [
        {
          feature: "prior_level_sweep",
          params: { level: "PDH", direction: "above" },
          gate: AM_GATE,
        },
      ],
      trigger_long: [
        {
          feature: "orderblock_engulf",
          params: { direction: "BULLISH", lookback: 6, min_body_pct: 0.0 },
        },
      ],
      trigger_short: [
        {
          feature: "orderblock_engulf",
          params: { direction: "BEARISH", lookback: 6, min_body_pct: 0.0 },
        },
      ],
      setup_window: { long: ARM_UNTIL_11, short: ARM_UNTIL_11 },
      stop: { type: "fixed_pts", stop_pts: 10 },
      target: { type: "r_multiple", r: 3 },
    },
  },
];
