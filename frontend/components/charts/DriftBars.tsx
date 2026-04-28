import { chartTheme, type ChartTheme } from "./theme";

export interface DriftRow {
  metric: string;
  live: number;
  test: number;
  z: number;
  status: "ok" | "warn" | "stale";
}

interface DriftBarsProps {
  rows: DriftRow[];
  width?: number;
  height?: number;
  theme?: ChartTheme;
  title?: string | null;
}

/**
 * Horizontal twin-bar drift visualization. Each row shows test (muted) and
 * live (toned by status) against a common max, with z-score annotation.
 */
export default function DriftBars({
  rows,
  width = 720,
  height = 180,
  theme,
  title = null,
}: DriftBarsProps) {
  const t = theme ?? chartTheme;
  if (!rows.length) {
    return <svg viewBox={`0 0 ${width} ${height}`} />;
  }
  const ml = 80,
    mr = 60,
    mt = title ? 28 : 14,
    mb = 14;
  const innerW = width - ml - mr;
  const rowH = (height - mt - mb) / rows.length;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      {title ? (
        <text x={ml - 72} y={18} fontSize={12} fill={t.fg} fontWeight={600}>
          {title}
        </text>
      ) : null}
      {rows.map((r, i) => {
        const y = mt + i * rowH;
        const max =
          Math.max(Math.abs(r.live), Math.abs(r.test)) * 1.4 || 1;
        const liveW = (Math.abs(r.live) / max) * innerW;
        const testW = (Math.abs(r.test) / max) * innerW;
        const sevColor =
          r.status === "warn" ? t.neg : r.status === "ok" ? t.pos : t.mut;
        return (
          <g key={i}>
            <text
              x={ml - 8}
              y={y + rowH / 2 + 3}
              fontSize={10}
              fill={t.fg}
              textAnchor="end"
            >
              {r.metric}
            </text>
            <rect
              x={ml}
              y={y + 4}
              width={testW}
              height={(rowH - 12) / 2}
              fill={t.mut}
              opacity={0.45}
              rx={2}
            />
            <rect
              x={ml}
              y={y + 4 + (rowH - 12) / 2 + 2}
              width={liveW}
              height={(rowH - 12) / 2}
              fill={sevColor}
              opacity={0.85}
              rx={2}
            />
            <text
              x={ml + Math.max(testW, liveW) + 6}
              y={y + rowH / 2 + 3}
              fontSize={9.5}
              fill={sevColor}
              fontWeight={600}
            >
              z={r.z >= 0 ? "+" : ""}
              {r.z.toFixed(1)}
            </text>
          </g>
        );
      })}
      <text x={ml} y={height - 2} fontSize={8.5} fill={t.mut}>
        test
      </text>
      <text x={ml + 30} y={height - 2} fontSize={8.5} fill={t.mut}>
        live
      </text>
    </svg>
  );
}
