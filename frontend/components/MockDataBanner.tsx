import { AlertTriangle } from "lucide-react";

interface MockDataBannerProps {
  message?: string;
}

export default function MockDataBanner({
  message = "Mock layout data — sample values for design review. Not connected to backend yet.",
}: MockDataBannerProps) {
  return (
    <div
      role="status"
      className="flex items-center gap-2 border-b border-amber-900/40 bg-amber-950/30 px-6 py-2 font-mono text-[11px] uppercase tracking-widest text-amber-300"
    >
      <AlertTriangle
        className="h-3.5 w-3.5 shrink-0 text-amber-400"
        strokeWidth={1.5}
        aria-hidden="true"
      />
      <span>{message}</span>
    </div>
  );
}
