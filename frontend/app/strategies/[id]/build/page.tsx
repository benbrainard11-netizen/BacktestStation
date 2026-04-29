import Link from "next/link";
import { notFound } from "next/navigation";

import ArchiveVersionButton from "@/components/strategies/ArchiveVersionButton";
import NewVersionButton from "@/components/strategies/NewVersionButton";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

/**
 * Per-strategy build sub-page. v1: versions list with markdown
 * rules (entry / exit / risk) + per-version run list.
 *
 * Phase C lands here later — for `composable` strategies, this page
 * gets a feature pantry + recipe editor instead of (or alongside)
 * the markdown rules.
 */
export default async function BuildPage({ params }: PageProps) {
  const { id } = await params;
  const [strategy, runs] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<BacktestRun[]>(`/api/strategies/${id}/runs`).catch(
      () => [] as BacktestRun[],
    ),
  ]);

  const runsByVersion = new Map<number, BacktestRun[]>();
  for (const run of runs) {
    const list = runsByVersion.get(run.strategy_version_id) ?? [];
    list.push(run);
    runsByVersion.set(run.strategy_version_id, list);
  }

  const sortedVersions = [...strategy.versions].sort((a, b) => b.id - a.id);

  return (
    <section className="flex flex-col gap-3">
      <header className="flex items-baseline justify-between gap-3 border-b border-border pb-2">
        <div>
          <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
            Build
          </h2>
          <p className="m-0 mt-0.5 text-xs text-text-mute">
            Each version freezes a specific entry / exit / risk
            ruleset. Phase C visual feature builder lands here later.
          </p>
        </div>
        <NewVersionButton strategyId={strategy.id} />
      </header>

      {sortedVersions.length === 0 ? (
        <Panel title="No versions yet">
          <p className="text-xs text-text-mute">
            A version captures a specific entry/exit/risk ruleset.
            Create one to start attaching backtest runs to it.
          </p>
        </Panel>
      ) : (
        <div className="flex flex-col gap-3">
          {sortedVersions.map((version) => (
            <VersionPanel
              key={version.id}
              version={version}
              runs={runsByVersion.get(version.id) ?? []}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function VersionPanel({
  version,
  runs,
}: {
  version: StrategyVersion;
  runs: BacktestRun[];
}) {
  const archived = version.archived_at != null;
  return (
    <Panel
      title={`Version ${version.version}${archived ? " (archived)" : ""}`}
      meta={`${runs.length} run${runs.length === 1 ? "" : "s"}`}
    >
      <div className={cn("flex flex-col gap-3", archived && "opacity-60")}>
        <div className="flex items-center justify-between gap-2">
          {archived ? (
            <span className="tabular-nums text-[10px] text-text-mute">
              archived · {formatDate(version.archived_at ?? null)}
            </span>
          ) : (
            <span />
          )}
          <ArchiveVersionButton versionId={version.id} archived={archived} />
        </div>
        <VersionMeta version={version} />
        {runs.length === 0 ? (
          <p className="tabular-nums text-xs text-text-mute">
            No runs for this version.
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
    <dl className="grid grid-cols-1 gap-x-6 gap-y-1 tabular-nums text-xs sm:grid-cols-2">
      {fields
        .filter((f) => f.value !== null && f.value !== "")
        .map((f) => (
          <div key={f.label} className="flex flex-col">
            <dt className="text-[10px] text-text-mute">{f.label}</dt>
            <dd className="text-text-dim whitespace-pre-wrap">{f.value}</dd>
          </div>
        ))}
    </dl>
  );
}

function RunsList({ runs }: { runs: BacktestRun[] }) {
  const sorted = [...runs].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full min-w-[700px] border-collapse text-[13px] tabular-nums">
        <thead>
          <tr className="text-xs text-text-mute">
            <th className="border-b border-border px-3 py-2 text-left font-normal">Run</th>
            <th className="border-b border-border px-3 py-2 text-left font-normal">Symbol</th>
            <th className="border-b border-border px-3 py-2 text-left font-normal">Date range</th>
            <th className="border-b border-border px-3 py-2 text-left font-normal">Created</th>
            <th className="border-b border-border px-3 py-2 text-right font-normal"></th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((run) => (
            <tr
              key={run.id}
              className="border-b border-border last:border-b-0 hover:bg-surface-alt"
            >
              <td className="whitespace-nowrap px-3 py-2 text-text">
                {run.name ?? `BT-${run.id}`}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-text-dim">
                {run.symbol}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-text-dim">
                {formatDateRange(run.start_ts, run.end_ts)}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-text-mute">
                {formatDate(run.created_at)}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right">
                <Link
                  href={`/backtests/${run.id}`}
                  className="text-xs text-accent hover:underline"
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
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

function formatDateTime(iso: string | null): string {
  if (iso === null) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

function formatDateRange(start: string | null, end: string | null): string {
  return `${formatDate(start)} → ${formatDate(end)}`;
}
