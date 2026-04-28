import { chartTheme, type ChartTheme } from "./theme";

export interface HourCell {
  di: number;
  hi: number;
  r: number;
}

export interface HourHeatmapData {
  days: string[];
  hours: string[];
  cells: HourCell[];
}

interface HourHeatmapProps {
  data: HourHeatmapData;
  width?: number;
  height?: number;
  theme?: ChartTheme;
  title?: string | null;
}

/**
 * Hour-of-day × day-of-week heatmap. Cell value = avg R per cell.
 */
export default function HourHeatmap({
  data,
  width = 720,
  height = 180,
  theme,
  title = null,
}: HourHeatmapProps) {
  const t = theme ?? chartTheme;
  const ml = 38,
    mr = 14,
    mt = title ? 30 : 18,
    mb = 18;
  const { days, hours, cells } = data;
  if (!days.length || !hours.length || !cells.length) {
    return <svg viewBox={`0 0 ${width} ${height}`} />;
  }
  const cellW = (width - ml - mr) / hours.length;
  const cellH = (height - mt - mb) / days.length;
  const max = Math.max(...cells.map((c) => Math.abs(c.r))) || 1;
  const colorFor = (r: number) => {
    const a = Math.min(1, Math.abs(r) / max);
    const c = r >= 0 ? t.pos : t.neg;
    return { fill: c, opacity: 0.15 + 0.7 * a };
  };

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

      {hours.map((h, i) => (
        <text
          key={`h${i}`}
          x={ml + i * cellW + cellW / 2}
          y={mt - 4}
          fontSize={9}
          fill={t.mut}
          textAnchor="middle"
        >
          {h}
        </text>
      ))}

      {days.map((d, di) => (
        <g key={`d${d}`}>
          <text
            x={ml - 6}
            y={mt + di * cellH + cellH / 2 + 3}
            fontSize={9}
            fill={t.fg}
            textAnchor="end"
          >
            {d}
          </text>
          {hours.map((h, hi) => {
            const cell = cells.find((c) => c.di === di && c.hi === hi);
            if (!cell) return null;
            const col = colorFor(cell.r);
            return (
              <g key={`c${d}${h}`}>
                <rect
                  x={ml + hi * cellW + 1}
                  y={mt + di * cellH + 1}
                  width={cellW - 2}
                  height={cellH - 2}
                  rx={2}
                  fill={col.fill}
                  opacity={col.opacity}
                />
                <text
                  x={ml + hi * cellW + cellW / 2}
                  y={mt + di * cellH + cellH / 2 + 3}
                  fontSize={9}
                  fill={t.fg}
                  textAnchor="middle"
                >
                  {cell.r >= 0 ? "+" : ""}
                  {cell.r.toFixed(1)}
                </text>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}
