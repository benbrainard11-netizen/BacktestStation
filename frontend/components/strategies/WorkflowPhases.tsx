import { cn } from "@/lib/utils";

export interface PhaseDef {
  key: string;
  label: string;
  /** Stage values from `Strategy.status` that map to this phase. */
  statuses: string[];
}

export const WORKFLOW_PHASES: PhaseDef[] = [
  { key: "idea", label: "Idea", statuses: ["idea", "research"] },
  { key: "build", label: "Build", statuses: ["building"] },
  { key: "backtest", label: "Backtest", statuses: ["backtest_validated"] },
  { key: "validate", label: "Validate", statuses: ["forward_test"] },
  { key: "live", label: "Live", statuses: ["live"] },
];

/**
 * Horizontal phase stepper across the top of the strategy workspace.
 * Highlights the phase that matches the strategy's current `status`,
 * shows earlier phases as completed, later phases as upcoming. Lets
 * the user see "where they are" in the quant workflow at a glance.
 *
 * Retired/archived strategies render the bar in a dimmed state with
 * no active phase.
 */
export default function WorkflowPhases({ status }: { status: string }) {
  const dimmed = status === "retired" || status === "archived";
  const activeIdx = dimmed
    ? -1
    : WORKFLOW_PHASES.findIndex((p) => p.statuses.includes(status));

  return (
    <ol className="flex items-center gap-0 overflow-x-auto rounded-lg border border-border bg-surface p-2">
      {WORKFLOW_PHASES.map((phase, i) => {
        const isActive = i === activeIdx;
        const isComplete = activeIdx >= 0 && i < activeIdx;
        const isUpcoming = activeIdx >= 0 && i > activeIdx;
        return (
          <li key={phase.key} className="flex flex-1 items-center gap-2">
            <a
              href={`#phase-${phase.key}`}
              className={cn(
                "flex flex-1 items-center gap-2 rounded-md px-3 py-2 text-[13px] transition-colors",
                isActive &&
                  "bg-accent/10 text-accent ring-1 ring-accent/30",
                isComplete && "text-text-dim hover:bg-surface-alt",
                isUpcoming && "text-text-mute hover:bg-surface-alt",
                dimmed && "text-text-mute",
              )}
            >
              <span
                className={cn(
                  "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border tabular-nums text-[10px]",
                  isActive
                    ? "border-accent bg-accent text-bg"
                    : isComplete
                      ? "border-pos/40 bg-pos/10 text-pos"
                      : "border-border bg-surface text-text-mute",
                )}
              >
                {isComplete ? "✓" : i + 1}
              </span>
              <span className="truncate">{phase.label}</span>
            </a>
            {i < WORKFLOW_PHASES.length - 1 ? (
              <span
                aria-hidden="true"
                className={cn(
                  "h-px w-4 shrink-0",
                  isComplete ? "bg-pos/40" : "bg-border",
                )}
              />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
