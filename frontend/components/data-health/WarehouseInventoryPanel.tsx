"use client";

import Panel from "@/components/Panel";
import type { components } from "@/lib/api/generated";

type Warehouse = components["schemas"]["WarehouseSummary"];

interface Props {
 warehouse: Warehouse;
}

export default function WarehouseInventoryPanel({ warehouse }: Props) {
 const meta =
 warehouse.last_scan_ts !== null && warehouse.last_scan_ts !== undefined
 ? `last scan ${new Date(warehouse.last_scan_ts).toISOString().slice(0, 19)}Z`
 : "never scanned";

 const schemas = warehouse.schemas ?? [];
 if (schemas.length === 0) {
 return (
 <Panel title="Warehouse inventory" meta="no datasets registered">
 <p className="tabular-nums text-xs text-text-mute">
 The <code className="text-text-dim">datasets</code> table is
 empty. Hit &quot;Re-scan now&quot; below to walk{" "}
 <code className="text-text-dim">$BS_DATA_ROOT</code> and
 register every partition on disk.
 </p>
 </Panel>
 );
 }

 return (
 <Panel title="Warehouse inventory" meta={meta}>
 <div className="overflow-x-auto">
 <table className="w-full tabular-nums text-xs">
 <thead>
 <tr className="text-left text-[10px] text-text-mute">
 <th className="pb-2 pr-4">Schema</th>
 <th className="pb-2 pr-4 text-right">Partitions</th>
 <th className="pb-2 pr-4 text-right">Size</th>
 <th className="pb-2 pr-4">Symbols</th>
 <th className="pb-2 pr-4">Date range</th>
 </tr>
 </thead>
 <tbody>
 {schemas.map((s) => {
 const symbols = s.symbols ?? [];
 return (
 <tr key={s.schema} className="border-t border-border">
 <td className="py-2 pr-4 text-text">{s.schema}</td>
 <td className="py-2 pr-4 text-right tabular-nums text-text">
 {s.partition_count.toLocaleString()}
 </td>
 <td className="py-2 pr-4 text-right tabular-nums text-text-dim">
 {formatBytes(s.total_bytes)}
 </td>
 <td className="py-2 pr-4 text-text-dim">
 {symbols.length === 0
 ? "—"
 : symbols.length <= 4
 ? symbols.join(", ")
 : `${symbols.slice(0, 3).join(", ")} +${symbols.length - 3}`}
 </td>
 <td className="py-2 pr-4 text-text-dim tabular-nums">
 {s.earliest_date && s.latest_date
 ? `${s.earliest_date} → ${s.latest_date}`
 : "—"}
 </td>
 </tr>
 );
 })}
 <tr className="border-t border-border font-medium">
 <td className="pt-2 pr-4 text-[10px] text-text-mute">
 Total
 </td>
 <td className="pt-2 pr-4 text-right tabular-nums text-text">
 {warehouse.total_partitions.toLocaleString()}
 </td>
 <td className="pt-2 pr-4 text-right tabular-nums text-text">
 {formatBytes(warehouse.total_bytes)}
 </td>
 <td colSpan={2}></td>
 </tr>
 </tbody>
 </table>
 </div>
 </Panel>
 );
}

function formatBytes(b: number): string {
 if (b === 0) return "—";
 if (b < 1e6) return `${(b / 1e3).toFixed(1)} KB`;
 if (b < 1e9) return `${(b / 1e6).toFixed(1)} MB`;
 return `${(b / 1e9).toFixed(2)} GB`;
}
