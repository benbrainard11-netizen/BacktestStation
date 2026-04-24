import Link from "next/link";
import { notFound } from "next/navigation";

import ArchiveStrategyButton from "@/components/strategies/ArchiveStrategyButton";
import ArchiveVersionButton from "@/components/strategies/ArchiveVersionButton";
import ExperimentsPanel from "@/components/strategies/ExperimentsPanel";
import MetricsGrid from "@/components/backtests/MetricsGrid";
import NewVersionButton from "@/components/strategies/NewVersionButton";
import NotesPanel from "@/components/strategies/NotesPanel";
import PromptGeneratorPanel from "@/components/strategies/PromptGeneratorPanel";
import StrategyEditor from "@/components/strategies/StrategyEditor";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import StatusPill from "@/components/StatusPill";
import { ApiError, apiGet } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type ExperimentDecisions = components["schemas"]["ExperimentDecisionsRead"];
type NoteTypes = components["schemas"]["NoteTypesRead"];
type PromptModes = components["schemas"]["PromptModesRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
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

  const [
    strategyRuns,
    noteTypesResponse,
    experimentDecisionsResponse,
    promptModesResponse,
  ] = await Promise.all([
    apiGet<BacktestRun[]>(`/api/strategies/${id}/runs`),
    apiGet<NoteTypes>("/api/notes/types").catch(
      () => ({ types: [] }) as NoteTypes,
    ),
    apiGet<ExperimentDecisions>("/api/experiments/decisions").catch(
      () => ({ decisions: [] }) as ExperimentDecisions,
    ),
    apiGet<PromptModes>("/api/prompts/modes").catch(
      () => ({ modes: [] }) as PromptModes,
    ),
  ]);
  // Endpoint already returns this strategy's runs ordered by created_at desc.
  const runsByVersion = new Map<number, BacktestRun[]>();
  for (const run of strategyRuns) {
    const list = runsByVersion.get(run.strategy_version_id) ?? [];
    list.push(run);
    runsByVersion.set(run.strategy_version_id, list);
  }
  const latestRun = strategyRuns[0] ?? null;
  const latestMetrics = latestRun
    ? await apiGet<RunMetrics>(
        `/api/backtests/${latestRun.id}/metrics`,
      ).catch((error) => {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      })
    : null;

  const sortedVersions = [...strategy.versions].sort((a, b) => b.id - a.id);
  const isArchived = strategy.status === "archived";

  return (
    <div className="pb-10">
      <div className="flex items-center justify-between gap-3 px-6 pt-4">
        <Link
          href="/strategies"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← All strategies
        </Link>
        <div className="flex items-center gap-2">
          <ArchiveStrategyButton
            strategyId={strategy.id}
            archived={isArchived}
          />
          <StrategyEditor
            strategyId={strategy.id}
            initialName={strategy.name}
            initialDescription={strategy.description}
            initialTags={strategy.tags}
          />
        </div>
      </div>
      <PageHeader
        title={strategy.name}
        description={`${strategy.slug} · ${strategy.versions.length} version${strategy.versions.length === 1 ? "" : "s"}`}
        meta={formatDate(strategy.created_at)}
      />

      <div className="flex flex-col gap-4 px-6">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill
            label="Stage"
            value={strategy.status}
            dot={stageTone(strategy.status)}
          />
          {strategy.tags && strategy.tags.length > 0
            ? strategy.tags.map((tag) => (
                <span
                  key={tag}
                  className="border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-400"
                >
                  {tag}
                </span>
              ))
            : null}
        </div>

        {strategy.description ? (
          <Panel title="Description">
            <p className="text-sm text-zinc-300">{strategy.description}</p>
          </Panel>
        ) : null}

        {latestMetrics ? (
          <Panel
            title="Latest run metrics"
            meta={
              latestRun
                ? `${latestRun.name ?? `BT-${latestRun.id}`} · ${formatDate(latestRun.created_at)}`
                : undefined
            }
          >
            <MetricsGrid metrics={latestMetrics} />
          </Panel>
        ) : null}

        {/*
          TODO (workstation, future pieces):
            - Research prompt generator (question → LLM-ready prompt w/ context)
            - Future in-app strategy engine hook
            - Forward/live drift monitor
            - Risk profile manager
        */}
        <NotesPanel
          strategyId={strategy.id}
          versions={strategy.versions}
          noteTypes={noteTypesResponse.types ?? []}
        />

        <ExperimentsPanel
          strategyId={strategy.id}
          versions={strategy.versions}
          runs={strategyRuns}
          decisions={experimentDecisionsResponse.decisions ?? []}
        />

        <PromptGeneratorPanel
          strategyId={strategy.id}
          modes={promptModesResponse.modes ?? []}
        />

        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Versions · {sortedVersions.length}
          </span>
          <NewVersionButton strategyId={strategy.id} />
        </div>

        {sortedVersions.length === 0 ? (
          <Panel title="No versions yet">
            <p className="font-mono text-xs text-zinc-500">
              A version captures a specific entry/exit/risk ruleset. Create one
              above to start attaching backtest runs to it.
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
  const archived = version.archived_at != null;
  return (
    <Panel
      title={`Version ${version.version}${archived ? " (archived)" : ""}`}
      meta={`${runs.length} run${runs.length === 1 ? "" : "s"}`}
    >
      <div
        className={cn(
          "flex flex-col gap-3",
          archived && "opacity-60",
        )}
      >
        <div className="flex items-center justify-between gap-2">
          {archived ? (
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              archived · {formatDate(version.archived_at ?? null)}
            </span>
          ) : (
            <span />
          )}
          <ArchiveVersionButton versionId={version.id} archived={archived} />
        </div>
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

function stageTone(
  status: string,
): "live" | "idle" | "warn" | "off" | null {
  switch (status) {
    case "live":
    case "backtest_validated":
    case "forward_test":
      return "live";
    case "research":
    case "building":
      return "warn";
    case "idea":
      return "idle";
    case "retired":
    case "archived":
      return "off";
    default:
      return null;
  }
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
