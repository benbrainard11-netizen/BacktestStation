"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";
import type {
  DistributionMetric,
  OutcomeDistribution,
} from "@/lib/prop-simulator/types";

interface OutcomeDistributionChartProps {
  distribution: OutcomeDistribution;
  width?: number;
  height?: number;
  className?: string;
}

function formatTick(metric: DistributionMetric, value: number): string {
  switch (metric) {
    case "final_balance":
      return `$${(value / 1000).toFixed(0)}k`;
    case "ev_after_fees": {
      const sign = value < 0 ? "-" : value > 0 ? "+" : "";
      return `${sign}$${Math.abs(value).toLocaleString("en-US", {
        maximumFractionDigits: 0,
      })}`;
    }
    case "max_drawdown":
      return `$${value.toFixed(0)}`;
  }
}

function formatRange(metric: DistributionMetric, value: number): string {
  switch (metric) {
    case "final_balance":
      return `$${Math.round(value).toLocaleString("en-US")}`;
    case "ev_after_fees": {
      const sign = value < 0 ? "-" : value > 0 ? "+" : "";
      return `${sign}$${Math.abs(Math.round(value)).toLocaleString("en-US")}`;
    }
    case "max_drawdown":
      return `$${Math.round(value).toLocaleString("en-US")}`;
  }
}

