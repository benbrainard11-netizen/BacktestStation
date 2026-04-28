import { chartTheme, type ChartTheme } from "./theme";

interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
  theme?: ChartTheme;
  /** Hide the area fill — line-only sparkline. */
  noFill?: boolean;
  /** Override stroke + area fill color. Defaults to theme.pos. */
  color?: string;
}

/**
 * Inline sparkline. 84×22 in StatTiles, 90×22 in tables, larger in panels.
 * Pure SVG, no axis. Renders the area at ~18% opacity by default.
 */
export default function Sparkline({
  values,
  width = 120,
  height = 28,
  theme,
  noFill,
  color,
}: SparklineProps) {
  const t = theme ?? chartTheme;
  const c = color ?? t.pos;
  if (!values || values.length === 0) {
    return <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} />;
  }
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const px = (i: number) =>
    values.length === 1 ? width / 2 : (i / (values.length - 1)) * width;
  const py = (v: number) =>
    height - 2 - ((v - lo) / (hi - lo || 1)) * (height - 4);
  const path = values
    .map(
      (v, i) =>
        `${i === 0 ? "M" : "L"}${px(i).toFixed(1)} ${py(v).toFixed(1)}`,
    )
    .join(" ");
  const area = `${path} L${width} ${height} L0 ${height} Z`;
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      style={{ display: "block" }}
      aria-hidden="true"
    >
      {!noFill && <path d={area} fill={c} opacity={0.18} />}
      <path d={path} fill="none" stroke={c} strokeWidth={1.3} />
    </svg>
  );
}
