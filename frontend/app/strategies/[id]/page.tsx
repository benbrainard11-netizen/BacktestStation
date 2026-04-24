import Link from "next/link";
import { notFound } from "next/navigation";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Strategy = components["schemas"]["StrategyRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function StrategyDetailPage({ params }: PageProps) {
  const { id } = await params;

  const strategy = await apiGet<Strategy>(`/api/strategies/${id}`).catch(
    (error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    },
  );

  const runs = await apiGet<BacktestRun[]>("/api/backtests");
  const runsByVersion = new Map<number, BacktestRun[]>();
  for (const run of runs) {
    const list = runsByVersion.get(run.strategy_version_id) ?? [];
    list.push(run);
    runsByVersion.set(run.strategy_version_id, list);
  }

  const sortedVersions = [...strategy.versions].sort(
    (a, b) => b.id - a.id,
  );

  return (
    <div className="pb-10">
      <div className="px-6 pt-4">
        <Link
          href="/strategies"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← All strategies
        </Link>
      </div>
      <PageHeader
        title={strategy.name}
        description={`${strategy.slug} · ${strategy.versions.length} version${strategy.versions.length === 1 ? "" : "s"} · status ${strategy.status}`}
        meta={formatDate(strategy.created_at)}
      />

      <div className="flex flex-col gap-4 px-6">
        {strategy.tags && strategy.tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {strategy.tags.map((tag) => (
              <span
                key={tag}
                className="border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-400"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null}

        {strategy.description ? (
          <Panel title="Description">
            <p className="text-sm text-zinc-300">{strategy.description}</p>
          </Panel>
        ) : null}

        {sortedVersions.length === 0 ? (
          <Panel title="Versions">
            <p className="font-mono text-xs text-zinc-500">
              No versions registered yet.
            </p>
          </Panel>
        ) : (
          sortedVersions.map((version) => (
            <VersionPanel
              key={version.id}
              version={version}
              runs={runsByVersion.get(version.id) ?? []}
            />
          ))
        )}
      </div>
    </div>
  );
}

function VersionPanel({
  version,
  runs,
}: {
  version: StrategyVersion;
  runs: BacktestRun[];
}) {
  return (
    <Panel
      title={`Version ${version.version}`}
      meta={`${runs.length} run${runs.length === 1 ? "" : "s"}`}
    >
      <div className="flex flex-col gap-3">
        <VersionMeta version={version} />
        {runs.length === 0 ? (
          <p className="font-mono text-xs text-zinc-500">
            No imported runs for this version.
          </p>
        ) : (
          <RunsList runs={runs} />
        )}
      </div>
    </Panel>
  );
}

function VersionMeta({ version }: { version: StrategyVersion }) {
  const fields: { label: string; value: string | null }[] = [
    { label: "Created", value: formatDateTime(version.created_at) },
    { label: "Git SHA", value: version.git_commit_sha },
    { label: "Entry", value: version.entry_md },
    { label: "Exit", value: version.exit_md },
    { label: "Risk", value: version.risk_md },
  ];
  const hasAny = fields.some((f) => f.value !== null && f.value !== "");
  if (!hasAny) return null;
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-1 font-mono text-xs sm:grid-cols-2">
      {fields
        .filter((f) => f.value !== null && f.value !== "")
        .map((f) => (
          <div key={f.label} className="flex flex-col">
            <dt className="text-[10px] uppercase tracking-widest text-zinc-500">
              {f.label}
            </dt>
            <dd className="text-zinc-300">{f.value}</dd>
          </div>
        ))}
    </dl>
  );
}

function RunsList({ runs }: { runs: BacktestRun[] }) {
  const sorted = [...runs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full min-w-[700px] font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/40">
            <th className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500">
              Run
            </th>
            <th className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500">
              Symbol
            </th>
            <th className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500">
              Date range
            </th>
            <th className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500">
              Created
            </th>
            <th className="px-3 py-1.5 text-right text-[10px] uppercase tracking-widest text-zinc-500"></th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((run) => (
            <tr key={run.id} className="border-b border-zinc-900 last:border-b-0 hover:bg-zinc-900/30">
              <td className="px-3 py-1 text-zinc-100">
                {run.name ?? `BT-${run.id}`}
              </td>
              <td className="px-3 py-1 text-zinc-400">{run.symbol}</td>
              <td className="px-3 py-1 text-zinc-400">
                {formatDateRange(run.start_ts, run.end_ts)}
              </td>
              <td className="px-3 py-1 text-zinc-500">
                {formatDate(run.created_at)}
              </td>
              <td className="px-3 py-1 text-right">
                <Link
                  href={`/backtests/${run.id}`}
                  className="border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-[10px] uppercase tracking-widest text-zinc-200 hover:bg-zinc-800"
                >
                  Open →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 10);
}

function formatDateTime(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

function formatDateRange(start: string | null, end: string | null): string {
  const s = formatDate(start);
  const e = formatDate(end);
  if (s === "—" && e === "—") return "—";
  return `${s} → ${e}`;
}
