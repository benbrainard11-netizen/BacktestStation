import { cn } from "@/lib/utils";

interface ConfidenceBreakdownRow {
 label: string;
 score: number; // 0-100
 caveat?: string;
}

interface ConfidenceBreakdownProps {
 rows: ConfidenceBreakdownRow[];
}

function scoreTone(score: number): string {
 if (score >= 85) return "text-pos";
 if (score >= 70) return "text-text";
 if (score >= 40) return "text-warn";
 return "text-neg";
}

function barTone(score: number): string {
 if (score >= 85) return "bg-pos/70";
 if (score >= 70) return "bg-text-mute";
 if (score >= 40) return "bg-warn/60";
 return "bg-neg/70";
}

export default function ConfidenceBreakdown({ rows }: ConfidenceBreakdownProps) {
 return (
 <ul className="space-y-2">
 {rows.map((row) => {
 const pct = Math.max(0, Math.min(100, row.score));
 return (
 <li key={row.label} className="flex items-center gap-3">
 <span className="w-44 shrink-0 tabular-nums text-[10px] text-text-mute">
 {row.label}
 </span>
 <div className="relative h-1.5 flex-1 overflow-hidden border border-border bg-surface">
 <div
 className={cn("h-full", barTone(pct))}
 style={{ width: `${pct}%` }}
 />
 </div>
 <span
 className={cn(
 "w-12 shrink-0 text-right tabular-nums text-xs tabular-nums",
 scoreTone(pct),
 )}
 >
 {Math.round(pct)}
 </span>
 </li>
 );
 })}
 </ul>
 );
}
