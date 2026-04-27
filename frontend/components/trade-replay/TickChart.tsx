"use client";

import {
  CandlestickSeries,
  ColorType,
  LineSeries,
  createChart,
  createSeriesMarkers,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type LineData,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";

import type { components } from "@/lib/api/generated";
import {
  binTicksToMicroCandles,
  bidLine,
  askLine,
  tickIndexAtMs,
} from "@/lib/trade-replay/binTicks";

type Window = components["schemas"]["TradeReplayWindowRead"];

const SPEED_PRESETS = [
  { label: "1x", ms: 1000 },
  { label: "5x", ms: 200 },
  { label: "30x", ms: 33 },
  { label: "60x", ms: 16 },
] as const;

interface Props {
  payload: Window;
}

export default function TickChart({ payload }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const bidRef = useRef<ISeriesApi<"Line"> | null>(null);
  const askRef = useRef<ISeriesApi<"Line"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const tickHandleRef = useRef<number | null>(null);

  const ticks = payload.ticks ?? [];
  const anchor = payload.anchor;

  const candles = useMemo<CandlestickData[]>(() => {
    return binTicksToMicroCandles(ticks).map((c) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
  }, [ticks]);

  const bidLineData = useMemo<LineData[]>(
    () => bidLine(ticks).map((p) => ({ time: p.time as Time, value: p.value })),
    [ticks],
  );
  const askLineData = useMemo<LineData[]>(
    () => askLine(ticks).map((p) => ({ time: p.time as Time, value: p.value })),
    [ticks],
  );

  const [cursorIndex, setCursorIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState<number>(SPEED_PRESETS[1].ms);

  const tickCount = ticks.length;

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
      timeScale: { timeVisible: true, secondsVisible: true },
      rightPriceScale: { borderColor: "#27272a" },
    });
    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      borderVisible: false,
    });
    const bid = chart.addSeries(LineSeries, {
      color: "rgba(34, 197, 94, 0.35)",
      lineWidth: 1,
      lastValueVisible: false,
      priceLineVisible: false,
    });
    const ask = chart.addSeries(LineSeries, {
      color: "rgba(239, 68, 68, 0.35)",
      lineWidth: 1,
      lastValueVisible: false,
      priceLineVisible: false,
    });

    chartRef.current = chart;
    candleRef.current = candle;
    bidRef.current = bid;
    askRef.current = ask;
    markersRef.current = createSeriesMarkers(candle, []);

    return () => {
      markersRef.current?.detach();
      markersRef.current = null;
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      bidRef.current = null;
      askRef.current = null;
    };
  }, []);

  // Push the visible slice of candles + bid/ask whenever cursor or data
  // changes. Cursor walks ticks; we map back to a wall-clock cutoff so
  // candles + lines stay synced.
  useEffect(() => {
    if (!candleRef.current || !bidRef.current || !askRef.current) return;

    const cutoffMs =
      ticks.length > 0
        ? new Date(
            ticks[Math.min(cursorIndex, ticks.length - 1)].ts,
          ).getTime()
        : 0;
    const cutoffSec = Math.floor(cutoffMs / 1000);

    candleRef.current.setData(candles.filter((c) => (c.time as number) <= cutoffSec));
    bidRef.current.setData(bidLineData.filter((p) => (p.time as number) <= cutoffSec));
    askRef.current.setData(askLineData.filter((p) => (p.time as number) <= cutoffSec));
    chartRef.current?.timeScale().fitContent();
  }, [candles, bidLineData, askLineData, cursorIndex, ticks]);

  // Anchor lines (entry, stop, target) — rendered as priceLines on the
  // candle series so they live forever, regardless of cursor.
  useEffect(() => {
    const series = candleRef.current;
    if (!series || !anchor) return;
    const lines = [
      {
        price: anchor.entry_price,
        color: "#a1a1aa",
        lineStyle: 0,
        lineWidth: 1 as const,
        title: `entry ${anchor.entry_price.toFixed(2)}`,
      },
    ];
    if (anchor.stop_price !== null && anchor.stop_price !== undefined) {
      lines.push({
        price: anchor.stop_price,
        color: "#ef4444",
        lineStyle: 2,
        lineWidth: 1 as const,
        title: `stop ${anchor.stop_price.toFixed(2)}`,
      });
    }
    if (anchor.target_price !== null && anchor.target_price !== undefined) {
      lines.push({
        price: anchor.target_price,
        color: "#22c55e",
        lineStyle: 2,
        lineWidth: 1 as const,
        title: `target ${anchor.target_price.toFixed(2)}`,
      });
    }
    const created = lines.map((l) => series.createPriceLine(l));
    return () => {
      for (const line of created) {
        try {
          series.removePriceLine(line);
        } catch {
          /* chart already torn down */
        }
      }
    };
  }, [anchor]);

  // Entry marker (and exit if available) on the candle series.
  useEffect(() => {
    if (!candleRef.current || !anchor) return;
    const candleTimes = new Set(candles.map((c) => c.time as number));
    const markers: SeriesMarker<Time>[] = [];
    const entrySec = Math.floor(new Date(anchor.entry_ts).getTime() / 1000);
    if (candleTimes.has(entrySec)) {
      const isLong = anchor.side.toLowerCase() === "long";
      markers.push({
        time: entrySec as Time,
        position: isLong ? "belowBar" : "aboveBar",
        color: isLong ? "#22c55e" : "#ef4444",
        shape: isLong ? "arrowUp" : "arrowDown",
        text: `entry ${anchor.side} @${anchor.entry_price.toFixed(2)}`,
      });
    }
    if (
      anchor.exit_ts &&
      anchor.exit_price !== null &&
      anchor.exit_price !== undefined
    ) {
      const exitSec = Math.floor(new Date(anchor.exit_ts).getTime() / 1000);
      if (candleTimes.has(exitSec)) {
        markers.push({
          time: exitSec as Time,
          position: "aboveBar",
          color: "#a1a1aa",
          shape: "circle",
          text: `exit @${anchor.exit_price.toFixed(2)}`,
        });
      }
    }
    markersRef.current?.setMarkers(markers);
  }, [anchor, candles]);

  // Playback tick. Each interval advances cursor by the number of ticks
  // covered in the last `speedMs * (1000 / SPEED_PRESETS[0].ms)`
  // milliseconds of *wall-clock data time*. Simpler: convert speed
  // multiplier × 1 second of data per second of wall-clock at 1x.
  useEffect(() => {
    if (!playing) {
      if (tickHandleRef.current !== null) {
        window.clearInterval(tickHandleRef.current);
        tickHandleRef.current = null;
      }
      return;
    }
    if (tickCount === 0) return;
    // Speed: SPEED_PRESETS[i].ms = wall-clock delay between frames.
    // Each frame should advance the cursor by 1 wall-clock-second-equivalent
    // worth of data, i.e. all ticks within the next 1s of ts_event.
    const advanceMsPerFrame = 1000;
    tickHandleRef.current = window.setInterval(() => {
      setCursorIndex((prev) => {
        if (prev >= tickCount - 1) {
          setPlaying(false);
          return prev;
        }
        const curMs = new Date(ticks[prev].ts).getTime();
        const targetMs = curMs + advanceMsPerFrame;
        const next = tickIndexAtMs(ticks, targetMs);
        if (next <= prev) return Math.min(prev + 1, tickCount - 1);
        return Math.min(next, tickCount - 1);
      });
    }, speedMs);
    return () => {
      if (tickHandleRef.current !== null) {
        window.clearInterval(tickHandleRef.current);
        tickHandleRef.current = null;
      }
    };
  }, [playing, speedMs, tickCount, ticks]);

  if (tickCount === 0) {
    return (
      <div className="border border-zinc-800 bg-zinc-950 p-6 font-mono text-xs text-zinc-500">
        No TBBO ticks in the trade window for {payload.symbol}.
      </div>
    );
  }

  const cursorTick = ticks[Math.min(cursorIndex, tickCount - 1)];
  const cursorTime = new Date(cursorTick.ts);
  const cursorMid =
    cursorTick.bid_px !== null && cursorTick.ask_px !== null
      ? (cursorTick.bid_px + cursorTick.ask_px) / 2
      : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="border border-zinc-800 bg-zinc-950 p-3">
        <div
          ref={containerRef}
          className="h-[480px] w-full"
          aria-label={`Tick chart for ${payload.symbol} around trade ${payload.trade_id}`}
        />
      </div>
      <div className="flex flex-wrap items-center gap-3 border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs">
        <button
          type="button"
          onClick={() => setCursorIndex(0)}
          className="border border-zinc-800 bg-zinc-900 px-2 py-1 hover:bg-zinc-800"
          title="Reset to first tick"
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
            setCursorIndex((prev) => Math.min(tickCount - 1, prev + 1))
          }
          className="border border-zinc-800 bg-zinc-900 px-2 py-1 hover:bg-zinc-800"
          title="Step forward 1 tick"
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
          max={Math.max(0, tickCount - 1)}
          value={cursorIndex}
          onChange={(e) => {
            setPlaying(false);
            setCursorIndex(Number.parseInt(e.target.value, 10));
          }}
          className="ml-2 flex-1 accent-zinc-500"
          aria-label="Scrub tick timeline"
        />
        <span className="ml-2 tabular-nums text-zinc-500">
          {cursorIndex + 1}/{tickCount}
        </span>
        <span className="tabular-nums text-zinc-400">
          {cursorTime.toISOString().slice(11, 23)} UTC
          {cursorMid !== null ? ` · mid ${cursorMid.toFixed(2)}` : ""}
        </span>
      </div>
    </div>
  );
}
