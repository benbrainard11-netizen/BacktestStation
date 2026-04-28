// Polar radar/spider chart for confidence subscores. Pure SVG. Supports
// any number of axes (used by both 6-axis backtest confidence and
// 7-axis simulator confidence). Renders concentric reference rings, an
// axis spoke per label, an emerald-tinted filled polygon connecting
// the score points, and a tick label at each axis tip.

import { cn } from "@/lib/utils";

interface ConfidenceRadarProps {
 rows: { label: string; score: number }[];
 size?: number;
 className?: string;
}

// 0,0 = center. We emit polar → cartesian inline.
function polar(centerX: number, centerY: number, radius: number, angleRad: number) {
 return {
 x: centerX + Math.cos(angleRad) * radius,
 y: centerY + Math.sin(angleRad) * radius,
 };
}

function shortLabel(label: string): string {
 // Two-line wrap support; we keep it simple — split on first space, take
 // up to 14 chars per line.
 if (label.length <= 14) return label;
 const words = label.split(" ");
 if (words.length === 1) return label.slice(0, 14);
 let line1 = "";
 for (const w of words) {
 if ((line1 + " " + w).trim().length > 14) break;
 line1 = (line1 + " " + w).trim();
 }
 const line2 = label.slice(line1.length).trim();
 return `${line1}\n${line2}`;
}

export default function ConfidenceRadar({
 rows,
 size = 240,
 className,
}: ConfidenceRadarProps) {
 if (rows.length < 3) {
 // Radar needs at least a triangle to read meaningfully.
 return null;
 }

 const cx = size / 2;
 const cy = size / 2;
 const padding = 36; // room for label text outside the rings
 const maxR = size / 2 - padding;
 const ringValues = [25, 50, 75, 100];

 // Start angle at top (-90deg) and sweep clockwise.
 const axisAngle = (i: number) =>
 -Math.PI / 2 + (i / rows.length) * Math.PI * 2;

 const polygonPoints = rows
 .map((row, i) => {
 const r = (Math.max(0, Math.min(100, row.score)) / 100) * maxR;
 const p = polar(cx, cy, r, axisAngle(i));
 return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
 })
 .join(" ");

 return (
 <div
 className={cn("relative", className)}
 style={{ width: size, height: size }}
 >
 <svg
 viewBox={`0 0 ${size} ${size}`}
 className="block h-full w-full"
 aria-hidden="true"
 >
 {/* concentric reference rings */}
 {ringValues.map((v) => {
 const r = (v / 100) * maxR;
 return (
 <circle
 key={v}
 cx={cx}
 cy={cy}
 r={r}
 fill="none"
 stroke="rgb(63 63 70 / 0.45)"
 strokeWidth="0.6"
 strokeDasharray={v === 100 ? "0" : "2 4"}
 />
 );
 })}

 {/* axis spokes */}
 {rows.map((row, i) => {
 const tip = polar(cx, cy, maxR, axisAngle(i));
 return (
 <line
 key={`spoke-${row.label}`}
 x1={cx}
 y1={cy}
 x2={tip.x}
 y2={tip.y}
 stroke="rgb(63 63 70 / 0.5)"
 strokeWidth="0.5"
 />
 );
 })}

 {/* score polygon */}
 <polygon
 points={polygonPoints}
 fill="rgb(52 211 153 / 0.18)"
 stroke="rgb(52 211 153 / 0.85)"
 strokeWidth="1.25"
 strokeLinejoin="round"
 style={{
 transition:
 "points 380ms cubic-bezier(0.16, 1, 0.3, 1)",
 }}
 />

 {/* score points */}
 {rows.map((row, i) => {
 const r = (Math.max(0, Math.min(100, row.score)) / 100) * maxR;
 const p = polar(cx, cy, r, axisAngle(i));
 return (
 <circle
 key={`pt-${row.label}`}
 cx={p.x}
 cy={p.y}
 r="2.4"
 fill="rgb(52 211 153)"
 />
 );
 })}

 {/* labels just outside the outer ring */}
 {rows.map((row, i) => {
 const tip = polar(cx, cy, maxR + 14, axisAngle(i));
 // anchor based on which side of center we're on
 const angle = axisAngle(i);
 const cosA = Math.cos(angle);
 let anchor: "start" | "middle" | "end" = "middle";
 if (cosA > 0.2) anchor = "start";
 else if (cosA < -0.2) anchor = "end";
 const lines = shortLabel(row.label).split("\n");
 return (
 <text
 key={`lbl-${row.label}`}
 x={tip.x}
 y={tip.y}
 textAnchor={anchor}
 dominantBaseline="middle"
 fontSize="8.5"
 fill="rgb(161 161 170)"
 fontFamily="var(--font-work-sans)"
 >
 {lines.map((line, li) => (
 <tspan
 key={li}
 x={tip.x}
 dy={li === 0 ? 0 : 10}
 className=" "
 >
 {line}
 </tspan>
 ))}
 </text>
 );
 })}

 {/* tiny center dot */}
 <circle cx={cx} cy={cy} r="1.5" fill="rgb(82 82 91)" />
 </svg>
 </div>
 );
}
