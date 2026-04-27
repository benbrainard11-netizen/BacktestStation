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
import { chartTimeFormatter, etHMS } from "@/lib/trade-replay/etFormat";
import {
  type ResampledBar,
  type Timeframe,
  barIndexAtSec,
  resample,
} from "@/lib/trade-replay/resampleBars";

type ReplayBar = components["schemas"]["ReplayBar"];
type Anchor = components["schemas"]["TradeReplayAnchor"];

const SPEED_PRESETS = [
  { label: "1x", ms: 1000 },
  { label: "5x", ms: 200 },
  { label: "30x", ms: 33 },
  { label: "60x", ms: 16 },
] as const;

interface Props {
  bars: ReplayBar[];
  anchor: Anchor;
  timeframe: Timeframe;
}

export default function BarChart({ bars, anchor, timeframe }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const tickHandleRef = useRef<number | null>(null);

  const candles = useMemo<ResampledBar[]>(
    () => resample(bars, timeframe),
    [bars, timeframe],
  );
  const candleData = useMemo<CandlestickData[]>(
    () =>
      candles.map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    [candles],
  );

  const entrySec = useMemo(
    () => Math.floor(new Date(anchor.entry_ts).getTime() / 1000),
    [anchor.entry_ts],
  );

  // Cursor starts on the bar containing the trade entry — that's the
  // whole point of "review old trade." We initialize once per timeframe
  // change so resampling resets the index appropriately.
  const initialCursor = useMemo(() => {
    const idx = barIndexAtSec(candles, entrySec);
    // Show a few bars after entry by default so user sees the immediate
    // outcome bars without scrubbing.
    return Math.min(candles.length - 1, idx + 5);
  }, [candles, entrySec]);

  const [cursorIndex, setCursorIndex] = useState(initialCursor);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState<number>(SPEED_PRESETS[1].ms);

  // Reset cursor whenever data or timeframe changes.
  useEffect(() => {
    setCursorIndex(initialCursor);
    setPlaying(false);
  }, [initialCursor]);

  // Mount chart once.
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
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: "#27272a",
      },
      rightPriceScale: { borderColor: "#27272a" },
      localization: {
        timeFormatter: chartTimeFormatter,
      },
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
    markersRef.current = createSeriesMarkers(series, []);
    return () => {
      markersRef.current?.detach();
      markersRef.current = null;
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Visible slice of candles up to cursor.
  useEffect(() => {
    if (!seriesRef.current) return;
    seriesRef.current.setData(candleData.slice(0, Math.max(1, cursorIndex + 1)));
    chartRef.current?.timeScale().fitContent();
  }, [candleData, cursorIndex]);

  // Anchor lines on the candle series — entry, stop, target stay
  // visible regardless of cursor position. Drawn as price lines so
  // they're labeled.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    const lines = [
      series.createPriceLine({
        price: anchor.entry_price,
        color: "#fde047",
        lineStyle: 0,
        lineWidth: 2 as const,
        title: `entry ${anchor.entry_price.toFixed(2)}`,
      }),
    ];
    if (anchor.stop_price !== null && anchor.stop_price !== undefined) {
      lines.push(
        series.createPriceLine({
          price: anchor.stop_price,
          color: "#fb7185",
          lineStyle: 2,
          lineWidth: 1 as const,
          title: `stop ${anchor.stop_price.toFixed(2)}`,
        }),
      );
    }
    if (anchor.target_price !== null && anchor.target_price !== undefined) {
      lines.push(
        series.createPriceLine({
          price: anchor.target_price,
          color: "#86efac",
          lineStyle: 2,
          lineWidth: 1 as const,
          title: `target ${anchor.target_price.toFixed(2)}`,
        }),
      );
    }
    return () => {
      for (const l of lines) {
        try {
          series.removePriceLine(l);
        } catch {
          /* chart torn down */
        }
      }
    };
  }, [anchor]);

  // Entry / exit markers. Entry maps to the bar that contains entry_ts;
  // exit similarly. Both stay visible on the chart at all times.
  useEffect(() => {
    if (!seriesRef.current) return;
    const candleTimes: Time[] = candles.map((c) => c.time as Time);
    if (candleTimes.length === 0) {
      markersRef.current?.setMarkers([]);
      return;
    }

    const entryBucket = bucketAt(candleTimes, entrySec);
    const markers: SeriesMarker<Time>[] = [];
    if (entryBucket !== null) {
      const isLong = anchor.side.toLowerCase() === "long";
      markers.push({
        time: entryBucket as Time,
        position: isLong ? "belowBar" : "aboveBar",
        color: isLong ? "#22c55e" : "#ef4444",
        shape: isLong ? "arrowUp" : "arrowDown",
        text: `${anchor.side.toUpperCase()} @${anchor.entry_price.toFixed(2)} · ${etHMS(new Date(anchor.entry_ts).getTime())}`,
      });
    }
    if (anchor.exit_ts && anchor.exit_price !== null && anchor.exit_price !== undefined) {
      const exitSec = Math.floor(new Date(anchor.exit_ts).getTime() / 1000);
      const exitBucket = bucketAt(candleTimes, exitSec);
      if (exitBucket !== null) {
        markers.push({
          time: exitBucket as Time,
          position: "aboveBar",
          color: "#a1a1aa",
          shape: "circle",
          text: `exit @${anchor.exit_price.toFixed(2)}`,
        });
      }
    }
    markersRef.current?.setMarkers(markers);
  }, [anchor, candles, entrySec]);

  // Playback tick — advances 1 candle per setInterval fire.
  useEffect(() => {
    if (!playing) {
      if (tickHandleRef.current !== null) {
        window.clearInterval(tickHandleRef.current);
        tickHandleRef.current = null;
      }
      return;
    }
    if (candles.length === 0) return;
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
        No bars in the warehouse for this trade's date.
      </div>
    );
  }

  const cursorBar = candles[Math.min(cursorIndex, candles.length - 1)];
  const cursorMs = cursorBar.time * 1000;

  return (
    <div className="flex flex-col gap-3">
      <div className="border border-zinc-800 bg-zinc-950 p-3">
        <div
          ref={containerRef}
          className="h-[480px] w-full"
          aria-label={`Trade replay chart, ${timeframe} candles`}
        />
      </div>
      <div className="flex flex-wrap items-center gap-3 border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs">
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
        <button
          type="button"
          onClick={() => {
            const idx = barIndexAtSec(candles, entrySec);
            setCursorIndex(Math.min(candles.length - 1, idx + 5));
            setPlaying(false);
          }}
          className="border border-zinc-700 bg-zinc-900 px-2 py-1 hover:bg-zinc-800"
          title="Jump to trade entry"
        >
          ↺ Entry
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
        <span className="tabular-nums text-zinc-300">
          {etHMS(cursorMs)} ET · {cursorBar.close.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

/**
 * Given a sorted list of candle epoch-seconds and a target epoch-second,
 * find the candle whose bucket contains the target. Returns the candle's
 * `time` (its bucket open second) or null if outside the range.
 */
function bucketAt(candleTimes: Time[], targetSec: number): Time | null {
  let last: Time | null = null;
  for (const t of candleTimes) {
    if ((t as number) > targetSec) break;
    last = t;
  }
  return last;
}
