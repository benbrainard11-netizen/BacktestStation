import type { Trade } from "@/lib/api/types";

interface ReplayChartProps {
  trade: Trade;
}

const WIDTH = 1000;
const HEIGHT = 300;
const PAD_X = 72;
const PAD_Y = 28;

/**
 * Minimalist schematic using only real trade data — no synthetic candles.
 * Shows the stop/target zones, entry and exit levels, and a straight-line
 * price path between the two known (ts, price) points. Real candle data
 * replaces this later when the Databento/parquet pipeline lands.
 */
export default function ReplayChart({ trade }: ReplayChartProps) {
  const entryTs = new Date(trade.entry_ts).getTime();
  const exitTs =
    trade.exit_ts !== null ? new Date(trade.exit_ts).getTime() : entryTs;

  // Give the plot breathing room: 15% of trade duration before/after,
  // minimum 5 min either side so single-bar trades still get a visible span.
  const duration = Math.max(5 * 60_000, exitTs - entryTs);
  const pad = Math.max(5 * 60_000, duration * 0.15);
  const startTs = entryTs - pad;
  const endTs = exitTs + pad;

  const isLong = trade.side === "long";
  const entry = trade.entry_price;
  const exit = trade.exit_price;
  const stop = trade.stop_price;
  const target = trade.target_price;

  const allPrices = [entry, exit, stop, target].filter(
    (v): v is number => v !== null,
  );
  const pMin = Math.min(...allPrices);
  const pMax = Math.max(...allPrices);
  const padding = (pMax - pMin) * 0.18 || 2;
  const yMin = pMin - padding;
  const yMax = pMax + padding;

  const entryX = scaleX(entryTs, startTs, endTs);
  const exitX = scaleX(exitTs, startTs, endTs);
  const entryY = scaleY(entry, yMin, yMax);
  const exitY = exit !== null ? scaleY(exit, yMin, yMax) : entryY;
  const stopY = stop !== null ? scaleY(stop, yMin, yMax) : null;
  const targetY = target !== null ? scaleY(target, yMin, yMax) : null;

  const sideColor = isLong ? "rgb(52 211 153)" : "rgb(244 63 94)";
  const pnlColor =
    trade.pnl === null || trade.pnl === 0
      ? "rgb(161 161 170)"
      : trade.pnl > 0
        ? "rgb(52 211 153)"
        : "rgb(244 63 94)";

  return (
    <div className="flex flex-col gap-2">
      <div className="border border-zinc-800 bg-zinc-950">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="block w-full"
          style={{ height: HEIGHT }}
        >
          {/* Stop zone: between entry and stop */}
          {stopY !== null ? (
            <Zone
              yTop={Math.min(entryY, stopY)}
              yBottom={Math.max(entryY, stopY)}
              xLeft={entryX}
              xRight={WIDTH - PAD_X}
              fill="rgb(244 63 94 / 0.08)"
            />
          ) : null}
          {/* Target zone: between entry and target */}
          {targetY !== null ? (
            <Zone
              yTop={Math.min(entryY, targetY)}
              yBottom={Math.max(entryY, targetY)}
              xLeft={entryX}
              xRight={WIDTH - PAD_X}
              fill="rgb(52 211 153 / 0.08)"
            />
          ) : null}

          {/* Horizontal levels */}
          <Level
            y={entryY}
            label={`entry ${entry.toFixed(2)}`}
            color="rgb(228 228 231)"
            solid
          />
          {targetY !== null ? (
            <Level
              y={targetY}
              label={`target ${target!.toFixed(2)}`}
              color="rgb(52 211 153)"
            />
          ) : null}
          {stopY !== null ? (
            <Level
              y={stopY}
              label={`stop ${stop!.toFixed(2)}`}
              color="rgb(244 63 94)"
            />
          ) : null}

          {/* Vertical time markers */}
          <TimeMarker x={entryX} label="entry" />
          {exit !== null && exitTs !== entryTs ? (
            <TimeMarker x={exitX} label="exit" />
          ) : null}

          {/* Price path — straight line from entry point to exit point */}
          {exit !== null ? (
            <line
              x1={entryX}
              x2={exitX}
              y1={entryY}
              y2={exitY}
              stroke={pnlColor}
              strokeWidth={1.5}
              strokeDasharray="2 3"
              vectorEffect="non-scaling-stroke"
            />
          ) : null}

          {/* Entry marker (side-colored) */}
          <Marker
            x={entryX}
            y={entryY}
            color={sideColor}
            label={isLong ? "LONG" : "SHORT"}
            size={7}
          />
          {/* Exit marker */}
          {exit !== null ? (
            <Marker
              x={exitX}
              y={exitY}
              color={pnlColor}
              label={`${trade.exit_reason ?? "exit"} ${exit.toFixed(2)}`}
              size={5}
              labelBelow
            />
          ) : null}
        </svg>
        <div className="flex justify-between border-t border-zinc-900 px-3 py-1 font-mono text-[10px] text-zinc-600">
          <span>{formatTs(startTs)}</span>
          <span>
            {formatTs(entryTs)}
            {exitTs !== entryTs ? ` → ${formatTs(exitTs)}` : ""}
          </span>
          <span>{formatTs(endTs)}</span>
        </div>
      </div>
      <p className="font-mono text-[10px] text-zinc-600">
        Schematic view — real price levels only. Tick-by-tick chart lands when the
        Databento data pipeline is wired.
      </p>
    </div>
  );
}

