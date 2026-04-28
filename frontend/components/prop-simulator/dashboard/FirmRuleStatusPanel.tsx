import Link from "next/link";

import Panel from "@/components/Panel";
import type { FirmRuleStatusSummary } from "@/lib/prop-simulator/types";

interface FirmRuleStatusPanelProps {
 summary: FirmRuleStatusSummary;
}

function StatRow({
 label,
 value,
 tone,
}: {
 label: string;
 value: number;
 tone: "emerald" | "amber" | "zinc";
}) {
 const toneClass =
 tone === "emerald"
 ? "text-pos"
 : tone === "amber"
 ? "text-warn"
 : "text-text-dim";
 return (
 <div className="flex items-center justify-between border-b border-border py-2 last:border-b-0">
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span className={`tabular-nums text-sm tabular-nums ${toneClass}`}>
 {value}
 </span>
 </div>
 );
}

export default function FirmRuleStatusPanel({
 summary,
}: FirmRuleStatusPanelProps) {
 return (
 <Panel title="Firm rule status" meta={`${summary.total} total`}>
 <div className="flex flex-col gap-4">
 <div>
 <StatRow label="Verified" value={summary.verified} tone="emerald" />
 <StatRow label="Unverified" value={summary.unverified} tone="amber" />
 <StatRow label="Demo" value={summary.demo} tone="zinc" />
 </div>
 <Link
 href="/prop-simulator/firms"
 className="border border-border bg-surface px-3 py-2 text-center tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 Manage firm profiles →
 </Link>
 {summary.demo === summary.total ? (
 <p className="tabular-nums text-[10px] text-warn/80">
 Every profile is demo · edit before trusting
 </p>
 ) : null}
 </div>
 </Panel>
 );
}
