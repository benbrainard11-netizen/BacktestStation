"use client";

import MetricCard from "@/components/MetricCard";
import Panel from "@/components/Panel";
import type { components } from "@/lib/api/generated";

type Disk = components["schemas"]["DiskSpaceRead"];

interface Props {
 disk: Disk;
}

export default function DiskSpacePanel({ disk }: Props) {
 const totalGB = disk.total_bytes / 1e9;
 const usedGB = disk.used_bytes / 1e9;
 const freeGB = disk.free_bytes / 1e9;
 const pctUsed = disk.total_bytes > 0
 ? (disk.used_bytes / disk.total_bytes) * 100
 : 0;

 const tone: "positive" | "negative" | "neutral" =
 disk.total_bytes === 0
 ? "neutral"
 : pctUsed >= 75
 ? "negative"
 : "positive";

 return (
 <Panel title="Warehouse disk" meta={disk.path}>
 {disk.total_bytes === 0 ? (
 <p className="tabular-nums text-xs text-text-mute">
 Path doesn&apos;t exist or isn&apos;t mounted on this host.
 </p>
 ) : (
 <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
 <MetricCard
 label="Free"
 value={`${freeGB.toFixed(0)} GB`}
 valueTone={tone}
 />
 <MetricCard
 label="Used"
 value={`${usedGB.toFixed(0)} GB (${pctUsed.toFixed(1)}%)`}
 valueTone="neutral"
 />
 <MetricCard
 label="Total"
 value={`${totalGB.toFixed(0)} GB`}
 valueTone="neutral"
 />
 </div>
 )}
 </Panel>
 );
}
