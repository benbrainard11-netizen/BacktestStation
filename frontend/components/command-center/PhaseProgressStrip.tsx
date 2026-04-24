import { Activity, CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { MOCK_PHASES, type MockPhase } from "@/lib/mocks/commandCenter";

function PhaseBlock({ phase }: { phase: MockPhase }) {
  const isComplete = phase.status === "complete";
  const isActive = phase.status === "active";
  const Icon = isComplete ? CheckCircle2 : Activity;

  const iconTone = isComplete
    ? "text-emerald-400"
    : isActive
      ? "text-emerald-400"
      : "text-zinc-600";

  const ringTone = isActive ? "border-emerald-500/40" : "border-zinc-800";
  const statusTone = isActive
    ? "text-emerald-400"
    : isComplete
      ? "text-zinc-200"
      : "text-zinc-500";
  const statusLabel =
    phase.status === "complete"
      ? "Complete"
      : phase.status === "active"
        ? "Active"
        : "Pending";

  return (
    <div className="flex min-w-0 shrink-0 items-center gap-3">
      <span
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border bg-zinc-950",
          ringTone,
        )}
      >
        <Icon className={cn("h-4 w-4", iconTone)} strokeWidth={1.5} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          {phase.label}
        </p>
        <p className={cn("text-sm font-medium", statusTone)}>{statusLabel}</p>
        <p className="mt-0.5 text-xs text-zinc-500">{phase.detail}</p>
      </div>
    </div>
  );
}

export default function PhaseProgressStrip() {
  return (
    <section className="border border-zinc-800 bg-zinc-950 px-6 py-5">
      <div className="flex items-center">
        {MOCK_PHASES.map((phase, i) => (
          <div key={phase.key} className="flex flex-1 items-center">
            <PhaseBlock phase={phase} />
            {i < MOCK_PHASES.length - 1 ? (
              <div
                aria-hidden="true"
                className="mx-4 h-px flex-1 border-t border-dashed border-zinc-800"
              />
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
