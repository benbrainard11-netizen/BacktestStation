import type { Trade } from "@/lib/api/types";

interface RMultipleHistogramProps {
  trades: Trade[];
}

const WIDTH = 1000;
const HEIGHT = 200;
const PAD_X = 16;
const PAD_Y = 24;
const BIN_WIDTH = 0.5; // each bar covers a 0.5R range

export default function RMultipleHistogram({ trades }: RMultipleHistogramProps) {
  const rs = trades
    .map((t) => t.r_multiple)
    .filter((v): v is number => v !== null);

  if (rs.length === 0) {
    return (
      <p className="font-mono text-xs text-zinc-500">
        No r_multiple values on trades in this run.
      </p>
    );
  }

  const min = Math.min(...rs);
  const max = Math.max(...rs);
  // Nice bin edges: floor/ceil to the nearest BIN_WIDTH
  const binStart = Math.floor(min / BIN_WIDTH) * BIN_WIDTH;
  const binEnd = Math.ceil(max / BIN_WIDTH) * BIN_WIDTH;
  const binCount = Math.max(1, Math.round((binEnd - binStart) / BIN_WIDTH));

  const bins: { lo: number; hi: number; count: number }[] = [];
  for (let i = 0; i < binCount; i++) {
    bins.push({
      lo: binStart + i * BIN_WIDTH,
      hi: binStart + (i + 1) * BIN_WIDTH,
      count: 0,
    });
  }
  for (const r of rs) {
    const idx = Math.min(
      bins.length - 1,
      Math.max(0, Math.floor((r - binStart) / BIN_WIDTH)),
    );
    bins[idx].count += 1;
  }

  const maxCount = Math.max(...bins.map((b) => b.count));
  const innerWidth = WIDTH - PAD_X * 2;
  const innerHeight = HEIGHT - PAD_Y * 2;
  const barWidth = innerWidth / bins.length;

  const wins = rs.filter((r) => r > 0).length;
  const losses = rs.filter((r) => r < 0).length;
  const breakeven = rs.filter((r) => r === 0).length;
  const avg = rs.reduce((s, r) => s + r, 0) / rs.length;

  const zeroBinIndex = bins.findIndex((b) => b.lo <= 0 && 0 < b.hi);
  const zeroX =
    zeroBinIndex >= 0
      ? PAD_X + (zeroBinIndex + (0 - bins[zeroBinIndex].lo) / BIN_WIDTH) * barWidth
      : null;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-zinc-400">
        <span>
          <span className="text-zinc-500">wins</span>{" "}
          <span className="text-emerald-400">{wins}</span>
        </span>
        <span>
          <span className="text-zinc-500">losses</span>{" "}
          <span className="text-rose-400">{losses}</span>
        </span>
        {breakeven > 0 ? (
          <span>
            <span className="text-zinc-500">breakeven</span>{" "}
            <span className="text-zinc-400">{breakeven}</span>
          </span>
        ) : null}
        <span>
          <span className="text-zinc-500">avg</span>{" "}
          <span className={avg > 0 ? "text-emerald-400" : "text-rose-400"}>
            {avg > 0 ? "+" : ""}
            {avg.toFixed(2)}R
          </span>
        </span>
        <span>
          <span className="text-zinc-500">range</span>{" "}
          <span className="text-zinc-300">
            {min.toFixed(2)}R → {max.toFixed(2)}R
          </span>
        </span>
      </div>
      <div className="border border-zinc-800 bg-zinc-950">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="block w-full"
          style={{ height: HEIGHT }}
        >
          {zeroX !== null ? (
            <line
              x1={zeroX}
              x2={zeroX}
              y1={PAD_Y}
              y2={HEIGHT - PAD_Y}
              stroke="rgb(63 63 70)"
              strokeWidth={1}
              strokeDasharray="3 3"
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
          {bins.map((bin, i) => {
            const h = (bin.count / maxCount) * innerHeight;
            const x = PAD_X + i * barWidth;
            const y = HEIGHT - PAD_Y - h;
            const fill =
              bin.hi <= 0
                ? "rgb(244 63 94 / 0.55)"
                : bin.lo >= 0
                  ? "rgb(52 211 153 / 0.55)"
                  : "rgb(113 113 122 / 0.55)";
            return (
              <g key={i}>
                <rect
                  x={x + 1}
                  y={y}
                  width={Math.max(0, barWidth - 2)}
                  height={h}
                  fill={fill}
                />
                {bin.count > 0 ? (
                  <text
                    x={x + barWidth / 2}
                    y={y - 3}
                    textAnchor="middle"
                    className="font-mono"
                    fontSize={10}
                    fill="rgb(161 161 170)"
                  >
                    {bin.count}
                  </text>
                ) : null}
              </g>
            );
          })}
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
