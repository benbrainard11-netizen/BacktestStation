import type { components } from "@/lib/api/generated";

type EquityPoint = components["schemas"]["EquityPointRead"];

interface OverlaidEquityChartProps {
  a: { label: string; points: EquityPoint[] };
  b: { label: string; points: EquityPoint[] };
}

const WIDTH = 1000;
const HEIGHT = 220;
const PAD_X = 12;
const PAD_Y = 12;
const A_COLOR = "rgb(52 211 153)";
const B_COLOR = "rgb(96 165 250)";

export default function OverlaidEquityChart({ a, b }: OverlaidEquityChartProps) {
  if (a.points.length === 0 && b.points.length === 0) {
    return <p className="font-mono text-xs text-zinc-500">No equity data.</p>;
  }

  const allTs = [...a.points, ...b.points]
    .map((p) => new Date(p.ts).getTime())
    .filter((t) => !Number.isNaN(t));
  const tsMin = Math.min(...allTs);
  const tsMax = Math.max(...allTs);

  const allEquity = [...a.points, ...b.points].map((p) => p.equity);
  const eqMin = Math.min(0, ...allEquity);
  const eqMax = Math.max(0, ...allEquity);

  const aPath = linePath(a.points, tsMin, tsMax, eqMin, eqMax);
  const bPath = linePath(b.points, tsMin, tsMax, eqMin, eqMax);

  const zeroY = scaleY(0, eqMin, eqMax);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-4 font-mono text-[11px] text-zinc-400">
        <span className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-5" style={{ background: A_COLOR }} />
          {a.label} · final {formatFinal(a.points)}
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-5" style={{ background: B_COLOR }} />
          {b.label} · final {formatFinal(b.points)}
        </span>
      </div>
      <div className="relative border border-zinc-800 bg-zinc-950">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="block w-full"
          style={{ height: HEIGHT }}
        >
          <line
            x1={PAD_X}
            x2={WIDTH - PAD_X}
            y1={zeroY}
            y2={zeroY}
            stroke="rgb(39 39 42)"
            strokeWidth={1}
            vectorEffect="non-scaling-stroke"
          />
          {aPath ? (
            <path
              d={aPath}
              fill="none"
              stroke={A_COLOR}
              strokeWidth={1.2}
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
          {bPath ? (
            <path
              d={bPath}
              fill="none"
              stroke={B_COLOR}
              strokeWidth={1.2}
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-2 font-mono text-[10px] text-zinc-600">
          <div className="flex justify-between">
            <span>{eqMax.toFixed(0)}</span>
            <span>{formatDateShort(tsMin)} → {formatDateShort(tsMax)}</span>
          </div>
          <span>{eqMin.toFixed(0)}</span>
        </div>
      </div>
    </div>
  );
}

function linePath(
  points: EquityPoint[],
  tsMin: number,
  tsMax: number,
  eqMin: number,
  eqMax: number,
): string {
  if (points.length === 0) return "";
  return points
    .map((p, i) => {
      const t = new Date(p.ts).getTime();
      const x = scaleX(t, tsMin, tsMax);
      const y = scaleY(p.equity, eqMin, eqMax);
      return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function scaleX(t: number, tsMin: number, tsMax: number): number {
  const innerWidth = WIDTH - PAD_X * 2;
  if (tsMax === tsMin) return PAD_X;
  return PAD_X + ((t - tsMin) / (tsMax - tsMin)) * innerWidth;
}

function scaleY(value: number, min: number, max: number): number {
  const innerHeight = HEIGHT - PAD_Y * 2;
  if (max === min) return PAD_Y + innerHeight / 2;
  const ratio = (value - min) / (max - min);
  return PAD_Y + (1 - ratio) * innerHeight;
}

function formatFinal(points: EquityPoint[]): string {
  if (points.length === 0) return "—";
  const final = points[points.length - 1].equity;
  const sign = final > 0 ? "+" : "";
  return `${sign}${final.toFixed(2)}R`;
}

function formatDateShort(ms: number): string {
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toISOString().slice(0, 10);
}
