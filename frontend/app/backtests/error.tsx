"use client";

import PageHeader from "@/components/PageHeader";

export default function BacktestsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <PageHeader
        title="Backtests"
        description="Imported runs from existing backtest result files"
      />
      <div className="px-6 pb-10">
        <div className="border border-rose-900 bg-rose-950/40 p-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
            Failed to load runs
          </p>
          <p className="mt-2 font-mono text-xs text-zinc-200">
            {error.message}
          </p>
          <p className="mt-3 text-xs text-zinc-500">
            Backend reachable at the configured API URL? The default is
            <span className="ml-1 font-mono text-zinc-300">
              http://localhost:8000
            </span>
            .
          </p>
          <button
            type="button"
            onClick={reset}
            className="mt-4 border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
          >
            Retry
          </button>
        </div>
      </div>
    </div>
  );
}
