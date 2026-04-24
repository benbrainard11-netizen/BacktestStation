"use client";

import PageHeader from "@/components/PageHeader";

export default function StrategiesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <PageHeader
        title="Strategies"
        description="Every strategy seen across imported runs"
      />
      <div className="px-6 pb-10">
        <div className="border border-rose-900 bg-rose-950/40 p-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
            Failed to load strategies
          </p>
          <p className="mt-2 font-mono text-xs text-zinc-200">{error.message}</p>
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
