"use client";

import Btn from "@/components/ui/Btn";

export default function BacktestDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="px-8 pb-10 pt-6">
      <div className="mb-4">
        <Btn href="/backtests">← All runs</Btn>
      </div>
      <div className="rounded-lg border border-neg/30 bg-neg/10 p-4">
        <p className="m-0 text-xs text-neg">Failed to load backtest</p>
        <p className="m-0 mt-2 text-[13px] text-text">{error.message}</p>
        <div className="mt-4">
          <Btn onClick={reset}>Retry</Btn>
        </div>
      </div>
    </div>
  );
}
