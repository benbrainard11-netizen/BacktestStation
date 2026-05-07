"use client";

import {
  ColorType,
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type Time,
} from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";

import { Card, CardHead } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

import type { BotPayload } from "./LiveBotPanel";

type LiveHeartbeat = components["schemas"]["LiveHeartbeatRead"];

type WindowKey = "1h" | "6h" | "1d" | "all";

const WINDOW_OPTIONS: { key: WindowKey; label: string; seconds: number | null }[] = [
  { key: "1h", label: "1h", seconds: 3600 },
  { key: "6h", label: "6h", seconds: 6 * 3600 },
  { key: "1d", label: "1d", seconds: 24 * 3600 },
  { key: "all", label: "all", seconds: null },
];

interface Props {
  history: LiveHeartbeat[];
}

/**
 * Account-balance curve over the recent heartbeat window. Reads
 * `payload.balance` from each heartbeat, plots as a single line
 * series with hover tooltip. Window selector filters the input
 * before setData(). Color follows last-vs-first delta — green when
 * up over the window, red when down.
 *
 * Empty / insufficient data states render as muted text instead of
 * an empty chart.
 */
export function EquityCurveChart({ history }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const [window, setWindow] = useState<WindowKey>("all");

  // Build full series chronologically, then filter by window.
  const series: LineData[] = useMemo(() => {
    if (history.length === 0) return [];
    const ordered = [...history].reverse();
    const cutoffSec =
      WINDOW_OPTIONS.find((o) => o.key === window)?.seconds ?? null;
    const cutoff =
      cutoffSec === null ? 0 : Date.now() - cutoffSec * 1000;
    const filtered: LineData[] = [];
    for (const hb of ordered) {
      const tsMs = new Date(hb.ts).getTime();
      if (cutoff > 0 && tsMs < cutoff) continue;
      const p = (hb.payload ?? {}) as BotPayload;
      if (typeof p.balance !== "number") continue;
      filtered.push({
        time: (Math.floor(tsMs / 1000) as Time),
        value: p.balance,
      });
    }
    return filtered;
  }, [history, window]);

  const first = series.length > 0 ? series[0].value : null;
  const last = series.length > 0 ? series[series.length - 1].value : null;
  const delta =
    first !== null && last !== null ? (last as number) - (first as number) : 0;
  const lineColor =
    delta > 0
      ? "var(--pos)"
      : delta < 0
        ? "var(--neg)"
        : "var(--ink-2)";

  // Mount the chart once.
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#27272a" },
        horzLines: { color: "#27272a" },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: "#27272a" },
      crosshair: {
        // Magnet snap to series points
        mode: 1,
      },
    });
    const lineSeries = chart.addSeries(LineSeries, {
      color: "#22c55e",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = lineSeries;

    // Hover tooltip — uses the chart's crosshair move callback to read
    // the data point under the cursor and position a small absolute
    // tooltip div. Scoped inside the container ref.
    chart.subscribeCrosshairMove((param) => {
      const tooltip = tooltipRef.current;
      if (!tooltip) return;
      if (
        !param.point ||
        param.point.x < 0 ||
        param.point.y < 0 ||
        !param.time ||
        !seriesRef.current
      ) {
        tooltip.style.display = "none";
        return;
      }
      const value = param.seriesData.get(seriesRef.current) as
        | LineData
        | undefined;
      if (!value) {
        tooltip.style.display = "none";
        return;
      }
      const ts = new Date((value.time as number) * 1000);
      tooltip.innerHTML = `
        <div class="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-4">
          ${ts.toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
        <div class="font-mono text-[12.5px] tabular-nums text-ink-0">
          $${value.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </div>
      `;
      tooltip.style.display = "block";
      // Position tooltip 12px to the right of the cursor, clamped within
      // the container's bounds.
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const x = Math.min(param.point.x + 12, rect.width - 110);
      const y = Math.max(0, param.point.y - 30);
      tooltip.style.left = `${x}px`;
      tooltip.style.top = `${y}px`;
    });

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Push the filtered series + update line color whenever window or
  // history changes.
  useEffect(() => {
    if (!seriesRef.current) return;
    seriesRef.current.applyOptions({ color: lineColor });
    seriesRef.current.setData(series);
    chartRef.current?.timeScale().fitContent();
  }, [series, lineColor]);

  return (
    <Card>
      <CardHead
        eyebrow="equity curve"
        title="Account balance"
        right={
          <div className="flex items-center gap-1.5">
            {WINDOW_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setWindow(opt.key)}
                className={cn(
                  "rounded border px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.06em] transition-colors",
                  window === opt.key
                    ? "border-accent-line bg-accent-soft text-accent"
                    : "border-line bg-bg-2 text-ink-3 hover:border-line-3 hover:text-ink-1",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        }
      />

      {series.length < 2 ? (
        <div className="px-4 py-10 text-center font-mono text-[11.5px] text-ink-3">
          {history.length === 0
            ? "Waiting for heartbeats…"
            : "Need ≥2 balance points to chart this window."}
        </div>
      ) : (
        <div className="relative">
          <div ref={containerRef} className="h-56 w-full" />
          <div
            ref={tooltipRef}
            className="pointer-events-none absolute z-10 hidden rounded border border-line bg-bg-1/95 px-2.5 py-1.5 backdrop-blur-sm"
            style={{ display: "none" }}
          />
          {/* Footer: first/last/delta summary so a glance gives the magnitude. */}
          <div className="flex items-center justify-between border-t border-line px-4 py-2 font-mono text-[10.5px] text-ink-3">
            <span>
              start{" "}
              <span className="tabular-nums text-ink-1">
                ${first?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </span>
            <span
              className={cn(
                "tabular-nums",
                delta > 0
                  ? "text-pos"
                  : delta < 0
                    ? "text-neg"
                    : "text-ink-2",
              )}
            >
              Δ {delta >= 0 ? "+" : ""}${delta.toFixed(0)}
            </span>
            <span>
              latest{" "}
              <span className="tabular-nums text-ink-1">
                ${last?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </span>
          </div>
        </div>
      )}
    </Card>
  );
}
