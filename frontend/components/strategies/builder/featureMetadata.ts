/**
 * Hand-curated map of metadata each feature publishes / reads.
 *
 * The backend's /api/features endpoint doesn't yet expose these
 * relationships formally. Until it does, this file is the source of
 * truth for the visual builder's chain hints. Keep in sync with
 * `backend/app/features/*.py` — each feature's `FeatureResult.metadata`
 * dict shape.
 *
 * Feature-not-listed = treat as `{ publishes: [], reads: [] }`. That's
 * the safe default and keeps the builder usable for new features added
 * to the registry before this file gets updated.
 */

export type FeatureMetadataSpec = {
  publishes: string[];
  reads: string[];
};

export const FEATURE_METADATA: Record<string, FeatureMetadataSpec> = {
  prior_level_sweep: {
    publishes: ["swept_level", "level_ts", "level_kind"],
    reads: [],
  },
  swing_sweep: {
    publishes: ["swept_level", "pivot_bar_idx", "side"],
    reads: [],
  },
  smt_at_level: {
    publishes: ["smt_strength", "sweepers", "holders", "leader"],
    reads: ["swept_level"],
  },
  fvg_touch_recent: {
    publishes: ["fvg_high", "fvg_low", "fvg_mid"],
    reads: [],
  },
  decisive_close: {
    publishes: ["body_pct", "range_pts", "body_pts"],
    reads: [],
  },
  co_score: {
    publishes: ["co_score", "sub_features"],
    reads: [],
  },
  volatility_regime: {
    publishes: ["atr", "regime"],
    reads: [],
  },
  time_window: {
    publishes: [],
    reads: [],
  },
};

export function metadataFor(featureName: string): FeatureMetadataSpec {
  return FEATURE_METADATA[featureName] ?? { publishes: [], reads: [] };
}

/**
 * Stop type "fvg_buffer" needs fvg_touch_recent published somewhere in
 * the same recipe (typically in entry_long or entry_short). Track this
 * implicit dependency so the builder can warn.
 */
export const STOP_TYPE_REQUIRES: Record<string, string[]> = {
  fvg_buffer: ["fvg_high", "fvg_low"],
  fixed_pts: [],
};