function Zone({
  yTop,
  yBottom,
  xLeft,
  xRight,
  fill,
}: {
  yTop: number;
  yBottom: number;
  xLeft: number;
  xRight: number;
  fill: string;
}) {
  return (
    <rect
      x={xLeft}
      y={yTop}
      width={Math.max(0, xRight - xLeft)}
      height={Math.max(0, yBottom - yTop)}
      fill={fill}
    />
  );
}

function Level({
  y,
  label,
  color,
  solid,
}: {
  y: number;
  label: string;
  color: string;
  solid?: boolean;
}) {
  return (
    <g>
      <line
        x1={PAD_X}
        x2={WIDTH - PAD_X}
        y1={y}
        y2={y}
        stroke={color}
        strokeWidth={1}
        strokeDasharray={solid ? undefined : "4 4"}
        strokeOpacity={solid ? 0.8 : 0.6}
        vectorEffect="non-scaling-stroke"
      />
      <text
        x={WIDTH - PAD_X + 4}
        y={y}
        dominantBaseline="middle"
        fontSize={10}
        fill={color}
        className="font-mono"
      >
        {label}
      </text>
    </g>
  );
}

function TimeMarker({ x, label }: { x: number; label: string }) {
  return (
    <g>
      <line
        x1={x}
        x2={x}
        y1={PAD_Y}
        y2={HEIGHT - PAD_Y}
        stroke="rgb(63 63 70)"
        strokeWidth={1}
        strokeDasharray="3 4"
        vectorEffect="non-scaling-stroke"
      />
      <text
        x={x}
        y={PAD_Y - 8}
        textAnchor="middle"
        fontSize={9}
        fill="rgb(113 113 122)"
        className="font-mono uppercase tracking-widest"
      >
        {label}
      </text>
    </g>
  );
}

function Marker({
  x,
  y,
  color,
  label,
  size,
  labelBelow,
}: {
  x: number;
  y: number;
  color: string;
  label: string;
  size: number;
  labelBelow?: boolean;
}) {
  return (
    <g>
      <circle cx={x} cy={y} r={size} fill={color} />
      <text
        x={x + size + 4}
        y={labelBelow ? y + size + 10 : y - size - 4}
        fontSize={10}
        fill={color}
        className="font-mono"
      >
        {label}
      </text>
    </g>
  );
}

function scaleX(ts: number, startTs: number, endTs: number): number {
  const innerWidth = WIDTH - PAD_X * 2;
  if (endTs === startTs) return WIDTH / 2;
  return PAD_X + ((ts - startTs) / (endTs - startTs)) * innerWidth;
}

function scaleY(value: number, min: number, max: number): number {
  const innerHeight = HEIGHT - PAD_Y * 2;
  if (max === min) return PAD_Y + innerHeight / 2;
  const ratio = (value - min) / (max - min);
  return PAD_Y + (1 - ratio) * innerHeight;
}

function formatTs(ms: number): string {
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) return "—";
  return `${date.toISOString().slice(0, 10)} ${date.toISOString().slice(11, 16)}`;
}
