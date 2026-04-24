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
  if (score >= 85) return "text-emerald-400";
  if (score >= 70) return "text-zinc-100";
  if (score >= 40) return "text-amber-300";
  return "text-rose-400";
}

function barTone(score: number): string {
  if (score >= 85) return "bg-emerald-500/70";
  if (score >= 70) return "bg-zinc-400";
  if (score >= 40) return "bg-amber-500/60";
  return "bg-rose-500/70";
}

export default function ConfidenceBreakdown({ rows }: ConfidenceBreakdownProps) {
  return (
    <ul className="space-y-2">
      {rows.map((row) => {
        const pct = Math.max(0, Math.min(100, row.score));
        return (
          <li key={row.label} className="flex items-center gap-3">
            <span className="w-44 shrink-0 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              {row.label}
            </span>
            <div className="relative h-1.5 flex-1 overflow-hidden border border-zinc-800 bg-zinc-950">
              <div
                className={cn("h-full", barTone(pct))}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span
              className={cn(
                "w-12 shrink-0 text-right font-mono text-xs tabular-nums",
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
