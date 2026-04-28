import { chartTheme, fmtR, type ChartTheme } from "./theme";

export interface HistogramBin {
  lo: number;
  hi: number;
  bin: string;
  count: number;
}

interface RHistogramProps {
  bins: HistogramBin[];
  width?: number;
  height?: number;
  theme?: ChartTheme;
  /** Mark expectancy with a vertical dashed line + chip. */
  expectancy?: number | null;
  title?: string | null;
}

/**
 * R-multiple distribution histogram. Negative bars are tone-neg, the small
 * "0R" bin is muted, and positive bars are tone-pos. Optionally annotates
 * expectancy with a vertical line.
 */
export default function RHistogram({
  bins,
  width = 720,
  height = 240,
  theme,
  expectancy = null,
  title = null,
}: RHistogramProps) {
  const t = theme ?? chartTheme;
  if (!bins.length) {
    return <svg viewBox={`0 0 ${width} ${height}`} />;
  }
  const ml = 36,
    mr = 16,
    mt = title ? 32 : 14,
    mb = 36;
  const innerW = width - ml - mr;
  const innerH = height - mt - mb;
  const max = Math.max(...bins.map((b) => b.count)) || 1;
  const total = bins.reduce((s, b) => s + b.count, 0);
  const bw = innerW / bins.length;

  const yTicks = [
    0,
    Math.ceil((max * 0.5) / 5) * 5,
    Math.ceil(max / 5) * 5,
  ];

  const allHi = bins[bins.length - 1].hi;
  const allLo = bins[0].lo;
  const eX =
    expectancy === null
      ? null
      : ml + ((expectancy - allLo) / (allHi - allLo)) * innerW;

  const zeroIdx = bins.findIndex((b) => b.lo === 0);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      {title ? (
        <text x={ml} y={18} fontSize={12} fill={t.fg} fontWeight={600}>
          {title}
        </text>
      ) : null}

      {yTicks.map((tk, i) => {
        const denom = yTicks[yTicks.length - 1] || 1;
        const y = mt + innerH - (tk / denom) * innerH;
        return (
          <g key={`y${i}`}>
            <line
              x1={ml}
              x2={width - mr}
              y1={y}
              y2={y}
              stroke={t.grid}
              strokeWidth={1}
            />
            <text
              x={ml - 6}
              y={y + 3}
              fontSize={9}
              fill={t.mut}
              textAnchor="end"
            >
              {tk}
            </text>
          </g>
        );
      })}

      {zeroIdx >= 0 ? (
        <line
          x1={ml + zeroIdx * bw}
          x2={ml + zeroIdx * bw}
          y1={mt}
          y2={mt + innerH}
          stroke={t.axis}
          strokeWidth={1}
          strokeDasharray="2 3"
          opacity={0.6}
        />
      ) : null}

      {bins.map((b, i) => {
        const h = (b.count / max) * innerH;
        const x = ml + i * bw;
        const isNeg = b.hi <= 0;
        const isZero = b.lo === 0 && b.hi === 1;
        const fill = isNeg ? t.neg : isZero ? t.mut : t.pos;
        return (
          <g key={i}>
            <rect
              x={x + 2}
              y={mt + innerH - h}
              width={bw - 4}
              height={h}
              fill={fill}
              opacity={0.9}
              rx={1.5}
            />
            {b.count > 0 ? (
              <text
                x={x + bw / 2}
                y={mt + innerH - h - 4}
                fontSize={9}
                textAnchor="middle"
                fill={t.fg}
              >
                {b.count}
              </text>
            ) : null}
            <text
              x={x + bw / 2}
              y={mt + innerH + 14}
              fontSize={9.5}
              textAnchor="middle"
              fill={t.mut}
            >
              {b.bin}
            </text>
          </g>
        );
      })}

      {eX !== null && expectancy !== null ? (
        <g>
          <line
            x1={eX}
            x2={eX}
            y1={mt}
            y2={mt + innerH}
            stroke={t.brand}
            strokeWidth={1.3}
            strokeDasharray="3 2"
          />
          <rect
            x={eX + 4}
            y={mt + 4}
            width={86}
            height={16}
            rx={3}
            fill={t.panel}
            stroke={t.grid}
          />
          <text x={eX + 8} y={mt + 14.5} fontSize={9.5} fill={t.fg}>
            E = {fmtR(expectancy)}
          </text>
        </g>
      ) : null}

      <text x={ml} y={height - 6} fontSize={9} fill={t.mut}>
        n={total} · wins=
        {bins.filter((b) => b.lo >= 1).reduce((s, b) => s + b.count, 0)} ·
        losses=
        {bins.filter((b) => b.hi <= 0).reduce((s, b) => s + b.count, 0)}
      </text>
    </svg>
  );
}
