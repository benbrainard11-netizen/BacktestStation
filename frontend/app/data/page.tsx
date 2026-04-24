import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import RefreshDatasetsButton from "@/components/data/RefreshDatasetsButton";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Dataset = components["schemas"]["DatasetRead"];

export const dynamic = "force-dynamic";

export default async function DataWarehousePage() {
  const datasets = await apiGet<Dataset[]>("/api/datasets").catch(
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
      <div className="flex items-center justify-end gap-3 px-6 pt-4">
        <RefreshDatasetsButton />
      </div>
      <PageHeader
        title="Data warehouse"
        description="Files BacktestStation knows about. Click refresh to re-scan the disk."
        meta={`${datasets.length} files · ${symbolCount} symbols · ${schemaCount} schemas · ${formatBytes(totalBytes)}`}
      />

      <div className="flex flex-col gap-4 px-6">
        {datasets.length === 0 ? (
          <Panel title="No data yet">
            <p className="font-mono text-xs text-zinc-500">
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
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {schema}
      </span>
      <div className="overflow-x-auto border border-zinc-800">
        <table className="w-full min-w-[700px] font-mono text-xs">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/40">
              <th className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500">
                Date
              </th>
              <th className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500">
                Source
              </th>
              <th className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500">
                Kind
              </th>
              <th className="px-3 py-1.5 text-right text-[10px] uppercase tracking-widest text-zinc-500">
                Size
              </th>
              <th className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500">
                Path
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((ds) => (
              <tr
                key={ds.id}
                className="border-b border-zinc-900 last:border-b-0 hover:bg-zinc-900/30"
              >
                <td className="px-3 py-1 text-zinc-300">
                  {formatDate(ds.start_ts)}
                </td>
                <td className="px-3 py-1 text-zinc-400">{ds.source}</td>
                <td className="px-3 py-1 text-zinc-400">{ds.kind}</td>
                <td className="px-3 py-1 text-right text-zinc-300">
                  {formatBytes(ds.file_size_bytes)}
                </td>
                <td className="px-3 py-1 font-mono text-[10px] text-zinc-500">
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
