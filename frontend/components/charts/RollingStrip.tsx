import { chartTheme, type ChartTheme } from "./theme";

interface RollingStripProps {
  values: number[];
  width?: number;
  height?: number;
  theme?: ChartTheme;
  color?: string;
  label?: string | null;
  baseline?: number | null;
  fmt?: (v: number) => string;
}

/**
 * Thin axis-less rolling-metric strip. Annotates min/max on the left,
 * latest value on the right, and an optional baseline reference line.
 */
export default function RollingStrip({
  values,
  width = 720,
  height = 70,
  theme,
  color,
  label = null,
  baseline = null,
  fmt,
}: RollingStripProps) {
  const t = theme ?? chartTheme;
  const c = color ?? t.brand;
  if (!values.length) {
    return <svg viewBox={`0 0 ${width} ${height}`} />;
  }
  const ml = 36,
    mr = 36,
    mt = label ? 18 : 6,
    mb = 14;
  const innerW = width - ml - mr;
  const innerH = height - mt - mb;
  const lo = Math.min(...values, baseline ?? Infinity);
  const hi = Math.max(...values, baseline ?? -Infinity);
  const px = (i: number) =>
    values.length === 1 ? ml : ml + (i / (values.length - 1)) * innerW;
  const py = (v: number) =>
    mt + innerH - ((v - lo) / (hi - lo || 1)) * innerH;
  const path = values
    .map(
      (v, i) =>
        `${i === 0 ? "M" : "L"}${px(i).toFixed(1)} ${py(v).toFixed(1)}`,
    )
    .join(" ");

  const fmtV = (v: number) => (fmt ? fmt(v) : v.toFixed(2));
  const last = values[values.length - 1];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      {label ? (
        <text x={ml} y={12} fontSize={10} fill={t.mut}>
          {label}
        </text>
      ) : null}
      <text
        x={ml - 6}
        y={py(hi) + 3}
        fontSize={8.5}
        fill={t.mut}
        textAnchor="end"
      >
        {fmtV(hi)}
      </text>
      <text
        x={ml - 6}
        y={py(lo) + 3}
        fontSize={8.5}
        fill={t.mut}
        textAnchor="end"
      >
        {fmtV(lo)}
      </text>
      {baseline !== null ? (
        <g>
          <line
            x1={ml}
            x2={width - mr}
            y1={py(baseline)}
            y2={py(baseline)}
            stroke={t.grid}
            strokeWidth={1}
            strokeDasharray="2 3"
          />
          <text
            x={width - mr + 4}
            y={py(baseline) + 3}
            fontSize={8.5}
            fill={t.mut}
          >
            {fmtV(baseline)}
          </text>
        </g>
      ) : null}
      <path d={path} fill="none" stroke={c} strokeWidth={1.3} />
      <text
        x={width - mr + 4}
        y={py(last) + 3}
        fontSize={9}
        fill={c}
        fontWeight={600}
      >
        {fmtV(last)}
      </text>
    </svg>
  );
}
