import { cn } from "@/lib/utils";

interface ChartPlaceholderProps {
  label: string;
  className?: string;
}

export default function ChartPlaceholder({
  label,
  className,
}: ChartPlaceholderProps) {
  return (
    <div
      className={cn(
        "bg-stripes flex h-48 items-center justify-center border border-dashed border-zinc-800 text-center",
        className,
      )}
    >
      <div className="max-w-xs px-6">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Chart · placeholder
        </p>
        <p className="mt-2 text-xs text-zinc-500">{label}</p>
      </div>
    </div>
  );
}
