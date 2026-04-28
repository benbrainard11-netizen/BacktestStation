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
 <div className="flex flex-col gap-2 rounded-lg border border-warn/30 bg-warn/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
 <div className="flex items-start gap-2">
 <AlertTriangle
 className="mt-0.5 h-4 w-4 shrink-0 text-warn"
 strokeWidth={1.5}
 aria-hidden="true"
 />
 <div>
 <p className="tabular-nums text-[11px] text-warn">
 All {status.total} firm profiles are demo / unverified
 </p>
 <p className="mt-1 text-xs text-warn/80">
 Pass rates, EV, and payout estimates below are built on demo firm
 rules. Edit each profile&apos;s numbers in Firm Rules and mark them
 verified before trusting the outputs.
 </p>
 </div>
 </div>
 <Link
 href="/prop-simulator/firms"
 className="shrink-0 rounded-md border border-warn/30 bg-warn/10 px-3 py-1.5 text-center text-xs text-warn hover:bg-warn/10"
 >
 Open Firm Rules →
 </Link>
 </div>
 );
}
