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
      ? "text-emerald-400"
      : tone === "amber"
        ? "text-amber-300"
        : "text-zinc-300";
  return (
    <div className="flex items-center justify-between border-b border-zinc-900 py-2 last:border-b-0">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span className={`font-mono text-sm tabular-nums ${toneClass}`}>
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
          className="border border-zinc-800 bg-zinc-950 px-3 py-2 text-center font-mono text-[10px] uppercase tracking-widest text-zinc-300 hover:bg-zinc-900"
        >
          Manage firm profiles →
        </Link>
        {summary.demo === summary.total ? (
          <p className="font-mono text-[10px] uppercase tracking-widest text-amber-400/80">
            Every profile is demo · edit before trusting
          </p>
        ) : null}
      </div>
    </Panel>
  );
}
