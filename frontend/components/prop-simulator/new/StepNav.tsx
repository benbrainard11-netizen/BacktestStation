import { cn } from "@/lib/utils";

export interface StepDef {
  key: string;
  label: string;
}

interface StepNavProps {
  steps: StepDef[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export default function StepNav({ steps, currentIndex, onSelect }: StepNavProps) {
  return (
    <ol className="flex flex-wrap items-stretch border border-zinc-800 bg-zinc-950">
      {steps.map((step, index) => {
        const isActive = index === currentIndex;
        const isDone = index < currentIndex;
        return (
          <li key={step.key} className="flex min-w-0 flex-1">
            <button
              type="button"
              onClick={() => onSelect(index)}
              className={cn(
                "flex w-full items-center gap-3 border-r border-zinc-800 px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest last:border-r-0",
                isActive && "bg-zinc-900 text-zinc-100",
                !isActive && isDone && "text-zinc-400 hover:bg-zinc-900/60",
                !isActive && !isDone && "text-zinc-500 hover:bg-zinc-900/40",
              )}
            >
              <span
                className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center border text-[10px]",
                  isActive
                    ? "border-zinc-600 bg-zinc-800 text-zinc-100"
                    : isDone
                      ? "border-emerald-900 bg-emerald-950/40 text-emerald-300"
                      : "border-zinc-800 bg-zinc-950 text-zinc-500",
                )}
              >
                {index + 1}
              </span>
              <span className="truncate">{step.label}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
