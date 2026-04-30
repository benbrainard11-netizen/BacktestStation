import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import RefreshDatasetsButton from "@/components/data/RefreshDatasetsButton";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Dataset = components["schemas"]["DatasetRead"];

export const dynamic = "force-dynamic";
const DATASET_PREVIEW_LIMIT = 500;

export default async function DataWarehousePage() {
 const datasets = await apiGet<Dataset[]>(
 `/api/datasets?limit=${DATASET_PREVIEW_LIMIT}`,
 ).catch(
 () => [] as Dataset[],
 );

 // Group by symbol → schema for the table layout.
 const grouped = new Map<string, Map<string, Dataset[]>>();
 for (const ds of datasets) {
 const symKey = ds.symbol ?? "(mixed)";
 const schemaMap = grouped.get(symKey) ?? new Map<string, Dataset[]>();
 const list = schemaMap.get(ds.schema) ?? [];
 list.push(ds);
 schemaMap.set(ds.schema, list);
 grouped.set(symKey, schemaMap);
 }

 const totalBytes = datasets.reduce((n, d) => n + d.file_size_bytes, 0);
 const symbolCount = grouped.size;
 const schemaCount = new Set(datasets.map((d) => d.schema)).size;

 return (
 <div className="pb-10">
 <div className="flex items-center justify-end gap-3 px-8 pt-4">
 <RefreshDatasetsButton />
 </div>
 <PageHeader
 title="Data warehouse"
 description="Files BacktestStation knows about. Click refresh to re-scan the disk."
 meta={`${datasets.length}${datasets.length === DATASET_PREVIEW_LIMIT ? "+" : ""} files · ${symbolCount} symbols · ${schemaCount} schemas · ${formatBytes(totalBytes)}`}
 />

 <div className="flex flex-col gap-4 px-8">
 {datasets.length === 0 ? (
 <Panel title="No data yet">
 <p className="tabular-nums text-xs text-text-mute">
 The datasets table is empty. Either no warehouse files exist
 under <code>BS_DATA_ROOT</code>, or the scan hasn&apos;t run yet.
 Click <strong>Refresh</strong> to walk the disk.
 </p>
 </Panel>
 ) : (
 [...grouped.entries()]
 .sort(([a], [b]) => a.localeCompare(b))
 .map(([symbol, schemaMap]) => (
 <Panel
 key={symbol}
 title={symbol}
 meta={`${[...schemaMap.values()].flat().length} files`}
 >
 <div className="flex flex-col gap-3">
 {[...schemaMap.entries()]
 .sort(([a], [b]) => a.localeCompare(b))
 .map(([schema, list]) => (
 <DatasetTable
 key={schema}
 schema={schema}
 rows={list}
 />
 ))}
 </div>
 </Panel>
 ))
 )}
 </div>
 </div>
 );
}

function DatasetTable({
 schema,
 rows,
}: {
 schema: string;
 rows: Dataset[];
}) {
 const sorted = [...rows].sort((a, b) => {
 const aTs = a.start_ts ? new Date(a.start_ts).getTime() : 0;
 const bTs = b.start_ts ? new Date(b.start_ts).getTime() : 0;
 return bTs - aTs;
 });
 return (
 <div className="flex flex-col gap-1">
 <span className="text-xs text-text-mute">{schema}</span>
 <div className="overflow-x-auto rounded-lg border border-border bg-surface">
 <table className="w-full min-w-[700px] border-collapse text-[13px] tabular-nums">
 <thead>
 <tr className="text-xs text-text-mute">
 <th className="border-b border-border px-3 py-2 text-left font-normal">
 Date
 </th>
 <th className="border-b border-border px-3 py-2 text-left font-normal">
 Source
 </th>
 <th className="border-b border-border px-3 py-2 text-left font-normal">
 Kind
 </th>
 <th className="border-b border-border px-3 py-2 text-right font-normal">
 Size
 </th>
 <th className="border-b border-border px-3 py-2 text-left font-normal">
 Path
 </th>
 </tr>
 </thead>
 <tbody>
 {sorted.map((ds) => (
 <tr
 key={ds.id}
 className="border-b border-border last:border-b-0 hover:bg-surface-alt"
 >
 <td className="whitespace-nowrap px-3 py-2 text-text-dim">
 {formatDate(ds.start_ts)}
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-text-dim">{ds.source}</td>
 <td className="whitespace-nowrap px-3 py-2 text-text-dim">{ds.kind}</td>
 <td className="whitespace-nowrap px-3 py-2 text-right text-text-dim">
 {formatBytes(ds.file_size_bytes)}
 </td>
 <td
 className="max-w-[480px] truncate px-3 py-2 text-xs text-text-mute"
 title={ds.file_path}
 >
 {ds.file_path}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </div>
 );
}

function formatBytes(bytes: number): string {
 if (bytes < 1024) return `${bytes} B`;
 if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
 if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
 return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function formatDate(iso: string | null): string {
 if (iso === null) return "—";
 const d = new Date(iso);
 if (Number.isNaN(d.getTime())) return iso;
 return d.toISOString().slice(0, 10);
}
