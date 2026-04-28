import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";
import type { SelectedPath } from "@/lib/prop-simulator/types";

interface EquityPathOverlayPanelProps {
 paths: SelectedPath[];
}

const BUCKET_TONE: Record<SelectedPath["bucket"], string> = {
 best: "stroke-pos",
 worst: "stroke-neg",
 median: "stroke-text-mute",
 near_fail: "stroke-neg/60",
 near_pass: "stroke-pos/60",
};

const BUCKET_LABEL: Record<SelectedPath["bucket"], string> = {
 best: "Best",
 worst: "Worst",
 median: "Median",
 near_fail: "Near-fail",
 near_pass: "Near-pass",
};

function PathLines({ paths, width, height }: { paths: SelectedPath[]; width: number; height: number }) {
 if (paths.length === 0) return null;

 const allPoints = paths.flatMap((p) => p.equity_curve);
 const min = Math.min(...allPoints);
 const max = Math.max(...allPoints);
 const range = max - min || 1;
 const maxLen = Math.max(...paths.map((p) => p.equity_curve.length));

 return (
 <svg
 viewBox={`0 0 ${width} ${height}`}
 className="block w-full"
 preserveAspectRatio="none"
 aria-hidden="true"
 >
 {paths.map((path) => {
 const stepX = width / Math.max(1, maxLen - 1);
 const points = path.equity_curve
 .map((v, i) => {
 const x = i * stepX;
 const y = height - ((v - min) / range) * height;
 return `${x.toFixed(1)},${y.toFixed(1)}`;
 })
 .join(" ");
 return (
 <polyline
 key={path.bucket}
 points={points}
 fill="none"
 strokeWidth={1.25}
 strokeLinecap="round"
 strokeLinejoin="round"
 className={BUCKET_TONE[path.bucket]}
 />
 );
 })}
 </svg>
 );
}

export default function EquityPathOverlayPanel({
 paths,
}: EquityPathOverlayPanelProps) {
 return (
 <Panel title="Equity path overlay" meta={`${paths.length} selected paths`}>
 <div className="flex flex-col gap-3">
 <div className="border border-border bg-surface p-3">
 <PathLines paths={paths} width={600} height={160} />
 </div>
 <div className="flex flex-wrap gap-3 tabular-nums text-[10px] text-text-dim">
 {paths.map((path) => (
 <span key={path.bucket} className="flex items-center gap-1.5">
 <span
 aria-hidden="true"
 className={cn(
 "h-[3px] w-4",
 path.bucket === "best" && "bg-pos",
 path.bucket === "near_pass" && "bg-pos/60",
 path.bucket === "median" && "bg-text-dim",
 path.bucket === "near_fail" && "bg-neg/60",
 path.bucket === "worst" && "bg-neg",
 )}
 />
 {BUCKET_LABEL[path.bucket]}
 </span>
 ))}
 </div>
 </div>
 </Panel>
 );
}
