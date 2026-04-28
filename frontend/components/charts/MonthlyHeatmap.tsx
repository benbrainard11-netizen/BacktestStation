import { chartTheme, fmtR0, type ChartTheme } from "./theme";

export interface MonthlyCell {
  year: number;
  mi: number;
  r: number;
}

export interface MonthlyHeatmapData {
  years: number[];
  months: string[];
  grid: MonthlyCell[];
}

interface MonthlyHeatmapProps {
  data: MonthlyHeatmapData;
  width?: number;
  height?: number;
  theme?: ChartTheme;
  title?: string | null;
}

/**
 * Year × month R heatmap with row-total YTD column on the right. Cell color
 * intensity scales with |R| / max|R|.
 */
export default function MonthlyHeatmap({
  data,
  width = 720,
  height = 180,
  theme,
  title = null,
}: MonthlyHeatmapProps) {
  const t = theme ?? chartTheme;
  const ml = 38,
    mr = 60,
    mt = title ? 30 : 14,
    mb = 18;
  const { years, months, grid } = data;
  if (!years.length || !months.length || !grid.length) {
    return <svg viewBox={`0 0 ${width} ${height}`} />;
  }
  const cellW = (width - ml - mr) / months.length;
  const cellH = (height - mt - mb) / years.length;
  const max = Math.max(...grid.map((g) => Math.abs(g.r))) || 1;

  const colorFor = (r: number) => {
    const a = Math.min(1, Math.abs(r) / max);
    const c = r >= 0 ? t.pos : t.neg;
    return { fill: c, opacity: 0.15 + 0.7 * a };
  };

  const totals = years.map((y) =>
    grid.filter((g) => g.year === y).reduce((s, g) => s + g.r, 0),
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

      {months.map((m, i) => (
        <text
          key={`m${i}`}
          x={ml + i * cellW + cellW / 2}
          y={mt - 4}
          fontSize={9}
          fill={t.mut}
          textAnchor="middle"
        >
          {m}
        </text>
      ))}

      {years.map((y, yi) => (
        <g key={`y${y}`}>
          <text
            x={ml - 6}
            y={mt + yi * cellH + cellH / 2 + 3}
            fontSize={9}
            fill={t.fg}
            textAnchor="end"
          >
            {y}
          </text>
          {months.map((m, mi) => {
            const cell = grid.find((g) => g.year === y && g.mi === mi);
            if (!cell) return null;
            const c = colorFor(cell.r);
            return (
              <g key={`c${y}${m}`}>
                <rect
                  x={ml + mi * cellW + 1}
                  y={mt + yi * cellH + 1}
                  width={cellW - 2}
                  height={cellH - 2}
                  rx={2}
                  fill={c.fill}
                  opacity={c.opacity}
                />
                <text
                  x={ml + mi * cellW + cellW / 2}
                  y={mt + yi * cellH + cellH / 2 + 3}
                  fontSize={9.5}
                  fill={t.fg}
                  textAnchor="middle"
                >
                  {fmtR0(cell.r)}
                </text>
              </g>
            );
          })}
          <text
            x={width - mr + 8}
            y={mt + yi * cellH + cellH / 2 + 3}
            fontSize={10}
            fill={totals[yi] >= 0 ? t.pos : t.neg}
            fontWeight={600}
          >
            {fmtR0(totals[yi])}
          </text>
        </g>
      ))}

      <text x={width - mr + 8} y={mt - 4} fontSize={9} fill={t.mut}>
        ytd
      </text>
    </svg>
  );
}
