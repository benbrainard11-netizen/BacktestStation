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
  low: "text-rose-400",
  moderate: "text-amber-300",
  high: "text-zinc-100",
  very_high: "text-emerald-400",
};

function overallTone(overall: number): string {
  if (overall >= 85) return "text-emerald-400";
  if (overall >= 70) return "text-zinc-100";
  if (overall >= 40) return "text-amber-300";
  return "text-rose-400";
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
                "font-mono text-5xl tabular-nums leading-none",
                overallTone(overall),
              )}
            >
              {Math.round(overall)}
            </span>
            <div className="flex flex-col">
              <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
                out of 100
              </span>
              <span className={cn("mt-1 font-mono text-xs", LABEL_TONE[label])}>
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
        <div className="border-t border-zinc-800 pt-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Main weaknesses
          </p>
          <ul className="mt-2 space-y-1.5">
            {weaknesses.map((w) => (
              <li key={w} className="flex items-start gap-2 text-xs text-zinc-400">
                <span
                  aria-hidden="true"
                  className="mt-1.5 h-px w-3 shrink-0 bg-zinc-700"
                />
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {footnote ? (
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          {footnote}
        </p>
      ) : null}
    </div>
  );
}
