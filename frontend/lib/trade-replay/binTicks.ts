/**
 * Pure helpers for the trade-replay chart layer.
 *
 * Bin TBBO ticks into 1-second microcandles. The chart visualizes the
 * binned series; the ghost-order resolver still walks the raw ticks.
 */

import type { components } from "@/lib/api/generated";

export type Tick = components["schemas"]["TradeReplayTickRead"];

export interface MicroCandle {
  /** epoch seconds (lightweight-charts UTCTimestamp) */
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface BidAskPoint {
  time: number;
  value: number;
}

/**
 * Compute midprice from a tick. If both bid and ask are present, returns
 * their average. If only one side has a value, returns that side. If
 * neither, returns null (the tick is quote-less, e.g. a synthetic
 * record — caller should skip it for chart purposes).
 */
export function tickMid(tick: Tick): number | null {
  const bid = tick.bid_px;
  const ask = tick.ask_px;
  if (bid !== null && ask !== null) return (bid + ask) / 2;
  if (bid !== null) return bid;
  if (ask !== null) return ask;
  if (tick.trade_px !== null) return tick.trade_px;
  return null;
}

/**
 * Bin ticks into 1-second OHLC microcandles using the midprice.
 * Ticks are assumed sorted by ts ascending — same order the API returns.
 *
 * Empty input → empty output. Ticks with no usable price are skipped.
 * If a 1-second window has no ticks, no candle is emitted for that
 * second — gaps are honest, not interpolated.
 */
export function binTicksToMicroCandles(ticks: Tick[]): MicroCandle[] {
  const out: MicroCandle[] = [];
  let currentSec: number | null = null;
  let cur: MicroCandle | null = null;

  for (const tick of ticks) {
    const mid = tickMid(tick);
    if (mid === null) continue;
    const tsSec = Math.floor(new Date(tick.ts).getTime() / 1000);
    if (tsSec !== currentSec) {
      if (cur !== null) out.push(cur);
      currentSec = tsSec;
      cur = { time: tsSec, open: mid, high: mid, low: mid, close: mid };
    } else if (cur !== null) {
      cur.high = Math.max(cur.high, mid);
      cur.low = Math.min(cur.low, mid);
      cur.close = mid;
    }
  }
  if (cur !== null) out.push(cur);
  return out;
}

/**
 * Extract the bid line as one point per tick (sub-second resolution
 * lost to the lightweight-charts seconds grid — multiple ticks within
 * the same second collapse to the last value, which is the right
 * "current bid" semantic).
 */
export function bidLine(ticks: Tick[]): BidAskPoint[] {
  return tickLineByField(ticks, "bid_px");
}

export function askLine(ticks: Tick[]): BidAskPoint[] {
  return tickLineByField(ticks, "ask_px");
}

function tickLineByField(
  ticks: Tick[],
  field: "bid_px" | "ask_px",
): BidAskPoint[] {
  const bySec = new Map<number, number>();
  for (const tick of ticks) {
    const v = tick[field];
    if (v === null) continue;
    const tsSec = Math.floor(new Date(tick.ts).getTime() / 1000);
    bySec.set(tsSec, v);
  }
  return Array.from(bySec.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([time, value]) => ({ time, value }));
}

/**
 * Find the index of the first tick whose timestamp is >= `targetMs`.
 * Returns ticks.length if no such tick exists. Used by the playback
 * cursor to map "wall-clock seconds elapsed" to a tick index.
 */
export function tickIndexAtMs(ticks: Tick[], targetMs: number): number {
  // Linear scan is fine for ~10k ticks; binary search if this becomes
  // hot. The cursor only steps forward in playback, so callers can
  // pass `fromIndex` later if needed.
  for (let i = 0; i < ticks.length; i++) {
    if (new Date(ticks[i].ts).getTime() >= targetMs) return i;
  }
  return ticks.length;
}
