// Reusable SVG equity-overlay chart. Multiple paths share one normalized
// Y-axis; X-axis stretches to the longest path. Faint grid + zero-line +
// per-bucket stroke colors. No external chart library.

import { cn } from "@/lib/utils";
import type { SelectedPath } from "@/lib/prop-simulator/types";

interface EquityOverlayChartProps {
  paths: SelectedPath[];
  width?: number;
  height?: number;
  showAxes?: boolean;
  className?: string;
}

const BUCKET_TONE: Record<SelectedPath["bucket"], string> = {
  best: "stroke-emerald-400",
  near_pass: "stroke-emerald-500/55",
  median: "stroke-zinc-300",
  near_fail: "stroke-rose-500/60",
  worst: "stroke-rose-400",
};

const BUCKET_LABEL: Record<SelectedPath["bucket"], string> = {
  best: "Best",
  near_pass: "Near-pass",
  median: "Median",
  near_fail: "Near-fail",
  worst: "Worst",
};

const BUCKET_DOT_BG: Record<SelectedPath["bucket"], string> = {
  best: "bg-emerald-400",
  near_pass: "bg-emerald-500/55",
  median: "bg-zinc-300",
  near_fail: "bg-rose-500/60",
  worst: "bg-rose-400",
};

export default function EquityOverlayChart({
  paths,
  width = 600,
  height = 200,
  showAxes = true,
  className,
}: EquityOverlayChartProps) {
  if (paths.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center font-mono text-xs text-zinc-500">
        No paths selected.
      </div>
    );
  }

  const allPoints = paths.flatMap((p) => p.equity_curve);
  const min = Math.min(...allPoints);
  const max = Math.max(...allPoints);
  const range = max - min || 1;
  const maxLen = Math.max(...paths.map((p) => p.equity_curve.length));

  const padLeft = showAxes ? 36 : 4;
  const padRight = 4;
  const padTop = 6;
  const padBottom = showAxes ? 18 : 4;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;

  const startBalance = paths[0]?.equity_curve[0] ?? 0;
  const startY = padTop + innerH - ((startBalance - min) / range) * innerH;

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
        {/* horizontal grid */}
        {showAxes
          ? yTickValues.map((v, i) => {
              const y = padTop + innerH - ((v - min) / range) * innerH;
              return (
                <g key={i}>
                  <line
                    x1={padLeft}
                    y1={y}
                    x2={width - padRight}
                    y2={y}
                    stroke="rgb(63 63 70 / 0.35)"
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

        {/* zero / starting-balance line */}
        <line
          x1={padLeft}
          y1={startY}
          x2={width - padRight}
          y2={startY}
          stroke="rgb(82 82 91 / 0.7)"
          strokeWidth="0.5"
        />

        {/* paths */}
        {paths.map((path) => {
          const stepX = innerW / Math.max(1, maxLen - 1);
          const points = path.equity_curve
            .map((v, i) => {
              const x = padLeft + i * stepX;
              const y = padTop + innerH - ((v - min) / range) * innerH;
              return `${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ");
          return (
            <polyline
              key={path.bucket}
              points={points}
              fill="none"
              strokeWidth={path.bucket === "median" ? 1.5 : 1.2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className={BUCKET_TONE[path.bucket]}
            />
          );
        })}

        {/* x-axis label markers */}
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
              day {maxLen - 1}
            </text>
          </>
        ) : null}
      </svg>

      <div className="flex flex-wrap gap-3 font-mono text-[10px] uppercase tracking-widest text-zinc-400">
        {paths.map((path) => (
          <span key={path.bucket} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className={cn("h-[3px] w-4 rounded-sm", BUCKET_DOT_BG[path.bucket])}
            />
            {BUCKET_LABEL[path.bucket]}
          </span>
        ))}
      </div>
    </div>
  );
}
