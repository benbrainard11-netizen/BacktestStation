"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";
import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Card, CardHead, Chip } from "@/components/atoms";
import type { components } from "@/lib/api/generated";

import { type FvgZoneInput, FvgZonesPrimitive } from "./FvgZonesPrimitive";

type ReplayPayload = components["schemas"]["ReplayPayload"];

const SPEED_PRESETS = [
  { label: "1×", ms: 1000 },
  { label: "5×", ms: 200 },
  { label: "30×", ms: 33 },
  { label: "60×", ms: 16 },
] as const;

interface Props {
  payload: ReplayPayload;
}

export default function ReplayChart({ payload }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const tickHandleRef = useRef<number | null>(null);

  const [cursorIndex, setCursorIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState<number>(SPEED_PRESETS[1].ms);
  const [showZones, setShowZones] = useState(true);

  const bars = useMemo(() => payload.bars ?? [], [payload.bars]);
  const entries = useMemo(() => payload.entries ?? [], [payload.entries]);
  const zones = useMemo(() => payload.fvg_zones ?? [], [payload.fvg_zones]);

  const candles: CandlestickData[] = useMemo(
    () =>
      bars.map((b) => ({
        time: Math.floor(new Date(b.ts).getTime() / 1000) as Time,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    [bars],
  );

  // FVG zone primitive — attached once, fed via setZones() on change.
  const zonesPrimitiveRef = useRef<FvgZonesPrimitive | null>(null);

  const zoneInputs = useMemo<FvgZoneInput[]>(
    () =>
      zones.map((z) => ({
        direction: z.direction,
        low: z.low,
        high: z.high,
        createdAtSec: Math.floor(new Date(z.created_at).getTime() / 1000),
        fillTimeSec:
          z.fill_time !== null && z.fill_time !== undefined
            ? Math.floor(new Date(z.fill_time).getTime() / 1000)
            : null,
      })),
    [zones],
  );

  // Mount the chart once. Token-driven colors so theme switches still work.
  useEffect(() => {
    if (!containerRef.current) return;
    const css = getComputedStyle(document.documentElement);
    const bg1 = css.getPropertyValue("--bg-1").trim() || "#0f1115";
    const ink2 = css.getPropertyValue("--ink-2").trim() || "#a0a8b3";
    const line = css.getPropertyValue("--line").trim() || "#1d2128";
    const pos = css.getPropertyValue("--pos").trim() || "#34d399";
    const neg = css.getPropertyValue("--neg").trim() || "#f87171";

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: bg1 },
        textColor: ink2,
      },
      grid: {
        vertLines: { color: line },
        horzLines: { color: line },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: line },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: pos,
      downColor: neg,
      wickUpColor: pos,
      wickDownColor: neg,
      borderVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;
    markersRef.current = createSeriesMarkers(series, []);
    const zonesPrimitive = new FvgZonesPrimitive();
    series.attachPrimitive(zonesPrimitive);
    zonesPrimitiveRef.current = zonesPrimitive;
    return () => {
      markersRef.current?.detach();
      markersRef.current = null;
      try {
        series.detachPrimitive(zonesPrimitive);
      } catch {
        /* chart torn down already */
      }
      zonesPrimitiveRef.current = null;
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Push zone inputs into the primitive whenever they change or the toggle flips.
  useEffect(() => {
    const primitive = zonesPrimitiveRef.current;
    if (!primitive) return;
    primitive.setZones(showZones ? zoneInputs : []);
    chartRef.current?.timeScale().applyOptions({});
  }, [zoneInputs, showZones]);

  // Push the visible slice of candles whenever cursor moves or data changes.
  useEffect(() => {
    if (!seriesRef.current) return;
    const visible = candles.slice(0, Math.max(1, cursorIndex + 1));
    seriesRef.current.setData(visible);
    chartRef.current?.timeScale().fitContent();
  }, [candles, cursorIndex]);

  // Entry markers on the candle series.
  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) return;
    const candleTimeSet = new Set(candles.map((c) => c.time));
    const css = getComputedStyle(document.documentElement);
    const pos = css.getPropertyValue("--pos").trim() || "#34d399";
    const neg = css.getPropertyValue("--neg").trim() || "#f87171";
    const markers: SeriesMarker<Time>[] = entries
      .map((e) => {
        const ts = Math.floor(new Date(e.entry_ts).getTime() / 1000) as Time;
        if (!candleTimeSet.has(ts)) return null;
        const isLong = e.side.toLowerCase() === "long";
        const pnlText =
          e.pnl !== null && e.pnl !== undefined
            ? ` ${e.pnl >= 0 ? "+" : ""}${e.pnl.toFixed(0)}`
            : "";
        return {
          time: ts,
          position: isLong ? "belowBar" : "aboveBar",
          color: isLong ? pos : neg,
          shape: isLong ? "arrowUp" : "arrowDown",
          text: `${e.side} @${e.entry_price.toFixed(2)}${pnlText}`,
        } as SeriesMarker<Time>;
      })
      .filter((m): m is SeriesMarker<Time> => m !== null);
    markersRef.current?.setMarkers(markers);
  }, [entries, candles]);

  // Playback tick.
  useEffect(() => {
    if (!playing) {
      if (tickHandleRef.current !== null) {
        window.clearInterval(tickHandleRef.current);
        tickHandleRef.current = null;
      }
      return;
    }
    tickHandleRef.current = window.setInterval(() => {
      setCursorIndex((prev) => {
        if (prev >= candles.length - 1) {
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, speedMs);
    return () => {
      if (tickHandleRef.current !== null) {
        window.clearInterval(tickHandleRef.current);
        tickHandleRef.current = null;
      }
    };
  }, [playing, speedMs, candles.length]);

  if (candles.length === 0) {
    return (
      <Card>
        <CardHead eyebrow="replay" title={`${payload.symbol} · ${String(payload.date)}`} />
        <div className="px-6 py-10 text-center font-mono text-[12px] text-ink-3">
          No bars in the warehouse for {payload.symbol} on{" "}
          {String(payload.date)}. The data may not be backfilled for this date,
          or the symbol may not be in the universe.
        </div>
      </Card>
    );
  }

  const currentBar = bars[cursorIndex];
  const currentBarTs = currentBar
    ? new Date(currentBar.ts).toISOString().slice(11, 19)
    : "—";

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHead
          eyebrow={`replay · ${payload.symbol}`}
          title={`${String(payload.date)}`}
          right={
            <div className="flex items-center gap-2">
              <Chip>
                {cursorIndex + 1}/{candles.length} bars
              </Chip>
              {currentBar && (
                <Chip tone="accent">
                  {currentBarTs} · {currentBar.close.toFixed(2)}
                </Chip>
              )}
              {entries.length > 0 && (
                <Chip tone="pos">{entries.length} entries</Chip>
              )}
              {zoneInputs.length > 0 && (
                <Chip tone={showZones ? "accent" : "default"}>
                  {zoneInputs.length} FVG
                </Chip>
              )}
            </div>
          }
        />
        <div className="p-3">
          <div
            ref={containerRef}
            className="h-[480px] w-full"
            aria-label={`Replay chart for ${payload.symbol} on ${String(payload.date)}`}
          />
        </div>
        <div className="flex flex-wrap items-center gap-3 border-t border-line bg-bg-1 px-3 py-3">
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setCursorIndex(0)}
              className="btn btn-sm"
              title="Reset to first bar"
              aria-label="Reset to first bar"
            >
              <SkipBack size={14} />
            </button>
            <button
              type="button"
              onClick={() => setPlaying((p) => !p)}
              className="btn btn-primary btn-sm"
              aria-label={playing ? "Pause" : "Play"}
            >
              {playing ? (
                <>
                  <Pause size={14} /> Pause
                </>
              ) : (
                <>
                  <Play size={14} /> Play
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() =>
                setCursorIndex((prev) => Math.min(candles.length - 1, prev + 1))
              }
              className="btn btn-sm"
              title="Step forward 1 bar"
              aria-label="Step forward"
            >
              <SkipForward size={14} />
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              speed
            </span>
            <div
              role="radiogroup"
              aria-label="Playback speed"
              className="inline-flex rounded border border-line-2 bg-bg-2 p-0.5"
            >
              {SPEED_PRESETS.map((preset) => {
                const active = speedMs === preset.ms;
                return (
                  <button
                    key={preset.label}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setSpeedMs(preset.ms)}
                    className={
                      active
                        ? "rounded-[3px] bg-accent px-2 py-0.5 font-mono text-[11px] font-semibold text-[#031419]"
                        : "rounded-[3px] px-2 py-0.5 font-mono text-[11px] text-ink-2 hover:text-ink-0"
                    }
                  >
                    {preset.label}
                  </button>
                );
              })}
            </div>
          </div>

          {zoneInputs.length > 0 && (
            <button
              type="button"
              onClick={() => setShowZones((s) => !s)}
              aria-pressed={showZones}
              className={
                showZones
                  ? "btn btn-sm border-accent-line text-accent"
                  : "btn btn-sm"
              }
              title={
                showZones
                  ? "Hide FVG zones"
                  : "Show FVG zones (5m, both directions)"
              }
            >
              FVG {showZones ? "on" : "off"}
            </button>
          )}

          <input
            type="range"
            min={0}
            max={Math.max(0, candles.length - 1)}
            value={cursorIndex}
            onChange={(e) => {
              setPlaying(false);
              setCursorIndex(Number.parseInt(e.target.value, 10));
            }}
            className="ml-auto min-w-[200px] flex-1 accent-[var(--accent)]"
            aria-label="Scrub timeline"
          />
        </div>
      </Card>

      <EntriesList bars={bars} entries={entries} cursorIndex={cursorIndex} />
    </div>
  );
}

function EntriesList({
  bars,
  entries,
  cursorIndex,
}: {
  bars: NonNullable<ReplayPayload["bars"]>;
  entries: NonNullable<ReplayPayload["entries"]>;
  cursorIndex: number;
}) {
  if (entries.length === 0) return null;
  const cursorTs = bars[cursorIndex]?.ts ?? bars[0]?.ts ?? null;
  const cursorMs = cursorTs ? new Date(cursorTs).getTime() : 0;
  return (
    <Card>
      <CardHead
        eyebrow={`entries · ${entries.length} this day`}
        title="Entry log"
      />
      <ul className="divide-y divide-line">
        {entries.map((e) => {
          const fired = new Date(e.entry_ts).getTime() <= cursorMs;
          return (
            <li
              key={e.trade_id}
              className={
                fired
                  ? "flex items-center gap-3 px-4 py-2 font-mono text-[12px] text-ink-1"
                  : "flex items-center gap-3 px-4 py-2 font-mono text-[12px] text-ink-4"
              }
            >
              <span className="w-20 text-ink-3">
                {new Date(e.entry_ts).toISOString().slice(11, 19)}
              </span>
              <span
                className={
                  e.side === "long"
                    ? "w-12 font-semibold text-pos"
                    : "w-12 font-semibold text-neg"
                }
              >
                {e.side.toUpperCase()}
              </span>
              <span className="w-20">@{e.entry_price.toFixed(2)}</span>
              {e.pnl !== null && e.pnl !== undefined ? (
                <span className={e.pnl >= 0 ? "text-pos" : "text-neg"}>
                  {e.pnl >= 0 ? "+" : "-"}${Math.abs(e.pnl).toFixed(0)}
                </span>
              ) : null}
              {e.exit_reason ? (
                <span className="text-ink-3">· {e.exit_reason}</span>
              ) : null}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