export default function OutcomeDistributionChart({
  distribution,
  width = 720,
  height = 220,
  className,
}: OutcomeDistributionChartProps) {
  const { buckets, stats, metric } = distribution;
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (buckets.length === 0) return null;

  const padLeft = 8;
  const padRight = 8;
  const padTop = 12;
  const padBottom = 22;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;

  const xMin = buckets[0].range_low;
  const xMax = buckets[buckets.length - 1].range_high;
  const xRange = xMax - xMin || 1;
  const yMax = Math.max(...buckets.map((b) => b.count));
  const yScale = innerH / (yMax || 1);

  const xPos = (value: number) =>
    padLeft + ((value - xMin) / xRange) * innerW;

  const sigmaLow = Math.max(xMin, stats.mean - stats.std_dev);
  const sigmaHigh = Math.min(xMax, stats.mean + stats.std_dev);

  const tickCount = 5;
  const ticks = Array.from({ length: tickCount + 1 }, (_, i) =>
    xMin + (xRange * i) / tickCount,
  );

  const totalCount = buckets.reduce((acc, b) => acc + b.count, 0);
  const hovered = hoverIndex !== null ? buckets[hoverIndex] ?? null : null;
  const hoverPct = hovered && totalCount > 0
    ? (hovered.count / totalCount) * 100
    : 0;

  const tooltipPx = hovered ? xPos(hovered.range_low + (hovered.range_high - hovered.range_low) / 2) : 0;
  const tooltipLeftPct = (tooltipPx / width) * 100;

  return (
    <div className={cn("relative flex flex-col gap-2", className)}>
      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="block w-full"
          preserveAspectRatio="none"
          aria-hidden="true"
          onMouseLeave={() => setHoverIndex(null)}
        >
          {/* ±1σ shaded band */}
          <rect
            x={xPos(sigmaLow)}
            y={padTop}
            width={Math.max(0, xPos(sigmaHigh) - xPos(sigmaLow))}
            height={innerH}
            fill="rgb(82 82 91 / 0.18)"
          />

          {/* histogram bars (with hover hit areas). y/height get a CSS
              transition so metric-tab switches tween instead of snap.
              SVG presentation-attribute transitions are supported in
              Chromium 78+; WebView2 is current. */}
          {buckets.map((bucket, i) => {
            const x0 = xPos(bucket.range_low);
            const x1 = xPos(bucket.range_high);
            const w = Math.max(1, x1 - x0 - 1);
            const h = bucket.count * yScale;
            const isHover = hoverIndex === i;
            return (
              <g key={i}>
                <rect
                  x={x0 + 0.5}
                  y={padTop + innerH - h}
                  width={w}
                  height={h}
                  fill={
                    isHover ? "rgb(212 212 216 / 0.85)" : "rgb(113 113 122 / 0.65)"
                  }
                  stroke="rgb(161 161 170 / 0.18)"
                  strokeWidth="0.5"
                  style={{
                    transition:
                      "y 320ms cubic-bezier(0.16, 1, 0.3, 1), height 320ms cubic-bezier(0.16, 1, 0.3, 1), fill 150ms ease-out",
                  }}
                />
                {/* full-height hit target */}
                <rect
                  x={x0 + 0.5}
                  y={padTop}
                  width={w}
                  height={innerH}
                  fill="transparent"
                  onMouseEnter={() => setHoverIndex(i)}
                />
              </g>
            );
          })}

          {/* mean / median lines also tween when metric switches */}

          {/* median line (dashed zinc) */}
          <line
            x1={xPos(stats.median)}
            x2={xPos(stats.median)}
            y1={padTop}
            y2={padTop + innerH}
            stroke="rgb(212 212 216 / 0.85)"
            strokeWidth="1"
            strokeDasharray="3 3"
            style={{
              transition:
                "x1 320ms cubic-bezier(0.16, 1, 0.3, 1), x2 320ms cubic-bezier(0.16, 1, 0.3, 1)",
            }}
          />

          {/* mean line (emerald) */}
          <line
            x1={xPos(stats.mean)}
            x2={xPos(stats.mean)}
            y1={padTop}
            y2={padTop + innerH}
            stroke="rgb(52 211 153 / 0.95)"
            strokeWidth="1.25"
            style={{
              transition:
                "x1 320ms cubic-bezier(0.16, 1, 0.3, 1), x2 320ms cubic-bezier(0.16, 1, 0.3, 1)",
            }}
          />

          {/* P10 / P90 markers */}
          {[stats.p10, stats.p90].map((v, i) => (
            <line
              key={i}
              x1={xPos(v)}
              x2={xPos(v)}
              y1={padTop + innerH - 4}
              y2={padTop + innerH + 4}
              stroke="rgb(161 161 170 / 0.85)"
              strokeWidth="1"
            />
          ))}

          {/* baseline */}
          <line
            x1={padLeft}
            y1={padTop + innerH}
            x2={width - padRight}
            y2={padTop + innerH}
            stroke="rgb(63 63 70 / 0.7)"
            strokeWidth="0.5"
          />

          {/* x-axis tick labels */}
          {ticks.map((v, i) => (
            <text
              key={i}
              x={xPos(v)}
              y={height - 6}
              textAnchor="middle"
              fontSize="9"
              fill="rgb(113 113 122)"
              fontFamily="var(--font-work-sans)"
            >
              {formatTick(metric, v)}
            </text>
          ))}
        </svg>

        {hovered ? (
          <div
            className="pointer-events-none absolute -top-1 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-md border border-zinc-700 bg-zinc-950/95 px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-200 shadow-dim"
            style={{ left: `${tooltipLeftPct}%` }}
          >
            <div className="text-zinc-100">
              {formatRange(metric, hovered.range_low)} ·{" "}
              {formatRange(metric, hovered.range_high)}
            </div>
            <div className="mt-0.5 text-zinc-500">
              <span className="text-emerald-400">
                {hovered.count.toLocaleString()}
              </span>{" "}
              seq · {hoverPct.toFixed(2)}%
            </div>
          </div>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400">
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-[3px] w-4 rounded-sm bg-emerald-400" />
          Mean
        </span>
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-px w-4 border-t border-dashed border-zinc-300"
          />
          Median
        </span>
        <span className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="h-2.5 w-3 rounded-sm bg-zinc-700/60 ring-1 ring-zinc-600/50"
          />
          ±1σ band
        </span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-[3px] w-4 rounded-sm bg-zinc-400" />
          P10 / P90 ticks
        </span>
        <span className="ml-auto text-zinc-600">hover bars for bucket counts</span>
      </div>
    </div>
  );
}
