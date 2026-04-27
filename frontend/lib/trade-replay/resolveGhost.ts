/**
 * Pure resolver for hypothetical "ghost" orders against a TBBO tick stream.
 *
 * Walks ticks forward from a starting index. Returns the first tick at
 * which the ghost's stop or target is hit. Honours CLAUDE.md
 * non-negotiable #8: when both are reachable on the same tick, **stop
 * wins**. No look-ahead; no cherry-picking.
 *
 * Long fills:
 *   - filled at ASK (entry buy)
 *   - exits at BID (sell to close); stop on bid <= stop, target on bid >= target
 * Short fills:
 *   - filled at BID (entry sell)
 *   - exits at ASK (buy to close); stop on ask >= stop, target on ask <= target
 *
 * The ghost is "placed" at a wall-clock time + observed midprice. The
 * `entryPrice` field in `GhostOrder` is the user's chosen entry — the
 * resolver does not require it to actually fill (we trust the click).
 * The first tick at or after `placedAtMs` is the start of the walk.
 */

import type { components } from "@/lib/api/generated";

export type Tick = components["schemas"]["TradeReplayTickRead"];

export type GhostSide = "long" | "short";

export interface GhostOrder {
  placedAtMs: number;
  entryPrice: number;
  side: GhostSide;
  stopPrice: number;
  targetPrice: number;
}

export interface GhostResolution {
  exitMs: number;
  exitPrice: number;
  rMultiple: number;
  reason: "stop" | "target" | "no_fill";
}

/**
 * Resolve a ghost order against the tick stream. Returns null only if
 * no resolution is possible (caller hasn't seen ticks yet); use
 * `reason="no_fill"` for the case where the ticks ran out without
 * touching either stop or target.
 */
export function resolveGhost(
  ticks: Tick[],
  ghost: GhostOrder,
): GhostResolution {
  // R-distance (positive points). Used for r_multiple of the resolved
  // outcome. If stop and entry collide, r_multiple is undefined → 0.
  const riskPts = Math.abs(ghost.entryPrice - ghost.stopPrice);

  // Walk forward starting at the first tick at or after placedAtMs.
  let i = 0;
  while (i < ticks.length) {
    const t = new Date(ticks[i].ts).getTime();
    if (t >= ghost.placedAtMs) break;
    i++;
  }

  for (; i < ticks.length; i++) {
    const tick = ticks[i];
    const exitMs = new Date(tick.ts).getTime();

    if (ghost.side === "long") {
      // Long: exit on bid_px (sell-to-close).
      const bid = tick.bid_px;
      if (bid === null) continue;
      const stopHit = bid <= ghost.stopPrice;
      const targetHit = bid >= ghost.targetPrice;
      if (stopHit && targetHit) {
        return {
          exitMs,
          exitPrice: ghost.stopPrice,
          rMultiple: riskPts > 0 ? -1 : 0,
          reason: "stop", // stop wins on ambiguous
        };
      }
      if (stopHit) {
        return {
          exitMs,
          exitPrice: ghost.stopPrice,
          rMultiple: riskPts > 0 ? -1 : 0,
          reason: "stop",
        };
      }
      if (targetHit) {
        const r =
          riskPts > 0 ? (ghost.targetPrice - ghost.entryPrice) / riskPts : 0;
        return {
          exitMs,
          exitPrice: ghost.targetPrice,
          rMultiple: r,
          reason: "target",
        };
      }
    } else {
      // Short: exit on ask_px (buy-to-close).
      const ask = tick.ask_px;
      if (ask === null) continue;
      const stopHit = ask >= ghost.stopPrice;
      const targetHit = ask <= ghost.targetPrice;
      if (stopHit && targetHit) {
        return {
          exitMs,
          exitPrice: ghost.stopPrice,
          rMultiple: riskPts > 0 ? -1 : 0,
          reason: "stop",
        };
      }
      if (stopHit) {
        return {
          exitMs,
          exitPrice: ghost.stopPrice,
          rMultiple: riskPts > 0 ? -1 : 0,
          reason: "stop",
        };
      }
      if (targetHit) {
        const r =
          riskPts > 0 ? (ghost.entryPrice - ghost.targetPrice) / riskPts : 0;
        return {
          exitMs,
          exitPrice: ghost.targetPrice,
          rMultiple: r,
          reason: "target",
        };
      }
    }
  }

  // Ran off the end of the window without filling.
  const lastMs =
    ticks.length > 0 ? new Date(ticks[ticks.length - 1].ts).getTime() : ghost.placedAtMs;
  return {
    exitMs: lastMs,
    exitPrice: ghost.entryPrice,
    rMultiple: 0,
    reason: "no_fill",
  };
}

/**
 * Default stop/target prices given an entry + side, mirroring the live
 * bot's risk policy: stop 1R away, target 3R away. The R-distance is
 * a parameter (live bot uses dollar-bound risk; this is just for sane
 * UI defaults — user will edit anyway).
 */
export function defaultGhostLevels(
  side: GhostSide,
  entryPrice: number,
  riskPts: number,
): { stopPrice: number; targetPrice: number } {
  if (side === "long") {
    return {
      stopPrice: entryPrice - riskPts,
      targetPrice: entryPrice + 3 * riskPts,
    };
  }
  return {
    stopPrice: entryPrice + riskPts,
    targetPrice: entryPrice - 3 * riskPts,
  };
}
