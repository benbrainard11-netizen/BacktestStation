import type { components } from "@/lib/api/generated";

type Trade = components["schemas"]["TradeRead"];

interface OverlaidRHistogramProps {
  a: { label: string; trades: Trade[] };
  b: { label: string; trades: Trade[] };
}

const WIDTH = 1000;
const HEIGHT = 220;
const PAD_X = 16;
const PAD_Y = 24;
const BIN_WIDTH = 0.5;
const A_COLOR = "rgb(52 211 153)";
const B_COLOR = "rgb(96 165 250)";

/**
 * Two-series histogram on a shared R-bin axis. Bars are drawn as filled
 * rectangles with alpha so overlap is visible; no chart lib.
 */
export default function OverlaidRHistogram({ a, b }: OverlaidRHistogramProps) {
  const aR = extractR(a.trades);
  const bR = extractR(b.trades);
  if (aR.length === 0 && bR.length === 0) {
    return <p className="font-mono text-xs text-zinc-500">No r_multiple values.</p>;
  }

  const combined = [...aR, ...bR];
  const min = Math.min(...combined);
  const max = Math.max(...combined);
  const binStart = Math.floor(min / BIN_WIDTH) * BIN_WIDTH;
  const binEnd = Math.ceil(max / BIN_WIDTH) * BIN_WIDTH;
  const binCount = Math.max(1, Math.round((binEnd - binStart) / BIN_WIDTH));

  const aBins = bin(aR, binStart, binCount);
  const bBins = bin(bR, binStart, binCount);
  const maxCount = Math.max(1, ...aBins, ...bBins);

  const innerWidth = WIDTH - PAD_X * 2;
  const innerHeight = HEIGHT - PAD_Y * 2;
  const barWidth = innerWidth / binCount;
  const halfWidth = Math.max(1, barWidth / 2 - 1);

  const zeroBinIndex = Math.round((0 - binStart) / BIN_WIDTH);

  const aAvg = aR.length ? aR.reduce((s, r) => s + r, 0) / aR.length : null;
  const bAvg = bR.length ? bR.reduce((s, r) => s + r, 0) / bR.length : null;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-4 font-mono text-[11px] text-zinc-400">
        <span className="flex items-center gap-2">
          <span className="inline-block h-2 w-4" style={{ background: A_COLOR }} />
          {a.label} · {aR.length} trades
          {aAvg !== null ? ` · avg ${formatR(aAvg)}` : null}
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block h-2 w-4" style={{ background: B_COLOR }} />
          {b.label} · {bR.length} trades
          {bAvg !== null ? ` · avg ${formatR(bAvg)}` : null}
        </span>
      </div>

      <div className="border border-zinc-800 bg-zinc-950">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="block w-full"
          style={{ height: HEIGHT }}
        >
          {/* Zero line */}
          {zeroBinIndex >= 0 && zeroBinIndex <= binCount ? (
            <line
              x1={PAD_X + zeroBinIndex * barWidth}
              x2={PAD_X + zeroBinIndex * barWidth}
              y1={PAD_Y}
              y2={HEIGHT - PAD_Y}
              stroke="rgb(63 63 70)"
              strokeWidth={1}
              strokeDasharray="3 3"
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
          {aBins.map((count, i) => (
            <rect
              key={`a-${i}`}
              x={PAD_X + i * barWidth + (barWidth / 2 - halfWidth - 1)}
              y={HEIGHT - PAD_Y - (count / maxCount) * innerHeight}
              width={halfWidth}
              height={(count / maxCount) * innerHeight}
              fill={`${A_COLOR.replace("rgb", "rgba").replace(")", " / 0.55)")}`}
            />
          ))}
          {bBins.map((count, i) => (
            <rect
              key={`b-${i}`}
              x={PAD_X + i * barWidth + barWidth / 2 + 1}
              y={HEIGHT - PAD_Y - (count / maxCount) * innerHeight}
              width={halfWidth}
              height={(count / maxCount) * innerHeight}
              fill={`${B_COLOR.replace("rgb", "rgba").replace(")", " / 0.55)")}`}
            />
          ))}
        </svg>
        <div className="flex justify-between border-t border-zinc-900 px-3 py-1 font-mono text-[10px] text-zinc-600">
          <span>{binStart.toFixed(1)}R</span>
          <span>0</span>
          <span>{binEnd.toFixed(1)}R</span>
        </div>
      </div>
    </div>
  );
}

function extractR(trades: Trade[]): number[] {
  return trades
    .map((t) => t.r_multiple)
    .filter((v): v is number => v !== null);
}

function bin(values: number[], binStart: number, binCount: number): number[] {
  const bins = new Array<number>(binCount).fill(0);
  for (const v of values) {
    const idx = Math.min(
      binCount - 1,
      Math.max(0, Math.floor((v - binStart) / BIN_WIDTH)),
    );
    bins[idx] += 1;
  }
  return bins;
}

function formatR(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}R`;
}
