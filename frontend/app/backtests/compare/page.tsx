import Link from "next/link";

import CompareMetricsTable from "@/components/backtests/CompareMetricsTable";
import OverlaidEquityChart from "@/components/backtests/OverlaidEquityChart";
import OverlaidRHistogram from "@/components/backtests/OverlaidRHistogram";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
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
      <div className="px-6 pt-4">
        <Link
          href="/backtests"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← All runs
        </Link>
      </div>
      <PageHeader
        title="Compare runs"
        description={`${aLabel} vs ${bLabel}`}
        meta={`A=#${runA.id}  B=#${runB.id}`}
      />
      <div className="flex flex-col gap-4 px-6">
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
          <Link
            href={`/backtests/${runA.id}`}
            className="border border-zinc-800 bg-zinc-950 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-200 hover:bg-zinc-900"
          >
            Open A: {aLabel} →
          </Link>
          <Link
            href={`/backtests/${runB.id}`}
            className="border border-zinc-800 bg-zinc-950 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-200 hover:bg-zinc-900"
          >
            Open B: {bLabel} →
          </Link>
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
      <div className="px-6">
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
    <div className="border border-zinc-800 bg-zinc-950 p-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Available runs
      </p>
      <ul className="mt-3 flex flex-col gap-1 font-mono text-xs text-zinc-300">
        {runs.map((run) => (
          <li key={run.id} className="flex items-center justify-between gap-3">
            <span>
              #{run.id} · {runLabel(run)}
            </span>
            <span className="text-zinc-600">{run.symbol}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-zinc-500">
        Add{" "}
        <code className="bg-zinc-900 px-1 text-zinc-300">?a=ID&amp;b=ID</code>{" "}
        to this URL to compare, e.g.{" "}
        <Link
          href={`/backtests/compare?a=${runs[0].id}&b=${runs[1].id}`}
          className="text-zinc-300 underline hover:text-zinc-100"
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
    <div className="border border-dashed border-zinc-800 bg-zinc-950 p-6">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Not enough runs
      </p>
      <p className="mt-2 text-sm text-zinc-300">
        {count === 0
          ? "No runs imported yet."
          : "Only one run in the DB — import another to compare."}
      </p>
      <Link
        href="/import"
        className="mt-3 inline-block border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
      >
        Go to Import →
      </Link>
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
      <div className="px-6 pt-4">
        <Link
          href="/backtests"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← All runs
        </Link>
      </div>
      <PageHeader title="Compare runs" description="One of the IDs wasn't found" />
      <div className="px-6">
        <div className="border border-rose-900 bg-rose-950/40 p-4 font-mono text-xs text-zinc-200">
          <p>A = #{a} {foundA ? "✓" : "✗ not found"}</p>
          <p>B = #{b} {foundB ? "✓" : "✗ not found"}</p>
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
