import { chartTheme, fmtR, niceTicks, type ChartTheme } from "./theme";

export interface Bar {
  ts: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

export interface CandleTrade {
  id: number;
  side: "long" | "short";
  entry_i: number;
  exit_i: number;
  entry: number;
  exit: number;
  r: number;
}

interface CandlesProps {
  bars: Bar[];
  trades?: CandleTrade[];
  width?: number;
  height?: number;
  theme?: ChartTheme;
  /** Optional vertical marker (bar index). */
  marker?: number | null;
  title?: string | null;
}

/**
 * Candlestick chart with volume sub-panel and overlay trade markers.
 * Each trade is drawn as a dashed line from entry to exit with side-tinted
 * markers and an R label at the exit.
 */
export default function Candles({
  bars,
  trades = [],
  width = 900,
  height = 380,
  theme,
  marker = null,
  title = null,
}: CandlesProps) {
  const t = theme ?? chartTheme;
  if (!bars.length) {
    return <svg viewBox={`0 0 ${width} ${height}`} />;
  }
  const ml = 8,
    mr = 56,
    mt = title ? 30 : 12,
    mb = 22;
  const volH = 56;
  const gap = 6;
  const priceH = height - mt - mb - volH - gap;

  const highs = bars.map((b) => b.h);
  const lows = bars.map((b) => b.l);
  const yMax = Math.max(...highs);
  const yMin = Math.min(...lows);
  const pad = (yMax - yMin) * 0.05;
  const lo = yMin - pad,
    hi = yMax + pad;

  const cw = (width - ml - mr) / bars.length;
  const px = (i: number) => ml + i * cw + cw / 2;
  const py = (p: number) =>
    mt + priceH - ((p - lo) / (hi - lo || 1)) * priceH;

  const vMax = Math.max(...bars.map((b) => b.v)) || 1;
  const vY = (v: number) =>
    mt + priceH + gap + volH - (v / vMax) * volH;

  const yTicks = niceTicks(lo, hi, 5);

  const xTickIdx: number[] = [];
  for (let i = 0; i < bars.length; i += 12) xTickIdx.push(i);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      {title ? (
        <text x={ml + 4} y={18} fontSize={12} fill={t.fg} fontWeight={600}>
          {title}
        </text>
      ) : null}

      {yTicks.map((tk, i) => (
        <g key={`y${i}`}>
          <line
            x1={ml}
            x2={width - mr}
            y1={py(tk)}
            y2={py(tk)}
            stroke={t.grid}
            strokeWidth={1}
          />
          <text x={width - mr + 6} y={py(tk) + 3} fontSize={9} fill={t.mut}>
            {tk.toFixed(2)}
          </text>
        </g>
      ))}

      {bars.map((b, i) => {
        const up = b.c >= b.o;
        const x = px(i);
        const bodyTop = py(Math.max(b.o, b.c));
        const bodyBot = py(Math.min(b.o, b.c));
        const w = Math.max(2, cw - 1.6);
        return (
          <g key={`b${i}`}>
            <line
              x1={x}
              x2={x}
              y1={py(b.h)}
              y2={py(b.l)}
              stroke={up ? t.pos : t.neg}
              strokeWidth={1}
            />
            <rect
              x={x - w / 2}
              y={bodyTop}
              width={w}
              height={Math.max(1, bodyBot - bodyTop)}
              fill={up ? t.pos : t.neg}
              opacity={0.9}
            />
          </g>
        );
      })}

      {trades.map((tr, i) => {
        const x1 = px(tr.entry_i),
          x2 = px(tr.exit_i);
        const y1 = py(tr.entry),
          y2 = py(tr.exit);
        const col = tr.r >= 0 ? t.pos : t.neg;
        return (
          <g key={`t${i}`}>
            <line
              x1={x1}
              x2={x2}
              y1={y1}
              y2={y2}
              stroke={col}
              strokeWidth={1.4}
              strokeDasharray="3 2"
            />
            <circle
              cx={x1}
              cy={y1}
              r={3.5}
              fill={t.panel}
              stroke={col}
              strokeWidth={1.4}
            />
            <circle
              cx={x2}
              cy={y2}
              r={3.5}
              fill={col}
              stroke={col}
              strokeWidth={1.4}
            />
            <text
              x={x1}
              y={y1 - 7}
              fontSize={8.5}
              fill={col}
              textAnchor="middle"
            >
              {tr.side === "long" ? "▲" : "▼"} #{tr.id}
            </text>
            <text
              x={x2}
              y={y2 + 12}
              fontSize={8.5}
              fill={col}
              textAnchor="middle"
            >
              {fmtR(tr.r)}
            </text>
          </g>
        );
      })}

      {marker !== null && marker >= 0 && marker < bars.length ? (
        <line
          x1={px(marker)}
          x2={px(marker)}
          y1={mt}
          y2={mt + priceH}
          stroke={t.fg}
          strokeWidth={1}
          strokeDasharray="2 3"
          opacity={0.6}
        />
      ) : null}

      {bars.map((b, i) => {
        const up = b.c >= b.o;
        const x = px(i);
        const w = Math.max(2, cw - 1.6);
        const top = vY(b.v);
        return (
          <rect
            key={`v${i}`}
            x={x - w / 2}
            y={top}
            width={w}
            height={mt + priceH + gap + volH - top}
            fill={up ? t.pos : t.neg}
            opacity={0.4}
          />
        );
      })}

      {xTickIdx.map((xi, i) => (
        <text
          key={`xt${i}`}
          x={px(xi)}
          y={height - 6}
          fontSize={9}
          fill={t.mut}
          textAnchor="middle"
        >
          {bars[xi].ts.slice(11, 16)}
        </text>
      ))}

      <text
        x={width - mr + 6}
        y={mt + priceH + gap + 8}
        fontSize={9}
        fill={t.mut}
      >
        vol
      </text>
    </svg>
  );
}
