/**
 * Chart theme — values come from Direction A's dark palette. Charts are
 * pure SVG so we hand them concrete colors rather than tailwind classes.
 * Keep this in sync with `tailwind.config.ts` color tokens.
 */
export interface ChartTheme {
  /** primary text on chart */
  fg: string;
  /** muted text */
  mut: string;
  /** grid lines */
  grid: string;
  /** axis labels */
  axis: string;
  /** positive tone */
  pos: string;
  /** negative tone */
  neg: string;
  /** warn tone */
  warn: string;
  /** accent / brand */
  brand: string;
  /** chart background (matches surface) */
  panel: string;
}

export const chartTheme: ChartTheme = {
  fg: "#f5f4f2",
  mut: "rgba(245,244,242,0.50)",
  grid: "rgba(245,244,242,0.08)",
  axis: "rgba(245,244,242,0.40)",
  pos: "#4ade80",
  neg: "#f87171",
  warn: "#fbbf24",
  brand: "#8b95ff",
  panel: "#16140f",
};

export const fmtR = (v: number, sign = true): string =>
  `${sign && v >= 0 ? "+" : ""}${v.toFixed(2)}R`;

export const fmtR0 = (v: number, sign = true): string =>
  `${sign && v >= 0 ? "+" : ""}${v.toFixed(0)}R`;

export const fmtShortDate = (s: string): string =>
  s.length >= 10 ? s.slice(5) : s;

/** Pretty axis ticks in [lo, hi]. Returns 4–5 round values. */
export function niceTicks(lo: number, hi: number, n = 4): number[] {
  const span = hi - lo || 1;
  const step = Math.pow(10, Math.floor(Math.log10(span / n)));
  const err = (n / span) * step;
  let s = step;
  if (err <= 0.15) s = step * 10;
  else if (err <= 0.35) s = step * 5;
  else if (err <= 0.75) s = step * 2;
  const ticks: number[] = [];
  const start = Math.ceil(lo / s) * s;
  for (let v = start; v <= hi + 1e-9; v += s) {
    ticks.push(Number(v.toFixed(6)));
  }
  return ticks;
}
