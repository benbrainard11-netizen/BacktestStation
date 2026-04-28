import { chartTheme, fmtR, fmtR0, fmtShortDate, niceTicks, type ChartTheme } from "./theme";

export interface EquityPoint {
  i: number;
  r: number;
  dd: number;
  ts: string;
}

interface EquityCurveProps {
  points: EquityPoint[];
  width?: number;
  height?: number;
  theme?: ChartTheme;
  /** Show drawdown sub-panel beneath the curve. */
  showDD?: boolean;
  /** Optional vertical marker (x = point index). */
  marker?: number | null;
  title?: string | null;
  subtitle?: string | null;
}

/**
 * Equity curve with optional stacked drawdown sub-panel. Annotates peak,
 * trough, and the last value with chips. Pure SVG.
 */
export default function EquityCurve({
  points,
  width = 720,
  height = 300,
  theme,
  showDD = true,
  marker = null,
  title = null,
  subtitle = null,
}: EquityCurveProps) {
  const t = theme ?? chartTheme;
  if (points.length === 0) {
    return (
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%" }} />
    );
  }
  const ml = 48,
    mr = 16,
    mt = title ? 36 : 14,
    mb = 28;
  const ddH = showDD ? 64 : 0;
  const gap = showDD ? 18 : 0;
  const eqH = height - mt - mb - ddH - gap;

  const xs = points.map((p) => p.i);
  const ys = points.map((p) => p.r);
  const dds = points.map((p) => p.dd);
  const xMin = Math.min(...xs),
    xMax = Math.max(...xs);
  const yMin = Math.min(0, ...ys),
    yMax = Math.max(...ys);
  const ddMin = Math.min(...dds);

  const px = (x: number) =>
    ml + ((x - xMin) / (xMax - xMin || 1)) * (width - ml - mr);
  const eqY = (y: number) =>
    mt + eqH - ((y - yMin) / (yMax - yMin || 1)) * eqH;
  const ddY = (y: number) =>
    mt + eqH + gap + ddH - ((y - ddMin) / (0 - ddMin || 1)) * ddH;

  const eqTicks = niceTicks(yMin, yMax, 4);
  const ddTicks = niceTicks(ddMin, 0, 2);

  const xTickIdx: number[] = [];
  const N = 6;
  for (let i = 0; i < N; i++)
    xTickIdx.push(Math.round(xMin + (xMax - xMin) * (i / (N - 1))));

  const linePath = points
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"}${px(p.i).toFixed(1)} ${eqY(p.r).toFixed(1)}`,
    )
    .join(" ");
  const areaPath = `${linePath} L${px(xMax).toFixed(1)} ${eqY(yMin).toFixed(1)} L${px(xMin).toFixed(1)} ${eqY(yMin).toFixed(1)} Z`;
  const ddPath = points
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"}${px(p.i).toFixed(1)} ${ddY(p.dd).toFixed(1)}`,
    )
    .join(" ");
  const ddArea = `${ddPath} L${px(xMax).toFixed(1)} ${ddY(0).toFixed(1)} L${px(xMin).toFixed(1)} ${ddY(0).toFixed(1)} Z`;

  const peakIdx = points.reduce(
    (b, p, i) => (p.r > points[b].r ? i : b),
    0,
  );
  const troughIdx = points.reduce(
    (b, p, i) => (p.dd < points[b].dd ? i : b),
    0,
  );
  const lastIdx = points.length - 1;
  const last = points[lastIdx];

  const gradId = `eqgrad-${Math.random().toString(36).slice(2, 8)}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      <defs>
        <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={t.pos} stopOpacity="0.22" />
          <stop offset="100%" stopColor={t.pos} stopOpacity="0" />
        </linearGradient>
      </defs>

      {title ? (
        <g>
          <text x={ml} y={18} fontSize={12} fill={t.fg} fontWeight={600}>
            {title}
          </text>
          {subtitle ? (
            <text x={ml} y={32} fontSize={10} fill={t.mut}>
              {subtitle}
            </text>
          ) : null}
        </g>
      ) : null}

      {eqTicks.map((tk, i) => (
        <g key={`eg${i}`}>
          <line
            x1={ml}
            x2={width - mr}
            y1={eqY(tk)}
            y2={eqY(tk)}
            stroke={t.grid}
            strokeWidth={1}
            opacity={tk === 0 ? 0.6 : 1}
          />
          <text
            x={ml - 6}
            y={eqY(tk) + 3}
            fontSize={9}
            fill={t.mut}
            textAnchor="end"
          >
            {fmtR0(tk)}
          </text>
        </g>
      ))}

      <path d={areaPath} fill={`url(#${gradId})`} />
      <path
        d={linePath}
        fill="none"
        stroke={t.pos}
        strokeWidth={1.4}
        strokeLinejoin="round"
      />

      <g>
        <circle
          cx={px(peakIdx)}
          cy={eqY(points[peakIdx].r)}
          r={2.5}
          fill={t.pos}
        />
        <line
          x1={px(peakIdx)}
          x2={px(peakIdx)}
          y1={eqY(points[peakIdx].r) - 6}
          y2={eqY(points[peakIdx].r) - 16}
          stroke={t.mut}
          strokeWidth={1}
        />
        <text
          x={px(peakIdx)}
          y={eqY(points[peakIdx].r) - 20}
          fontSize={9}
          fill={t.fg}
          textAnchor="middle"
        >
          peak {fmtR0(points[peakIdx].r)}
        </text>
      </g>

      <g>
        <circle cx={px(lastIdx)} cy={eqY(last.r)} r={3} fill={t.fg} />
        <rect
          x={px(lastIdx) - 36}
          y={eqY(last.r) - 22}
          width={72}
          height={16}
          rx={3}
          fill={t.panel}
          stroke={t.grid}
        />
        <text
          x={px(lastIdx)}
          y={eqY(last.r) - 11}
          fontSize={9.5}
          fill={t.fg}
          textAnchor="middle"
        >
          {fmtR(last.r)}
        </text>
      </g>

      {marker !== null && marker >= xMin && marker <= xMax ? (
        <line
          x1={px(marker)}
          x2={px(marker)}
          y1={mt}
          y2={mt + eqH}
          stroke={t.fg}
          strokeWidth={1}
          strokeDasharray="2 3"
          opacity={0.5}
        />
      ) : null}

      {!showDD &&
        xTickIdx.map((xi, i) => (
          <text
            key={`xt${i}`}
            x={px(xi)}
            y={mt + eqH + 14}
            fontSize={9}
            fill={t.mut}
            textAnchor="middle"
          >
            {fmtShortDate(points[xi].ts)}
          </text>
        ))}

      {showDD ? (
        <g>
          <text x={ml} y={mt + eqH + gap - 4} fontSize={9} fill={t.mut}>
            drawdown
          </text>
          {ddTicks.map((tk, i) => (
            <g key={`dt${i}`}>
              <line
                x1={ml}
                x2={width - mr}
                y1={ddY(tk)}
                y2={ddY(tk)}
                stroke={t.grid}
                strokeWidth={1}
                opacity={tk === 0 ? 0.6 : 1}
              />
              <text
                x={ml - 6}
                y={ddY(tk) + 3}
                fontSize={9}
                fill={t.mut}
                textAnchor="end"
              >
                {fmtR0(tk)}
              </text>
            </g>
          ))}
          <path d={ddArea} fill={t.neg} opacity={0.18} />
          <path d={ddPath} fill="none" stroke={t.neg} strokeWidth={1.2} />
          <circle
            cx={px(troughIdx)}
            cy={ddY(points[troughIdx].dd)}
            r={2.5}
            fill={t.neg}
          />
          <text
            x={px(troughIdx)}
            y={ddY(points[troughIdx].dd) + 12}
            fontSize={9}
            fill={t.neg}
            textAnchor="middle"
          >
            trough {fmtR(points[troughIdx].dd)}
          </text>
          {xTickIdx.map((xi, i) => (
            <text
              key={`xtb${i}`}
              x={px(xi)}
              y={mt + eqH + gap + ddH + 14}
              fontSize={9}
              fill={t.mut}
              textAnchor="middle"
            >
              {fmtShortDate(points[xi].ts)}
            </text>
          ))}
        </g>
      ) : null}
    </svg>
  );
}
