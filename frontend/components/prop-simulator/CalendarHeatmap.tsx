"use client";

// GitHub-contributions-style daily P&L heatmap. Pure SVG. Cells colored
// by sign + quantile (rose for losses, emerald for gains, zinc for flat).
// Hover surfaces the date + P&L + trade count.

import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import type { DailyPnL } from "@/lib/prop-simulator/types";

interface CalendarHeatmapProps {
  data: DailyPnL[];
  cellSize?: number;
  cellGap?: number;
  className?: string;
}

const ROW_LABELS = ["", "Mon", "", "Wed", "", "Fri", ""];

function dayOfWeekIndex(iso: string): number {
  // 0 = Sunday … 6 = Saturday — match standard week-as-column layout.
  return new Date(iso + "T00:00:00Z").getUTCDay();
}

function isoWeekColumn(iso: string, firstDate: string): number {
  const a = new Date(firstDate + "T00:00:00Z");
  const b = new Date(iso + "T00:00:00Z");
  const days = Math.round((b.getTime() - a.getTime()) / 86_400_000);
  // Anchor to the Sunday-of-week of the first date so rows align.
  const firstDow = a.getUTCDay();
  return Math.floor((days + firstDow) / 7);
}

function colorFor(pnl: number, maxAbs: number): string {
  if (pnl === 0 || maxAbs === 0) return "rgb(39 39 42)";
  const intensity = Math.min(1, Math.abs(pnl) / maxAbs);
  if (pnl > 0) {
    // emerald ramp
    const alpha = 0.18 + intensity * 0.7;
    return `rgba(52, 211, 153, ${alpha.toFixed(3)})`;
  }
  const alpha = 0.18 + intensity * 0.7;
  return `rgba(244, 63, 94, ${alpha.toFixed(3)})`;
}

function formatPnl(pnl: number): string {
  const sign = pnl > 0 ? "+" : pnl < 0 ? "-" : "";
  return `${sign}$${Math.abs(pnl).toLocaleString("en-US")}`;
}

