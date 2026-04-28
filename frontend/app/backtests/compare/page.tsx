import Link from "next/link";

import CompareMetricsTable from "@/components/backtests/CompareMetricsTable";
import OverlaidEquityChart from "@/components/backtests/OverlaidEquityChart";
import OverlaidRHistogram from "@/components/backtests/OverlaidRHistogram";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import Btn from "@/components/ui/Btn";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type EquityPoint = components["schemas"]["EquityPointRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type Trade = components["schemas"]["TradeRead"];

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{ a?: string; b?: string }>;
}

export default async function CompareBacktestsPage({ searchParams }: PageProps) {
  const { a, b } = await searchParams;

  if (!a || !b) {
    return <PickTwoRuns />;
  }

  const [runA, runB] = await Promise.all([
    fetchOrNull<BacktestRun>(`/api/backtests/${a}`),
    fetchOrNull<BacktestRun>(`/api/backtests/${b}`),
  ]);

  if (runA === null || runB === null) {
    return <MissingRuns a={a} b={b} foundA={runA !== null} foundB={runB !== null} />;
  }

  const [metricsA, metricsB, equityA, equityB, tradesA, tradesB] = await Promise.all([
    fetchOrNull<RunMetrics>(`/api/backtests/${a}/metrics`),
    fetchOrNull<RunMetrics>(`/api/backtests/${b}/metrics`),
    apiGet<EquityPoint[]>(`/api/backtests/${a}/equity`),
    apiGet<EquityPoint[]>(`/api/backtests/${b}/equity`),
    apiGet<Trade[]>(`/api/backtests/${a}/trades`),
    apiGet<Trade[]>(`/api/backtests/${b}/trades`),
  ]);

  const aLabel = runLabel(runA);
  const bLabel = runLabel(runB);

  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/backtests">← All runs</Btn>
      </div>
      <PageHeader
        title="Compare runs"
        description={`${aLabel} vs ${bLabel}`}
        meta={`A=#${runA.id} B=#${runB.id}`}
      />
      <div className="flex flex-col gap-4 px-8">
        <Panel title="Equity curves" meta="overlaid">
          <OverlaidEquityChart
            a={{ label: aLabel, points: equityA }}
            b={{ label: bLabel, points: equityB }}
          />
        </Panel>
        <Panel title="R-multiple distribution" meta="overlaid">
          <OverlaidRHistogram
            a={{ label: aLabel, trades: tradesA }}
            b={{ label: bLabel, trades: tradesB }}
          />
        </Panel>
        <Panel title="Metrics" meta="Δ is better when green">
          <CompareMetricsTable
            a={metricsA}
            b={metricsB}
            aLabel={aLabel}
            bLabel={bLabel}
          />
        </Panel>
        <div className="flex gap-3">
          <Btn href={`/backtests/${runA.id}`}>Open A: {aLabel} →</Btn>
          <Btn href={`/backtests/${runB.id}`}>Open B: {bLabel} →</Btn>
        </div>
      </div>
    </div>
  );
}

async function PickTwoRuns() {
  const runs = await apiGet<BacktestRun[]>("/api/backtests").catch(() => []);

  return (
    <div className="pb-10">
      <PageHeader
        title="Compare runs"
        description="Pick two imported runs to compare side by side"
      />
      <div className="px-8">
        {runs.length < 2 ? (
          <EmptyPicker count={runs.length} />
        ) : (
          <Picker runs={runs} />
        )}
      </div>
    </div>
  );
}

function Picker({ runs }: { runs: BacktestRun[] }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-[18px]">
      <p className="m-0 text-xs text-text-mute">Available runs</p>
      <ul className="m-0 mt-3 flex list-none flex-col gap-1.5 p-0 text-[13px] text-text-dim">
        {runs.map((run) => (
          <li key={run.id} className="flex items-center justify-between gap-3">
            <span>
              #{run.id} · {runLabel(run)}
            </span>
            <span className="text-text-mute">{run.symbol}</span>
          </li>
        ))}
      </ul>
      <p className="m-0 mt-4 text-xs text-text-mute">
        Add{" "}
        <code className="rounded bg-surface-alt px-1 text-text-dim">
          ?a=ID&amp;b=ID
        </code>{" "}
        to this URL to compare, e.g.{" "}
        <Link
          href={`/backtests/compare?a=${runs[0].id}&b=${runs[1].id}`}
          className="text-accent hover:underline"
        >
          ?a={runs[0].id}&b={runs[1].id}
        </Link>
        .
      </p>
    </div>
  );
}

function EmptyPicker({ count }: { count: number }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface p-6">
      <p className="m-0 text-xs text-text-mute">Not enough runs</p>
      <p className="m-0 mt-2 text-[13px] text-text-dim">
        {count === 0
          ? "No runs imported yet."
          : "Only one run in the DB — import another to compare."}
      </p>
      <div className="mt-3">
        <Btn href="/import" variant="primary">
          Go to Import →
        </Btn>
      </div>
    </div>
  );
}

function MissingRuns({
  a,
  b,
  foundA,
  foundB,
}: {
  a: string;
  b: string;
  foundA: boolean;
  foundB: boolean;
}) {
  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/backtests">← All runs</Btn>
      </div>
      <PageHeader title="Compare runs" description="One of the IDs wasn't found" />
      <div className="px-8">
        <div className="rounded-lg border border-neg/30 bg-neg/10 p-4 text-[13px] text-text">
          <p className="m-0">A = #{a} {foundA ? "✓" : "✗ not found"}</p>
          <p className="m-0 mt-1">B = #{b} {foundB ? "✓" : "✗ not found"}</p>
        </div>
      </div>
    </div>
  );
}

function runLabel(run: BacktestRun): string {
  return run.name ?? `Backtest ${run.id}`;
}

async function fetchOrNull<T>(path: string): Promise<T | null> {
  try {
    return await apiGet<T>(path);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
