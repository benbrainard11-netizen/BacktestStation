import type { components } from "@/lib/api/generated";

import type { EquityPoint } from "@/components/charts/EquityCurve";
import type { MonthlyHeatmapData } from "@/components/charts/MonthlyHeatmap";
import type { HistogramBin } from "@/components/charts/RHistogram";
import type { ScatterTrade } from "@/components/charts/TradeScatter";
import type { HourHeatmapData } from "@/components/charts/HourHeatmap";

type Trade = components["schemas"]["TradeRead"];

const SHORT_MONTH = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/**
 * Build a cumulative-R equity curve from trades. Sorted by exit time
 * (entry as fallback). Drawdown = cumR - running peak.
 */
export function tradesToEquityPoints(trades: Trade[]): EquityPoint[] {
  const sorted = [...trades]
    .filter((tr) => tr.r_multiple !== null)
    .sort((a, b) => {
      const at = a.exit_ts ?? a.entry_ts;
      const bt = b.exit_ts ?? b.entry_ts;
      return new Date(at).getTime() - new Date(bt).getTime();
    });

  const points: EquityPoint[] = [];
  let cum = 0;
  let peak = 0;
  sorted.forEach((tr, i) => {
    cum += tr.r_multiple ?? 0;
    if (cum > peak) peak = cum;
    points.push({
      i,
      r: cum,
      dd: cum - peak,
      ts: tr.exit_ts ?? tr.entry_ts,
    });
  });
  return points;
}

/**
 * Derive a year × month R heatmap from trades. Years are inferred from
 * trade timestamps. Months always 12. `mi` is 0-indexed month.
 */
export function tradesToMonthlyHeatmap(trades: Trade[]): MonthlyHeatmapData {
  const buckets = new Map<string, number>();
  const yearSet = new Set<number>();
  for (const tr of trades) {
    const r = tr.r_multiple;
    if (r === null) continue;
    const ts = tr.exit_ts ?? tr.entry_ts;
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) continue;
    const y = d.getUTCFullYear();
    const mi = d.getUTCMonth();
    yearSet.add(y);
    const key = `${y}:${mi}`;
    buckets.set(key, (buckets.get(key) ?? 0) + r);
  }
  const years = Array.from(yearSet).sort((a, b) => a - b);
  const grid = Array.from(buckets.entries()).map(([key, r]) => {
    const [y, mi] = key.split(":");
    return { year: Number(y), mi: Number(mi), r };
  });
  return { years, months: SHORT_MONTH, grid };
}

const DEFAULT_BINS: { lo: number; hi: number; bin: string }[] = [
  { lo: -3, hi: -2, bin: "-3R" },
  { lo: -2, hi: -1, bin: "-2R" },
  { lo: -1, hi: 0, bin: "-1R" },
  { lo: 0, hi: 1, bin: "0R" },
  { lo: 1, hi: 2, bin: "+1R" },
  { lo: 2, hi: 3, bin: "+2R" },
  { lo: 3, hi: 4, bin: "+3R" },
  { lo: 4, hi: 5, bin: "+4R" },
  { lo: 5, hi: 6, bin: "+5R" },
];

export function tradesToRHistogram(trades: Trade[]): HistogramBin[] {
  return DEFAULT_BINS.map((b) => ({
    ...b,
    count: trades.filter(
      (tr) =>
        tr.r_multiple !== null && tr.r_multiple >= b.lo && tr.r_multiple < b.hi,
    ).length,
  }));
}

/**
 * Trade scatter input — hold time in minutes vs r_multiple. Skips trades
 * with missing exit timestamps (open trades) or null R.
 */
