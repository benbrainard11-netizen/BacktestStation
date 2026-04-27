/**
 * Client-side resampling of 1m OHLCV bars to a higher timeframe.
 *
 * Aligned to the wall-clock UTC minute. A 5m bucket spans
 * `[hh:mm0, hh:mm0+5)` where mm0 is mm rounded down to a multiple of 5.
 * Same convention `read_bars` uses on the backend, so client-resampled
 * bars stay consistent with engine-side resamples.
 *
 * Empty input → empty output. Trailing partial bucket is emitted (so
 * the last visible candle on the chart reflects whatever ticked in
 * during the active partial bucket).
 */

import type { components } from "@/lib/api/generated";

type Bar = components["schemas"]["ReplayBar"];

export interface ResampledBar {
  /** epoch seconds (lightweight-charts UTCTimestamp) of the bucket open */
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  /** original 1m bars covered by this bucket (in order) */
  source_count: number;
}

const TIMEFRAMES = {
  "1m": 1,
  "5m": 5,
  "15m": 15,
  "30m": 30,
} as const;

export type Timeframe = keyof typeof TIMEFRAMES;

export function timeframeMinutes(tf: Timeframe): number {
  return TIMEFRAMES[tf];
}

export function resample(bars: Bar[], tf: Timeframe): ResampledBar[] {
  const minutes = timeframeMinutes(tf);
  if (bars.length === 0) return [];
  const bucketMs = minutes * 60 * 1000;

  const out: ResampledBar[] = [];
  let cur: ResampledBar | null = null;
  let curBucketMs: number | null = null;

  for (const b of bars) {
    const ms = new Date(b.ts).getTime();
    const bucketStart = Math.floor(ms / bucketMs) * bucketMs;
    if (bucketStart !== curBucketMs) {
      if (cur !== null) out.push(cur);
      curBucketMs = bucketStart;
      cur = {
        time: Math.floor(bucketStart / 1000),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
        volume: b.volume,
        source_count: 1,
      };
    } else if (cur !== null) {
      cur.high = Math.max(cur.high, b.high);
      cur.low = Math.min(cur.low, b.low);
      cur.close = b.close;
      cur.volume += b.volume;
      cur.source_count += 1;
    }
  }
  if (cur !== null) out.push(cur);
  return out;
}

/**
 * Find the index of the first bar whose epoch second is >= `targetSec`.
 * Returns bars.length if none. Used by the chart to auto-scroll the
 * cursor to the trade entry on load.
 */
export function barIndexAtSec(
  bars: ResampledBar[],
  targetSec: number,
): number {
  for (let i = 0; i < bars.length; i++) {
    if (bars[i].time >= targetSec) return i;
  }
  return bars.length;
}
