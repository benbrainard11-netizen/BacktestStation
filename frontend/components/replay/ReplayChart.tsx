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
import { useEffect, useMemo, useRef, useState } from "react";

import type { components } from "@/lib/api/generated";

type ReplayPayload = components["schemas"]["ReplayPayload"];

const SPEED_PRESETS = [
  { label: "1x", ms: 1000 },
  { label: "5x", ms: 200 },
  { label: "30x", ms: 33 },
  { label: "60x", ms: 16 },
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

  const bars = payload.bars ?? [];
  const entries = payload.entries ?? [];
  const candles: CandlestickData[] = useMemo(
    () =>
      bars.map((b) => ({
        time: (Math.floor(new Date(b.ts).getTime() / 1000) as Time),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    [bars],
  );

  // Mount the chart once.
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#09090b" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#27272a" },
        horzLines: { color: "#27272a" },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: "#27272a" },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      borderVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;
    // v5 markers are a series-attached primitive, not a series method.
    markersRef.current = createSeriesMarkers(series, []);
    return () => {
      markersRef.current?.detach();
      markersRef.current = null;
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Push the visible slice of candles whenever cursor moves or data changes.
  useEffect(() => {
    if (!seriesRef.current) return;
    const visible = candles.slice(0, Math.max(1, cursorIndex + 1));
    seriesRef.current.setData(visible);
    chartRef.current?.timeScale().fitContent();
  }, [candles, cursorIndex]);

  // Entry markers on the candle series. Markers stay at fixed positions;
  // they "appear" as the cursor reaches their bar because we only render
  // the visible slice.
  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) return;
    const candleTimeSet = new Set(candles.map((c) => c.time));
    const markers: SeriesMarker<Time>[] = entries
      .map((e) => {
        const ts = (Math.floor(new Date(e.entry_ts).getTime() / 1000) as Time);
        if (!candleTimeSet.has(ts)) return null;
        const isLong = e.side.toLowerCase() === "long";
        const pnlText =
          e.pnl !== null && e.pnl !== undefined
            ? ` ${e.pnl >= 0 ? "+" : ""}${e.pnl.toFixed(0)}`
            : "";
        return {
          time: ts,
          position: isLong ? "belowBar" : "aboveBar",
          color: isLong ? "#22c55e" : "#ef4444",
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
      <div className="border border-zinc-800 bg-zinc-950 p-6 font-mono text-xs text-zinc-500">
        No bars in the warehouse for {payload.symbol} on{" "}
        {String(payload.date)}. The data may not be backfilled for this date,
        or the symbol may not be in the universe.
      </div>
    );
  }

  const currentBar = bars[cursorIndex];
  return (
    <div className="flex flex-col gap-3">
      <div className="border border-zinc-800 bg-zinc-950 p-3">
        <div
          ref={containerRef}
          className="h-[480px] w-full"
          aria-label={`Replay chart for ${payload.symbol} on ${String(payload.date)}`}
        />
      </div>
      <div className="flex items-center gap-3 border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs">
        <button
          type="button"
          onClick={() => setCursorIndex(0)}
          className="border border-zinc-800 bg-zinc-900 px-2 py-1 hover:bg-zinc-800"
          title="Reset to first bar"
        >
          ⏮
        </button>
        <button
          type="button"
          onClick={() => setPlaying((p) => !p)}
          className="border border-zinc-700 bg-zinc-900 px-3 py-1 hover:bg-zinc-800"
        >
          {playing ? "⏸ Pause" : "▶ Play"}
        </button>
        <button
          type="button"
          onClick={() =>
            setCursorIndex((prev) => Math.min(candles.length - 1, prev + 1))
          }
          className="border border-zinc-800 bg-zinc-900 px-2 py-1 hover:bg-zinc-800"
          title="Step forward 1 bar"
        >
          ⏭
        </button>
        <span className="text-zinc-500">Speed</span>
        {SPEED_PRESETS.map((preset) => (
          <button
            key={preset.label}
            type="button"
            onClick={() => setSpeedMs(preset.ms)}
            className={
              speedMs === preset.ms
                ? "border border-zinc-100 bg-zinc-100 px-2 py-1 text-zinc-950"
                : "border border-zinc-800 bg-zinc-900 px-2 py-1 hover:bg-zinc-800"
            }
          >
            {preset.label}
          </button>
        ))}
        <input
          type="range"
          min={0}
          max={Math.max(0, candles.length - 1)}
          value={cursorIndex}
          onChange={(e) => {
            setPlaying(false);
            setCursorIndex(Number.parseInt(e.target.value, 10));
          }}
          className="ml-2 flex-1 accent-zinc-500"
          aria-label="Scrub timeline"
        />
        <span className="ml-2 tabular-nums text-zinc-500">
          {cursorIndex + 1}/{candles.length}
        </span>
        {currentBar ? (
          <span className="tabular-nums text-zinc-400">
            {new Date(currentBar.ts).toISOString().slice(11, 19)} UTC ·{" "}
            {currentBar.close.toFixed(2)}
          </span>
        ) : null}
      </div>
      <EntriesList
        bars={bars}
        entries={entries}
        cursorIndex={cursorIndex}
      />
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
    <div className="border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs">
      <p className="mb-2 uppercase tracking-widest text-[10px] text-zinc-500">
        Entries this day ({entries.length})
      </p>
      <ul className="flex flex-col gap-1">
        {entries.map((e) => {
          const fired = new Date(e.entry_ts).getTime() <= cursorMs;
          return (
            <li
              key={e.trade_id}
              className={
                fired
                  ? "text-zinc-200"
                  : "text-zinc-600"
              }
            >
              {new Date(e.entry_ts).toISOString().slice(11, 19)} UTC{" "}
              <span
                className={
                  e.side === "long" ? "text-emerald-300" : "text-rose-300"
                }
              >
                {e.side.toUpperCase()}
              </span>{" "}
              @{e.entry_price.toFixed(2)}
              {e.pnl !== null && e.pnl !== undefined
                ? ` · ${e.pnl >= 0 ? "+" : ""}$${Math.abs(e.pnl).toFixed(0)}${
                    e.pnl >= 0 ? "" : " loss"
                  }`
                : ""}
              {e.exit_reason ? ` · ${e.exit_reason}` : ""}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
