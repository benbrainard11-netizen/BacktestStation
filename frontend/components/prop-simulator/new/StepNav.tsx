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
 <ol className="flex flex-wrap items-stretch overflow-hidden rounded-lg border border-border bg-surface">
 {steps.map((step, index) => {
 const isActive = index === currentIndex;
 const isDone = index < currentIndex;
 return (
 <li key={step.key} className="flex min-w-0 flex-1">
 <button
 type="button"
 onClick={() => onSelect(index)}
 className={cn(
 "flex w-full items-center gap-3 border-r border-border px-3 py-2.5 text-left text-xs transition-colors last:border-r-0",
 isActive && "bg-surface-alt text-text",
 !isActive && isDone && "text-text-dim hover:bg-surface-alt",
 !isActive && !isDone && "text-text-mute hover:bg-surface-alt",
 )}
 >
 <span
 className={cn(
 "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-xs tabular-nums",
 isActive
 ? "border-border bg-surface-alt text-text"
 : isDone
 ? "border-pos/30 bg-pos/10 text-pos"
 : "border-border bg-surface text-text-mute",
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
