"use client";

import Link from "next/link";

export default function BacktestDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="px-6 pb-10 pt-6">
      <Link
        href="/backtests"
        className="mb-4 inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
      >
        ← All runs
      </Link>
      <div className="border border-rose-900 bg-rose-950/40 p-4">
        <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
          Failed to load backtest
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
  );
}