export default function CalendarHeatmap({
  data,
  cellSize = 12,
  cellGap = 3,
  className,
}: CalendarHeatmapProps) {
  const [hover, setHover] = useState<DailyPnL | null>(null);

  const { weeks, maxAbs, totals } = useMemo(() => {
    if (data.length === 0)
      return { weeks: 0, maxAbs: 1, totals: { sum: 0, win: 0, loss: 0, flat: 0 } };
    const firstDate = data[0].date;
    let maxCol = 0;
    let mAbs = 0;
    let sum = 0;
    let win = 0;
    let loss = 0;
    let flat = 0;
    for (const d of data) {
      const col = isoWeekColumn(d.date, firstDate);
      if (col > maxCol) maxCol = col;
      const abs = Math.abs(d.pnl);
      if (abs > mAbs) mAbs = abs;
      sum += d.pnl;
      if (d.pnl > 0) win++;
      else if (d.pnl < 0) loss++;
      else flat++;
    }
    return {
      weeks: maxCol + 1,
      maxAbs: mAbs || 1,
      totals: { sum, win, loss, flat },
    };
  }, [data]);

  if (data.length === 0) return null;

  const labelW = 22;
  const padTop = 6;
  const padBottom = 6;
  const monthLabelH = 14;
  const stepX = cellSize + cellGap;
  const stepY = cellSize + cellGap;
  const width = labelW + weeks * stepX;
  const height = monthLabelH + 7 * stepY + padTop + padBottom;
  const firstDate = data[0].date;

  // Month labels: pick the first cell of each month from the data series.
  const monthMarkers: { x: number; label: string }[] = [];
  let lastMonth = -1;
  for (const d of data) {
    const month = new Date(d.date + "T00:00:00Z").getUTCMonth();
    if (month !== lastMonth) {
      lastMonth = month;
      const col = isoWeekColumn(d.date, firstDate);
      monthMarkers.push({
        x: labelW + col * stepX,
        label: new Date(d.date + "T00:00:00Z").toLocaleString("en-US", {
          month: "short",
        }),
      });
    }
  }

  return (
    <div className={cn("relative flex flex-col gap-3", className)}>
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width={width}
          height={height}
          className="block"
          aria-hidden="true"
        >
          {/* month labels along the top */}
          {monthMarkers.map((m, i) => (
            <text
              key={`${m.label}-${i}`}
              x={m.x}
              y={10}
              fontSize="9"
              fill="rgb(113 113 122)"
              fontFamily="var(--font-work-sans)"
              className="uppercase tracking-widest"
            >
              {m.label}
            </text>
          ))}

          {/* row labels (Mon / Wed / Fri) */}
          {ROW_LABELS.map((label, row) =>
            label ? (
              <text
                key={`row-${row}`}
                x={0}
                y={monthLabelH + padTop + row * stepY + cellSize - 2}
                fontSize="8"
                fill="rgb(113 113 122)"
                fontFamily="var(--font-work-sans)"
                className="uppercase tracking-widest"
              >
                {label}
              </text>
            ) : null,
          )}

          {/* day cells */}
          {data.map((d) => {
            const col = isoWeekColumn(d.date, firstDate);
            const row = dayOfWeekIndex(d.date);
            const x = labelW + col * stepX;
            const y = monthLabelH + padTop + row * stepY;
            const isHover = hover?.date === d.date;
            return (
              <rect
                key={d.date}
                x={x}
                y={y}
                width={cellSize}
                height={cellSize}
                rx={2}
                ry={2}
                fill={colorFor(d.pnl, maxAbs)}
                stroke={isHover ? "rgb(228 228 231)" : "rgb(63 63 70 / 0.35)"}
                strokeWidth={isHover ? 1 : 0.5}
                onMouseEnter={() => setHover(d)}
                onMouseLeave={() => setHover((curr) => (curr?.date === d.date ? null : curr))}
                style={{ transition: "stroke 120ms ease-out" }}
              />
            );
          })}
        </svg>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-[10px] uppercase tracking-widest text-zinc-400">
        <span className="flex items-center gap-1.5">
          <span className="text-zinc-600">range</span>
          <span>
            {data[0].date} → {data[data.length - 1].date}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="text-zinc-600">net</span>
          <span
            className={cn(
              "tabular-nums",
              totals.sum > 0
                ? "text-emerald-300"
                : totals.sum < 0
                  ? "text-rose-300"
                  : "text-zinc-200",
            )}
          >
            {formatPnl(totals.sum)}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="text-zinc-600">days</span>
          <span className="tabular-nums text-emerald-300">{totals.win}w</span>
          <span className="text-zinc-700">·</span>
          <span className="tabular-nums text-rose-300">{totals.loss}l</span>
          <span className="text-zinc-700">·</span>
          <span className="tabular-nums text-zinc-400">{totals.flat}f</span>
        </span>
        <span className="ml-auto flex items-center gap-1.5">
          <span className="text-zinc-600">scale</span>
          <span aria-hidden="true" className="h-2 w-2 rounded-sm bg-rose-400/80" />
          <span aria-hidden="true" className="h-2 w-2 rounded-sm bg-rose-400/40" />
          <span aria-hidden="true" className="h-2 w-2 rounded-sm bg-zinc-700" />
          <span aria-hidden="true" className="h-2 w-2 rounded-sm bg-emerald-400/40" />
          <span aria-hidden="true" className="h-2 w-2 rounded-sm bg-emerald-400/80" />
        </span>
      </div>

      {hover ? (
        <div className="rounded-md border border-zinc-700 bg-zinc-950/95 px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-zinc-200 shadow-dim">
          <div className="flex items-baseline gap-3">
            <span className="text-zinc-500">{hover.date}</span>
            <span
              className={cn(
                "tabular-nums",
                hover.pnl > 0
                  ? "text-emerald-300"
                  : hover.pnl < 0
                    ? "text-rose-300"
                    : "text-zinc-300",
              )}
            >
              {formatPnl(hover.pnl)}
            </span>
            <span className="text-zinc-500">·</span>
            <span className="tabular-nums text-zinc-400">
              {hover.trades} trades
            </span>
          </div>
        </div>
      ) : (
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          hover a cell · daily P&amp;L of the underlying backtest
        </p>
      )}
    </div>
  );
}
