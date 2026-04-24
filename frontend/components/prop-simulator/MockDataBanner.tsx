import { AlertTriangle } from "lucide-react";

export default function MockDataBanner() {
  return (
    <div className="flex items-center gap-2 border-b border-amber-900/50 bg-amber-950/25 px-6 py-1">
      <AlertTriangle
        className="h-3 w-3 shrink-0 text-amber-400"
        strokeWidth={1.5}
        aria-hidden="true"
      />
      <p className="font-mono text-[10px] uppercase tracking-widest text-amber-200">
        Prop Firm Simulator · mock design scaffold · not real Monte Carlo data
      </p>
    </div>
  );
}
