import type { components } from "@/lib/api/generated";

type EquityPoint = components["schemas"]["EquityPointRead"];

interface EquityChartProps {
 points: EquityPoint[];
}

const WIDTH = 1000;
const EQUITY_HEIGHT = 180;
const DRAWDOWN_HEIGHT = 80;
const PAD_X = 8;
const PAD_Y = 8;

export default function EquityChart({ points }: EquityChartProps) {
 if (points.length === 0) {
 return (
 <p className="tabular-nums text-xs text-text-mute">No equity points.</p>
 );
 }

 const equityValues = points.map((p) => p.equity);
 const drawdownValues = points.map((p) => p.drawdown ?? 0);

 const equityPath = linePath(equityValues, EQUITY_HEIGHT);
 const drawdownPath = areaPath(drawdownValues, DRAWDOWN_HEIGHT);

 const equityMin = Math.min(...equityValues);
 const equityMax = Math.max(...equityValues);
 const drawdownMin = Math.min(...drawdownValues);

 const firstTs = points[0].ts;
 const lastTs = points[points.length - 1].ts;

 return (
 <div className="flex flex-col gap-4">
 <ChartBlock
 label="Equity curve"
 meta={`${points.length} points · ${formatDate(firstTs)} → ${formatDate(lastTs)}`}
 axisMin={equityMin}
 axisMax={equityMax}
 height={EQUITY_HEIGHT}
 >
 <path
 d={equityPath}
 fill="none"
 stroke="rgb(52 211 153)"
 strokeWidth={1.2}
 vectorEffect="non-scaling-stroke"
 />
 </ChartBlock>
 <ChartBlock
 label="Drawdown"
 meta={`min ${drawdownMin.toFixed(2)}`}
 axisMin={drawdownMin}
 axisMax={0}
 height={DRAWDOWN_HEIGHT}
 >
 <path d={drawdownPath} fill="rgb(244 63 94 / 0.25)" stroke="none" />
 <path
 d={linePath(drawdownValues, DRAWDOWN_HEIGHT)}
 fill="none"
 stroke="rgb(244 63 94)"
 strokeWidth={1}
 vectorEffect="non-scaling-stroke"
 />
 </ChartBlock>
 </div>
 );
}

function ChartBlock({
 label,
 meta,
 axisMin,
 axisMax,
 height,
 children,
}: {
 label: string;
 meta: string;
 axisMin: number;
 axisMax: number;
 height: number;
 children: React.ReactNode;
}) {
 return (
 <div className="border border-border bg-surface">
 <header className="flex items-center justify-between border-b border-border px-3 py-1.5">
 <span className="tabular-nums text-[10px] text-text-dim">
 {label}
 </span>
 <span className="tabular-nums text-[10px] text-text-mute">
 {meta}
 </span>
 </header>
 <div className="relative">
 <svg
 viewBox={`0 0 ${WIDTH} ${height}`}
 preserveAspectRatio="none"
 className="block w-full"
 style={{ height }}
 >
 <line
 x1={PAD_X}
 x2={WIDTH - PAD_X}
 y1={height - PAD_Y}
 y2={height - PAD_Y}
 stroke="rgb(39 39 42)"
 strokeWidth={1}
 vectorEffect="non-scaling-stroke"
 />
 {children}
 </svg>
 <div className="pointer-events-none absolute inset-0 flex items-start justify-between px-3 py-1 tabular-nums text-[10px] text-text-mute">
 <span>{axisMax.toFixed(2)}</span>
 <span>{axisMin.toFixed(2)}</span>
 </div>
 </div>
 </div>
 );
}

function linePath(values: number[], height: number): string {
 if (values.length === 0) return "";
 const min = Math.min(...values);
 const max = Math.max(...values);
 return values
 .map((value, i) => {
 const x = scaleX(i, values.length);
 const y = scaleY(value, min, max, height);
 return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
 })
 .join(" ");
}

function areaPath(values: number[], height: number): string {
 if (values.length === 0) return "";
 const min = Math.min(...values);
 const max = Math.max(...values);
 const baselineY = scaleY(0, min, max, height);
 const top = values
 .map((value, i) => {
 const x = scaleX(i, values.length);
 const y = scaleY(value, min, max, height);
 return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
 })
 .join(" ");
 const lastX = scaleX(values.length - 1, values.length).toFixed(2);
 const firstX = scaleX(0, values.length).toFixed(2);
 return `${top} L ${lastX} ${baselineY.toFixed(2)} L ${firstX} ${baselineY.toFixed(2)} Z`;
}

function scaleX(index: number, total: number): number {
 if (total <= 1) return PAD_X;
 const innerWidth = WIDTH - PAD_X * 2;
 return PAD_X + (index / (total - 1)) * innerWidth;
}

function scaleY(
 value: number,
 min: number,
 max: number,
 height: number,
): number {
 const innerHeight = height - PAD_Y * 2;
 if (max === min) return PAD_Y + innerHeight / 2;
 const ratio = (value - min) / (max - min);
 return PAD_Y + (1 - ratio) * innerHeight;
}

function formatDate(iso: string): string {
 const date = new Date(iso);
 if (Number.isNaN(date.getTime())) return iso;
 return date.toISOString().slice(0, 10);
}
