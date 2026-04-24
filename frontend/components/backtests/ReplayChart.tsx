import type { Trade } from "@/lib/api/types";

interface ReplayChartProps {
  trade: Trade;
}

const WIDTH = 1000;
const HEIGHT = 320;
const PAD_X = 32;
const PAD_Y = 24;
const CANDLES_BEFORE = 20;
const CANDLES_AFTER = 20;
const CANDLE_MINUTES = 1;

/**
 * Phase 1 mock chart. Renders synthetic OHLC candles around the real
 * entry/exit timestamps so the replay workflow has something visible;
 * the bars carry NO real market information. Replace with real bars from
 * the Databento/parquet pipeline in a later phase.
 */
export default function ReplayChart({ trade }: ReplayChartProps) {
  const entryTs = new Date(trade.entry_ts).getTime();
  const exitTs = trade.exit_ts !== null ? new Date(trade.exit_ts).getTime() : entryTs;

  const startTs = entryTs - CANDLES_BEFORE * CANDLE_MINUTES * 60_000;
  const endTs = exitTs + CANDLES_AFTER * CANDLE_MINUTES * 60_000;

  const candles = generateSyntheticCandles(trade, startTs, endTs);

  const allPrices = [
    ...candles.flatMap((c) => [c.h, c.l]),
    trade.entry_price,
    trade.exit_price ?? trade.entry_price,
    trade.stop_price ?? trade.entry_price,
    trade.target_price ?? trade.entry_price,
  ];
  const pMin = Math.min(...allPrices);
  const pMax = Math.max(...allPrices);
  const padding = (pMax - pMin) * 0.08 || 1;
  const yMin = pMin - padding;
  const yMax = pMax + padding;

  const isLong = trade.side === "long";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between border border-amber-900/60 bg-amber-950/30 px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-amber-300">
        <span>Synthetic candle data — for layout only, not real market bars</span>
        <span className="text-amber-500/80">mock</span>
      </div>
      <div className="border border-zinc-800 bg-zinc-950">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="block w-full"
          style={{ height: HEIGHT }}
        >
          <PriceLine
            price={trade.entry_price}
            yMin={yMin}
            yMax={yMax}
            color="rgb(161 161 170)"
            label={`entry ${fmtPrice(trade.entry_price)}`}
          />
          {trade.exit_price !== null ? (
            <PriceLine
              price={trade.exit_price}
              yMin={yMin}
              yMax={yMax}
              color="rgb(161 161 170)"
              label={`exit ${fmtPrice(trade.exit_price)}`}
              dashed
            />
          ) : null}
          {trade.stop_price !== null ? (
            <PriceLine
              price={trade.stop_price}
              yMin={yMin}
              yMax={yMax}
              color="rgb(244 63 94)"
              label={`stop ${fmtPrice(trade.stop_price)}`}
            />
          ) : null}
          {trade.target_price !== null ? (
            <PriceLine
              price={trade.target_price}
              yMin={yMin}
              yMax={yMax}
              color="rgb(52 211 153)"
              label={`target ${fmtPrice(trade.target_price)}`}
            />
          ) : null}

          {candles.map((c, i) => {
            const x = scaleX(c.ts, startTs, endTs);
            const highY = scaleY(c.h, yMin, yMax);
            const lowY = scaleY(c.l, yMin, yMax);
            const openY = scaleY(c.o, yMin, yMax);
            const closeY = scaleY(c.c, yMin, yMax);
            const bullish = c.c >= c.o;
            const color = bullish ? "rgb(52 211 153 / 0.6)" : "rgb(244 63 94 / 0.6)";
            const bodyTop = Math.min(openY, closeY);
            const bodyH = Math.max(1, Math.abs(closeY - openY));
            return (
              <g key={i}>
                <line
                  x1={x}
                  x2={x}
                  y1={highY}
                  y2={lowY}
                  stroke={color}
                  strokeWidth={1}
                  vectorEffect="non-scaling-stroke"
                />
                <rect
                  x={x - 2.5}
                  y={bodyTop}
                  width={5}
                  height={bodyH}
                  fill={color}
                />
              </g>
            );
          })}

          <Marker
            ts={entryTs}
            price={trade.entry_price}
            startTs={startTs}
            endTs={endTs}
            yMin={yMin}
            yMax={yMax}
            color={isLong ? "rgb(52 211 153)" : "rgb(244 63 94)"}
            label={isLong ? "LONG" : "SHORT"}
          />
          {trade.exit_price !== null && trade.exit_ts !== null ? (
            <Marker
              ts={new Date(trade.exit_ts).getTime()}
              price={trade.exit_price}
              startTs={startTs}
              endTs={endTs}
              yMin={yMin}
              yMax={yMax}
              color="rgb(161 161 170)"
              label="EXIT"
              small
            />
          ) : null}
        </svg>
        <div className="flex justify-between border-t border-zinc-900 px-3 py-1 font-mono text-[10px] text-zinc-600">
          <span>{formatTs(startTs)}</span>
          <span>entry {formatTs(entryTs)}</span>
          <span>{formatTs(endTs)}</span>
        </div>
      </div>
    </div>
  );
}