export function tradesToScatter(trades: Trade[]): ScatterTrade[] {
  const out: ScatterTrade[] = [];
  for (const tr of trades) {
    if (tr.r_multiple === null) continue;
    if (tr.exit_ts === null) continue;
    const entry = new Date(tr.entry_ts).getTime();
    const exit = new Date(tr.exit_ts).getTime();
    if (Number.isNaN(entry) || Number.isNaN(exit)) continue;
    const hold = Math.max(0, (exit - entry) / 60_000);
    out.push({ hold, r: tr.r_multiple });
  }
  return out;
}

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/**
 * Hour × day-of-week heatmap. Buckets trades by entry timestamp's local
 * hour and weekday. Cell value = average R per cell. Hours pulled from
 * actual trade activity (no empty leading hours).
 */
export function tradesToHourHeatmap(trades: Trade[]): HourHeatmapData {
  const sums = new Map<string, { sum: number; n: number }>();
  const dayIdxs = new Set<number>();
  const hourIdxs = new Set<number>();
  for (const tr of trades) {
    if (tr.r_multiple === null) continue;
    const d = new Date(tr.entry_ts);
    if (Number.isNaN(d.getTime())) continue;
    const di = d.getDay();
    const hi = d.getHours();
    dayIdxs.add(di);
    hourIdxs.add(hi);
    const key = `${di}:${hi}`;
    const e = sums.get(key) ?? { sum: 0, n: 0 };
    e.sum += tr.r_multiple;
    e.n += 1;
    sums.set(key, e);
  }
  const days = Array.from(dayIdxs).sort((a, b) => a - b);
  const hours = Array.from(hourIdxs).sort((a, b) => a - b);
  const cells = Array.from(sums.entries()).map(([key, v]) => {
    const [di, hi] = key.split(":").map((n) => Number(n));
    return {
      di: days.indexOf(di),
      hi: hours.indexOf(hi),
      r: v.sum / v.n,
    };
  });
  return {
    days: days.map((d) => DAY_NAMES[d]),
    hours: hours.map((h) => `${h.toString().padStart(2, "0")}`),
    cells,
  };
}

/**
 * Compute a rolling-window metric over chronologically sorted trades.
 * Returns one number per trade once the window is full (earlier slots get
 * the cumulative-so-far value to keep arrays aligned by index).
 */
export function rolling(
  trades: Trade[],
  window: number,
  reducer: (chunk: Trade[]) => number,
): number[] {
  const sorted = [...trades]
    .filter((tr) => tr.r_multiple !== null)
    .sort((a, b) => {
      const at = a.exit_ts ?? a.entry_ts;
      const bt = b.exit_ts ?? b.entry_ts;
      return new Date(at).getTime() - new Date(bt).getTime();
    });
  return sorted.map((_, i) => {
    const lo = Math.max(0, i - window + 1);
    const chunk = sorted.slice(lo, i + 1);
    return reducer(chunk);
  });
}

export function rollingWinRate(window = 30) {
  return (trades: Trade[]) =>
    rolling(trades, window, (chunk) => {
      if (chunk.length === 0) return 0;
      const wins = chunk.filter((tr) => (tr.r_multiple ?? 0) > 0).length;
      return wins / chunk.length;
    });
}

export function rollingProfitFactor(window = 30) {
  return (trades: Trade[]) =>
    rolling(trades, window, (chunk) => {
      let wins = 0;
      let losses = 0;
      for (const tr of chunk) {
        const r = tr.r_multiple ?? 0;
        if (r > 0) wins += r;
        else losses += -r;
      }
      if (losses === 0) return wins > 0 ? 5 : 1;
      return wins / losses;
    });
}

export function rollingSharpe(window = 30) {
  return (trades: Trade[]) =>
    rolling(trades, window, (chunk) => {
      if (chunk.length < 2) return 0;
      const rs = chunk.map((tr) => tr.r_multiple ?? 0);
      const mean = rs.reduce((a, b) => a + b, 0) / rs.length;
      const variance =
        rs.reduce((a, b) => a + (b - mean) * (b - mean), 0) / (rs.length - 1);
      const stdev = Math.sqrt(variance);
      if (stdev === 0) return 0;
      return (mean / stdev) * Math.sqrt(252);
    });
}
