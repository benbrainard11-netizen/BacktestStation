"use client";

import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";

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
      <div className="px-8 pb-10">
        <div className="rounded-lg border border-neg/30 bg-neg/10 p-4">
          <p className="m-0 text-xs text-neg">Failed to load runs</p>
          <p className="m-0 mt-2 text-[13px] text-text">{error.message}</p>
          <p className="m-0 mt-3 text-xs text-text-mute">
            Backend reachable at the configured API URL? The default is
            <span className="ml-1 tabular-nums text-text-dim">
              http://localhost:8000
            </span>
            .
          </p>
          <div className="mt-4">
            <Btn onClick={reset}>Retry</Btn>
          </div>
        </div>
      </div>
    </div>
  );
}
