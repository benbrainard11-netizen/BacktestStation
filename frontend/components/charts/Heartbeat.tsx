import { chartTheme, type ChartTheme } from "./theme";

interface HeartbeatProps {
  width?: number;
  height?: number;
  theme?: ChartTheme;
  color?: string;
  /** When true (default), the trace breathes via opacity animation. */
  pulse?: boolean;
}

/**
 * Live-monitor ECG. Static path with optional CSS pulse on opacity.
 */
export default function Heartbeat({
  width = 320,
  height = 46,
  theme,
  color,
  pulse = true,
}: HeartbeatProps) {
  const t = theme ?? chartTheme;
  const c = color ?? t.pos;
  const pts: string[] = [];
  for (let x = 0; x < width; x++) {
    const cx = x % 80;
    let y = height / 2;
    if (cx > 30 && cx < 36) y = height / 2 - (cx - 30) * 4;
    else if (cx >= 36 && cx < 40) y = height / 2 + (cx - 36) * 5;
    else if (cx >= 40 && cx < 44) y = height / 2 - (cx - 40) * 2;
    pts.push(`${x},${y.toFixed(1)}`);
  }
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      style={{ display: "block" }}
      aria-hidden="true"
    >
      <line
        x1={0}
        x2={width}
        y1={height / 2}
        y2={height / 2}
        stroke={t.grid}
        strokeWidth={1}
      />
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={c}
        strokeWidth={1.3}
        className={pulse ? "animate-heartbeat-pulse" : ""}
      />
    </svg>
  );
}
