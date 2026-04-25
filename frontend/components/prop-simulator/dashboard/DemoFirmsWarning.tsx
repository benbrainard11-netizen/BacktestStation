import Link from "next/link";
import { AlertTriangle } from "lucide-react";

import type { FirmRuleStatusSummary } from "@/lib/prop-simulator/types";

interface DemoFirmsWarningProps {
  status: FirmRuleStatusSummary;
}

export default function DemoFirmsWarning({ status }: DemoFirmsWarningProps) {
  const allDemo = status.demo === status.total && status.total > 0;
  if (!allDemo) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2 border border-amber-900/70 bg-amber-950/25 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-2">
        <AlertTriangle
          className="mt-0.5 h-4 w-4 shrink-0 text-amber-400"
          strokeWidth={1.5}
          aria-hidden="true"
        />
        <div>
          <p className="font-mono text-[11px] uppercase tracking-widest text-amber-300">
            All {status.total} firm profiles are demo / unverified
          </p>
          <p className="mt-1 text-xs text-amber-200/80">
            Pass rates, EV, and payout estimates below are built on demo firm
            rules. Edit each profile&apos;s numbers in Firm Rules and mark them
            verified before trusting the outputs.
          </p>
        </div>
      </div>
      <Link
        href="/prop-simulator/firms"
        className="shrink-0 border border-amber-800 bg-amber-950/40 px-3 py-1.5 text-center font-mono text-[10px] uppercase tracking-widest text-amber-100 hover:bg-amber-900/40"
      >
        Open Firm Rules →
      </Link>
    </div>
  );
}
