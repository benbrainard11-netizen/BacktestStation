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
import {
  chartTimeFormatter,
  etHM,
  etHMS,
  utcMs,
} from "@/lib/trade-replay/etFormat";

type Window = components["schemas"]["TradeReplayWindowRead"];

/** Snap a target second to the nearest candle time at or before it. */
function nearestCandleSec(
  candles: CandlestickData[],
  targetSec: number,
): number | null {
  let last: number | null = null;
  for (const c of candles) {
    const t = c.time as number;
    if (t > targetSec) break;
    last = t;
  }
  return last;
}

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

  const candles = useMemo<CandlestickData[]>(
    () =>
      binTicksToMicroCandles(ticks).map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    [ticks],
  );

  const bidLineData = useMemo<LineData[]>(
    () => bidLine(ticks).map((p) => ({ time: p.time as Time, value: p.value })),
    [ticks],
  );
  const askLineData = useMemo<LineData[]>(
    () => askLine(ticks).map((p) => ({ time: p.time as Time, value: p.value })),
    [ticks],
  );

  const tickCount = ticks.length;
  const entryMs = useMemo(() => utcMs(anchor.entry_ts), [anchor.entry_ts]);
  const initialCursor = useMemo(() => {
    if (tickCount === 0) return 0;
    return Math.min(tickCount - 1, tickIndexAtMs(ticks, entryMs));
  }, [ticks, tickCount, entryMs]);

  const [cursorIndex, setCursorIndex] = useState(initialCursor);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState<number>(SPEED_PRESETS[1].ms);

  // Reset cursor to entry whenever new payload loads.
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
        secondsVisible: true,
        borderColor: "#27272a",
        tickMarkFormatter: (time: Time) => etHM(Number(time) * 1000),
      },
      rightPriceScale: { borderColor: "#27272a" },
      localization: { timeFormatter: chartTimeFormatter },
    });
    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      borderVisible: false,
    });
    const bid = chart.addSeries(LineSeries, {
      color: "rgba(34, 197, 94, 0.6)",
      lineWidth: 1,
      lastValueVisible: false,
      priceLineVisible: false,
    });
    const ask = chart.addSeries(LineSeries, {
      color: "rgba(239, 68, 68, 0.6)",
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

  // Visible slice up to the cursor (in tick time). Don't auto-fit on
  // every cursor change; the user's pan/zoom takes precedence after
  // the initial layout below.
  useEffect(() => {
    if (!candleRef.current || !bidRef.current || !askRef.current) return;
    if (ticks.length === 0) return;
    const cutoffMs = new Date(
      ticks[Math.min(cursorIndex, ticks.length - 1)].ts,
    ).getTime();
    const cutoffSec = Math.floor(cutoffMs / 1000);

    candleRef.current.setData(
      candles.filter((c) => (c.time as number) <= cutoffSec),
    );
    bidRef.current.setData(
      bidLineData.filter((p) => (p.time as number) <= cutoffSec),
    );
    askRef.current.setData(
      askLineData.filter((p) => (p.time as number) <= cutoffSec),
    );
  }, [candles, bidLineData, askLineData, cursorIndex, ticks]);

  // Initial / on-data-change viewport: fit content once.
  const lastDatasetRef = useRef<CandlestickData[] | null>(null);
  useEffect(() => {
    if (!chartRef.current || candles.length === 0) return;
    if (lastDatasetRef.current === candles) return;
    lastDatasetRef.current = candles;
    chartRef.current.timeScale().fitContent();
  }, [candles]);

  // Entry / stop / target reveal as cursor passes entry. Series are
  // mounted on data change; their data updates on cursor change.
  const entrySeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const stopSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const targetSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || candles.length === 0) return;

    const entrySeries = chart.addSeries(LineSeries, {
      color: "#fde047",
      lineWidth: 2,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    const stopSeries =
      anchor.stop_price !== null && anchor.stop_price !== undefined
        ? chart.addSeries(LineSeries, {
            color: "#fb7185",
            lineWidth: 1,
            lineStyle: 2,
            lastValueVisible: false,
            priceLineVisible: false,
            crosshairMarkerVisible: false,
          })
        : null;
    const targetSeries =
      anchor.target_price !== null && anchor.target_price !== undefined
        ? chart.addSeries(LineSeries, {
            color: "#86efac",
            lineWidth: 1,
            lineStyle: 2,
            lastValueVisible: false,
            priceLineVisible: false,
            crosshairMarkerVisible: false,
          })
        : null;

    entrySeriesRef.current = entrySeries;
    stopSeriesRef.current = stopSeries;
    targetSeriesRef.current = targetSeries;

    return () => {
      try {
        chart.removeSeries(entrySeries);
        if (stopSeries) chart.removeSeries(stopSeries);
        if (targetSeries) chart.removeSeries(targetSeries);
      } catch {
        /* chart torn down */
      }
      entrySeriesRef.current = null;
      stopSeriesRef.current = null;
      targetSeriesRef.current = null;
    };
  }, [anchor, candles]);

  useEffect(() => {
    const entrySeries = entrySeriesRef.current;
    if (!entrySeries) return;
    if (candles.length === 0 || ticks.length === 0) {
      entrySeries.setData([]);
      stopSeriesRef.current?.setData([]);
      targetSeriesRef.current?.setData([]);
      return;
    }

    const entryCandleSec = nearestCandleSec(candles, Math.floor(entryMs / 1000));
    const cursorMsLocal = new Date(
      ticks[Math.min(cursorIndex, ticks.length - 1)].ts,
    ).getTime();
    const cursorSec = Math.floor(cursorMsLocal / 1000);

    if (entryCandleSec === null || cursorSec < entryCandleSec) {
      entrySeries.setData([]);
      stopSeriesRef.current?.setData([]);
      targetSeriesRef.current?.setData([]);
      return;
    }

    const exitMs = anchor.exit_ts ? utcMs(anchor.exit_ts) : null;
    const exitCandleSec =
      exitMs !== null
        ? (nearestCandleSec(candles, Math.floor(exitMs / 1000)) ??
          (candles[candles.length - 1].time as number))
        : (candles[candles.length - 1].time as number);
    const rightEndSec = Math.min(cursorSec, exitCandleSec);

    const seg = (price: number): LineData[] => [
      { time: entryCandleSec as Time, value: price },
      { time: rightEndSec as Time, value: price },
    ];

    entrySeries.setData(seg(anchor.entry_price));
    if (
      stopSeriesRef.current &&
      anchor.stop_price !== null &&
      anchor.stop_price !== undefined
    ) {
      stopSeriesRef.current.setData(seg(anchor.stop_price));
    }
    if (
      targetSeriesRef.current &&
      anchor.target_price !== null &&
      anchor.target_price !== undefined
    ) {
      targetSeriesRef.current.setData(seg(anchor.target_price));
    }
  }, [anchor, candles, cursorIndex, ticks, entryMs]);

  // Entry/exit markers.
  useEffect(() => {
    if (!candleRef.current) return;
    const candleTimes = new Set(candles.map((c) => c.time as number));
    const markers: SeriesMarker<Time>[] = [];
    const entrySec = Math.floor(entryMs / 1000);
    if (candleTimes.has(entrySec)) {
      const isLong = anchor.side.toLowerCase() === "long";
      markers.push({
        time: entrySec as Time,
        position: isLong ? "belowBar" : "aboveBar",
        color: isLong ? "#22c55e" : "#ef4444",
        shape: isLong ? "arrowUp" : "arrowDown",
        text: `${anchor.side.toUpperCase()} @${anchor.entry_price.toFixed(2)} · ${etHMS(entryMs)}`,
      });
    }
    if (anchor.exit_ts && anchor.exit_price !== null && anchor.exit_price !== undefined) {
      const exitSec = Math.floor(utcMs(anchor.exit_ts) / 1000);
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
  }, [anchor, candles, entryMs]);

  // Playback. 1x = 1 wall-clock-second of data per UI second.
  useEffect(() => {
    if (!playing) {
      if (tickHandleRef.current !== null) {
        window.clearInterval(tickHandleRef.current);
        tickHandleRef.current = null;
      }
      return;
    }
    if (tickCount === 0) return;
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
  const cursorMs = new Date(cursorTick.ts).getTime();
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
        <button
          type="button"
          onClick={() => {
            setCursorIndex(initialCursor);
            setPlaying(false);
            chartRef.current?.timeScale().fitContent();
          }}
          className="border border-zinc-700 bg-zinc-900 px-2 py-1 hover:bg-zinc-800"
          title="Jump cursor + viewport back to trade entry"
        >
          ↺ Entry
        </button>
        <button
          type="button"
          onClick={() => chartRef.current?.timeScale().fitContent()}
          className="border border-zinc-800 bg-zinc-900 px-2 py-1 hover:bg-zinc-800"
          title="Fit all ticks in view (TradingView 'A')"
        >
          Fit
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
        <span className="tabular-nums text-zinc-300">
          {etHMS(cursorMs)} ET
          {cursorMid !== null ? ` · mid ${cursorMid.toFixed(2)}` : ""}
        </span>
      </div>
    </div>
  );
}
