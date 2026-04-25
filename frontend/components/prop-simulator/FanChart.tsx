// Monte Carlo fan chart — three nested grayscale ribbons (P10–P90,
// P25–P75) plus a median spine. The canonical "envelope of probable
// outcomes" view, replacing N spaghetti paths.

import { cn } from "@/lib/utils";
import type { FanBands } from "@/lib/prop-simulator/types";

interface FanChartProps {
  bands: FanBands;
  width?: number;
  height?: number;
  showAxes?: boolean;
  className?: string;
}

function buildRibbonPath(
  upper: number[],
  lower: number[],
  xs: number[],
): string {
  if (upper.length === 0) return "";
  const top = upper.map((v, i) => `${xs[i].toFixed(1)},${v.toFixed(1)}`);
  const bot = lower
    .map((v, i) => `${xs[i].toFixed(1)},${v.toFixed(1)}`)
    .reverse();
  return `M${top.join(" L")} L${bot.join(" L")} Z`;
}

export default function FanChart({
  bands,
  width = 600,
  height = 220,
  showAxes = true,
  className,
}: FanChartProps) {
  const len = bands.median.length;
  if (len === 0) return null;

  const padLeft = showAxes ? 36 : 4;
  const padRight = 4;
  const padTop = 6;
  const padBottom = showAxes ? 18 : 4;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;

  const allValues = [
    ...bands.p10,
    ...bands.p25,
    ...bands.median,
    ...bands.p75,
    ...bands.p90,
  ];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min || 1;

  const xPos = (i: number) =>
    padLeft + (i / Math.max(1, len - 1)) * innerW;
  const yPos = (v: number) =>
    padTop + innerH - ((v - min) / range) * innerH;

  const xs = bands.median.map((_, i) => xPos(i));

  const outerPath = buildRibbonPath(
    bands.p90.map(yPos),
    bands.p10.map(yPos),
    xs,
  );
  const innerPath = buildRibbonPath(
    bands.p75.map(yPos),
    bands.p25.map(yPos),
    xs,
  );

  const medianPoints = bands.median
    .map((v, i) => `${xs[i].toFixed(1)},${yPos(v).toFixed(1)}`)
    .join(" ");

  const startY = yPos(bands.starting_balance);

  const yTicks = 4;
  const yTickValues = Array.from({ length: yTicks + 1 }, (_, i) =>
    min + (range * i) / yTicks,
  );

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="block w-full"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {showAxes
          ? yTickValues.map((v, i) => {
              const y = yPos(v);
              return (
                <g key={i}>
                  <line
                    x1={padLeft}
                    y1={y}
                    x2={width - padRight}
                    y2={y}
                    stroke="rgb(63 63 70 / 0.3)"
                    strokeWidth="0.5"
                    strokeDasharray="2 4"
                  />
                  <text
                    x={padLeft - 4}
                    y={y + 3}
                    textAnchor="end"
                    fontSize="8"
                    fill="rgb(113 113 122)"
                    fontFamily="var(--font-work-sans)"
                  >
                    ${Math.round(v / 1000)}k
                  </text>
                </g>
              );
            })
          : null}

        <line
          x1={padLeft}
          y1={startY}
          x2={width - padRight}
          y2={startY}
          stroke="rgb(82 82 91 / 0.7)"
          strokeWidth="0.5"
        />

        {/* Outer ribbon: P10 → P90 (lightest fill) */}
        <path d={outerPath} fill="rgb(212 212 216 / 0.07)" />
        {/* Inner ribbon: P25 → P75 (medium fill) */}
        <path d={innerPath} fill="rgb(212 212 216 / 0.14)" />

        {/* Median spine */}
        <polyline
          points={medianPoints}
          fill="none"
          stroke="rgb(228 228 231)"
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {showAxes ? (
          <>
            <text
              x={padLeft}
              y={height - 4}
              fontSize="8"
              fill="rgb(113 113 122)"
              fontFamily="var(--font-work-sans)"
            >
              day 0
            </text>
            <text
              x={width - padRight}
              y={height - 4}
              textAnchor="end"
              fontSize="8"
              fill="rgb(113 113 122)"
              fontFamily="var(--font-work-sans)"
            >
              day {len - 1}
            </text>
          </>
        ) : null}
      </svg>

      <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400">
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-[3px] w-4 rounded-sm bg-zinc-200" />
          Median
        </span>
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="h-2 w-3 rounded-sm bg-zinc-200/30"
          />
          P25–P75
        </span>
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="h-2 w-3 rounded-sm bg-zinc-200/15"
          />
          P10–P90
        </span>
        <span className="ml-auto text-zinc-600">
          envelope · all 10,000 sequences
        </span>
      </div>
    </div>
  );
}
