import Link from "next/link";

import RunsExplorer from "@/components/backtests/RunsExplorer";
import PageHeader from "@/components/PageHeader";
import { apiGet } from "@/lib/api/client";
import type { BacktestRun } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function BacktestsPage() {
  const runs = await apiGet<BacktestRun[]>("/api/backtests");

  return (
    <div>
      <PageHeader
        title="Backtests"
        description="Imported runs from existing backtest result files"
      />

      <div className="flex flex-col gap-3 px-6 pb-10">
        {runs.length >= 2 ? (
          <div>
            <Link
              href="/backtests/compare"
              className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
            >
              Compare runs →
            </Link>
          </div>
        ) : null}
        {runs.length === 0 ? <EmptyRuns /> : <RunsExplorer runs={runs} />}
      </div>
    </div>
  );
}

function EmptyRuns() {
  return (
    <div className="border border-dashed border-zinc-800 bg-zinc-950 px-6 py-10">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        No runs yet
      </p>
      <p className="mt-2 text-sm text-zinc-300">
        Import a backtest bundle to populate this list.
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
