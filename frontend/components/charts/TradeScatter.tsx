import { chartTheme, fmtR0, type ChartTheme } from "./theme";

export interface ScatterTrade {
  hold: number;
  r: number;
}

interface TradeScatterProps {
  trades: ScatterTrade[];
  width?: number;
  height?: number;
  theme?: ChartTheme;
  title?: string | null;
}

/**
 * Hold-time vs R scatter, colored by sign. X axis in minutes.
 */
export default function TradeScatter({
  trades,
  width = 720,
  height = 260,
  theme,
  title = null,
}: TradeScatterProps) {
  const t = theme ?? chartTheme;
  if (!trades.length) {
    return <svg viewBox={`0 0 ${width} ${height}`} />;
  }
  const ml = 40,
    mr = 14,
    mt = title ? 30 : 14,
    mb = 28;
  const innerW = width - ml - mr;
  const innerH = height - mt - mb;

  const xs = trades.map((d) => d.hold);
  const ys = trades.map((d) => d.r);
  const xMin = 0,
    xMax = Math.max(...xs) * 1.05;
  const yMin = Math.min(...ys, -3),
    yMax = Math.max(...ys, 3);
  const px = (x: number) => ml + (x / (xMax - xMin || 1)) * innerW;
  const py = (y: number) =>
    mt + innerH - ((y - yMin) / (yMax - yMin || 1)) * innerH;

  const xTicks = [0, 15, 30, 45, 60, 75, 90].filter(
    (v) => v >= xMin && v <= xMax,
  );
  const yTicks = [-3, -2, -1, 0, 1, 2, 3, 4, 5].filter(
    (v) => v >= yMin && v <= yMax,
  );

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

      {yTicks.map((tk, i) => (
        <g key={`y${i}`}>
          <line
            x1={ml}
            x2={width - mr}
            y1={py(tk)}
            y2={py(tk)}
            stroke={t.grid}
            strokeWidth={1}
            opacity={tk === 0 ? 0.7 : 1}
          />
          <text
            x={ml - 6}
            y={py(tk) + 3}
            fontSize={9}
            fill={t.mut}
            textAnchor="end"
          >
            {fmtR0(tk)}
          </text>
        </g>
      ))}

      {xTicks.map((tk, i) => (
        <text
          key={`x${i}`}
          x={px(tk)}
          y={mt + innerH + 14}
          fontSize={9}
          fill={t.mut}
          textAnchor="middle"
        >
          {tk}m
        </text>
      ))}

      {trades.map((d, i) => (
        <circle
          key={i}
          cx={px(d.hold)}
          cy={py(d.r)}
          r={2.5}
          fill={d.r >= 0 ? t.pos : t.neg}
          opacity={0.7}
        />
      ))}

      <text
        x={width - mr}
        y={mt + innerH + 14}
        fontSize={9}
        fill={t.mut}
        textAnchor="end"
      >
        hold time →
      </text>
    </svg>
  );
}
