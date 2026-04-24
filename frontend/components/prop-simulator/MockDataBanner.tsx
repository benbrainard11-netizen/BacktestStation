import { AlertTriangle } from "lucide-react";

export default function MockDataBanner() {
  return (
    <div className="flex items-center gap-2 border-b border-amber-900/50 bg-amber-950/25 px-6 py-2">
      <AlertTriangle
        className="h-3.5 w-3.5 shrink-0 text-amber-400"
        strokeWidth={1.5}
        aria-hidden="true"
      />
      <p className="font-mono text-[10px] uppercase tracking-widest text-amber-200">
        Prop Firm Simulator · design scaffold · every number on these pages is
        MOCK demo data, not a real Monte Carlo result
      </p>
    </div>
  );
}
