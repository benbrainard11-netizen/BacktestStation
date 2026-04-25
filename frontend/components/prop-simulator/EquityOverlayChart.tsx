"use client";

import { useEffect, useRef, useState } from "react";

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

const BUCKET_TEXT: Record<SelectedPath["bucket"], string> = {
  best: "text-emerald-400",
  near_pass: "text-emerald-300/85",
  median: "text-zinc-200",
  near_fail: "text-rose-300/85",
  worst: "text-rose-400",
};

function formatBalance(v: number): string {
  return `$${Math.round(v).toLocaleString("en-US")}`;
}

export default function EquityOverlayChart({
  paths,
  width = 600,
  height = 200,
  showAxes = true,
  className,
}: EquityOverlayChartProps) {
  const [hoverDay, setHoverDay] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  // rAF coalesces high-frequency pointermove into one update per frame.
  const rafRef = useRef<number | null>(null);
  const pendingPxRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    },
    [],
  );

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

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    pendingPxRef.current = e.clientX - svg.getBoundingClientRect().left;
    if (rafRef.current !== null) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      const svgNow = svgRef.current;
      const px = pendingPxRef.current;
      if (svgNow === null || px === null) return;
      const rect = svgNow.getBoundingClientRect();
      const vx = (px / rect.width) * width;
      if (vx < padLeft || vx > width - padRight) {
        setHoverDay(null);
        return;
      }
      const stepX = innerW / Math.max(1, maxLen - 1);
      const dayIndex = Math.round((vx - padLeft) / stepX);
      setHoverDay(Math.max(0, Math.min(maxLen - 1, dayIndex)));
    });
  }

  function handleLeave() {
    pendingPxRef.current = null;
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    setHoverDay(null);
  }

  const stepX = innerW / Math.max(1, maxLen - 1);
  const hoverX = hoverDay !== null ? padLeft + hoverDay * stepX : null;

  // Per-path readout values at hoverDay (when path has data at that index).
  const hoverValues = hoverDay !== null
    ? paths.map((p) => ({
        bucket: p.bucket,
        value: p.equity_curve[hoverDay] ?? null,
      }))
    : [];

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {/* Status-line readout — always reserves vertical space so the chart
          doesn't jump. */}
      <div className="flex h-5 flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {hoverDay !== null ? (
          <>
            <span className="text-zinc-400">day {hoverDay}</span>
            <span className="text-zinc-700">·</span>
            {hoverValues.map((hv) =>
              hv.value !== null ? (
                <span key={hv.bucket} className="flex items-center gap-1">
                  <span className={BUCKET_TEXT[hv.bucket]}>
                    {BUCKET_LABEL[hv.bucket].slice(0, 3).toUpperCase()}
                  </span>
                  <span className="tabular-nums text-zinc-200">
                    {formatBalance(hv.value)}
                  </span>
                </span>
              ) : null,
            )}
          </>
        ) : (
          <span className="text-zinc-600">hover chart for crosshair</span>
        )}
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        className="block w-full"
        preserveAspectRatio="none"
        aria-hidden="true"
        onMouseMove={handleMove}
        onMouseLeave={handleLeave}
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

        {/* crosshair vertical guide + per-path dots */}
        {hoverX !== null ? (
          <>
            <line
              x1={hoverX}
              y1={padTop}
              x2={hoverX}
              y2={padTop + innerH}
              stroke="rgb(212 212 216 / 0.55)"
              strokeWidth="0.75"
              strokeDasharray="2 3"
            />
            {paths.map((path) => {
              const v = path.equity_curve[hoverDay ?? -1];
              if (v === undefined) return null;
              const y = padTop + innerH - ((v - min) / range) * innerH;
              return (
                <circle
                  key={path.bucket}
                  cx={hoverX}
                  cy={y}
                  r="2.5"
                  className={cn("fill-current", BUCKET_TEXT[path.bucket])}
                />
              );
            })}
          </>
        ) : null}

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