function PriceLine({
  price,
  yMin,
  yMax,
  color,
  label,
  dashed,
}: {
  price: number;
  yMin: number;
  yMax: number;
  color: string;
  label: string;
  dashed?: boolean;
}) {
  const y = scaleY(price, yMin, yMax);
  return (
    <g>
      <line
        x1={PAD_X}
        x2={WIDTH - PAD_X}
        y1={y}
        y2={y}
        stroke={color}
        strokeWidth={1}
        strokeDasharray={dashed ? "4 4" : undefined}
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

function Marker({
  ts,
  price,
  startTs,
  endTs,
  yMin,
  yMax,
  color,
  label,
  small,
}: {
  ts: number;
  price: number;
  startTs: number;
  endTs: number;
  yMin: number;
  yMax: number;
  color: string;
  label: string;
  small?: boolean;
}) {
  const x = scaleX(ts, startTs, endTs);
  const y = scaleY(price, yMin, yMax);
  const radius = small ? 4 : 6;
  return (
    <g>
      <circle cx={x} cy={y} r={radius} fill={color} />
      <text
        x={x + radius + 3}
        y={y - radius - 2}
        fontSize={10}
        fill={color}
        className="font-mono"
      >
        {label}
      </text>
    </g>
  );
}

interface Candle {
  ts: number;
  o: number;
  h: number;
  l: number;
  c: number;
}

function generateSyntheticCandles(
  trade: Trade,
  startTs: number,
  endTs: number,
): Candle[] {
  // deterministic pseudo-random walk seeded by trade id so replays are stable
  let state = trade.id * 2654435761;
  const rand = () => {
    state = Math.imul(state ^ (state >>> 15), 2246822507);
    state = Math.imul(state ^ (state >>> 13), 3266489909);
    state ^= state >>> 16;
    return (state >>> 0) / 4294967295;
  };

  const step = CANDLE_MINUTES * 60_000;
  const totalBars = Math.max(2, Math.round((endTs - startTs) / step));
  const entryTs = new Date(trade.entry_ts).getTime();
  const exitTs =
    trade.exit_ts !== null ? new Date(trade.exit_ts).getTime() : entryTs;

  const volatility = Math.max(
    1,
    Math.abs((trade.stop_price ?? trade.entry_price) - trade.entry_price) * 0.2,
  );

  let price = trade.entry_price + (rand() - 0.5) * volatility * 4;
  const candles: Candle[] = [];

  for (let i = 0; i < totalBars; i++) {
    const ts = startTs + i * step;
    const isEntryBar = Math.abs(ts - entryTs) < step / 2;
    const isExitBar = Math.abs(ts - exitTs) < step / 2;

    const drift = (rand() - 0.5) * volatility;
    const o = price;
    let c = o + drift;
    const h = Math.max(o, c) + rand() * volatility * 0.6;
    const l = Math.min(o, c) - rand() * volatility * 0.6;
    if (isEntryBar) {
      c = trade.entry_price;
    } else if (isExitBar && trade.exit_price !== null) {
      c = trade.exit_price;
    }
    candles.push({ ts, o, h, l, c });
    price = c;
  }
  return candles;
}

function scaleX(ts: number, startTs: number, endTs: number): number {
  const innerWidth = WIDTH - PAD_X * 2;
  if (endTs === startTs) return PAD_X;
  return PAD_X + ((ts - startTs) / (endTs - startTs)) * innerWidth;
}

function scaleY(value: number, min: number, max: number): number {
  const innerHeight = HEIGHT - PAD_Y * 2;
  if (max === min) return PAD_Y + innerHeight / 2;
  const ratio = (value - min) / (max - min);
  return PAD_Y + (1 - ratio) * innerHeight;
}

function fmtPrice(value: number): string {
  return value.toFixed(2);
}

function formatTs(ms: number): string {
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) return "—";
  return `${date.toISOString().slice(0, 10)} ${date.toISOString().slice(11, 16)}`;
}
