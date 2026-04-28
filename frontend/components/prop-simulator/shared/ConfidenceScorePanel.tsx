import { cn } from "@/lib/utils";
import type { ConfidenceLabel } from "@/lib/prop-simulator/types";

import ConfidenceBreakdown from "./ConfidenceBreakdown";
import ConfidenceRadar from "./ConfidenceRadar";

interface ConfidenceScorePanelProps {
 overall: number;
 label: ConfidenceLabel;
 subscoreRows: { label: string; score: number }[];
 weaknesses?: string[];
 footnote?: string;
}

const LABEL_TEXT: Record<ConfidenceLabel, string> = {
 low: "Low confidence",
 moderate: "Moderate confidence",
 high: "High confidence",
 very_high: "Very high confidence",
};

const LABEL_TONE: Record<ConfidenceLabel, string> = {
 low: "text-neg",
 moderate: "text-warn",
 high: "text-text",
 very_high: "text-pos",
};

function overallTone(overall: number): string {
 if (overall >= 85) return "text-pos";
 if (overall >= 70) return "text-text";
 if (overall >= 40) return "text-warn";
 return "text-neg";
}

export default function ConfidenceScorePanel({
 overall,
 label,
 subscoreRows,
 weaknesses,
 footnote,
}: ConfidenceScorePanelProps) {
 return (
 <div className="flex flex-col gap-5">
 <div className="grid grid-cols-1 gap-6 lg:grid-cols-[auto_1fr] lg:items-center">
 <div className="flex flex-col gap-4">
 <div className="flex items-baseline gap-4">
 <span
 className={cn(
 "tabular-nums text-5xl tabular-nums leading-none",
 overallTone(overall),
 )}
 >
 {Math.round(overall)}
 </span>
 <div className="flex flex-col">
 <span className="tabular-nums text-[10px] text-text-mute">
 out of 100
 </span>
 <span className={cn("mt-1 tabular-nums text-xs", LABEL_TONE[label])}>
 {LABEL_TEXT[label]}
 </span>
 </div>
 </div>
 <ConfidenceBreakdown rows={subscoreRows} />
 </div>

 <div className="flex justify-center lg:justify-end">
 <ConfidenceRadar rows={subscoreRows} size={260} />
 </div>
 </div>

 {weaknesses && weaknesses.length > 0 ? (
 <div className="border-t border-border pt-3">
 <p className="tabular-nums text-[10px] text-text-mute">
 Main weaknesses
 </p>
 <ul className="mt-2 space-y-1.5">
 {weaknesses.map((w) => (
 <li key={w} className="flex items-start gap-2 text-xs text-text-dim">
 <span
 aria-hidden="true"
 className="mt-1.5 h-px w-3 shrink-0 bg-border-strong"
 />
 <span>{w}</span>
 </li>
 ))}
 </ul>
 </div>
 ) : null}

 {footnote ? (
 <p className="tabular-nums text-[10px] text-text-mute">
 {footnote}
 </p>
 ) : null}
 </div>
 );
}
