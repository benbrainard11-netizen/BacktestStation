import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-[600px] px-6 py-16 text-center">
      <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-4">
        404
      </div>
      <h1 className="mt-3 text-[22px] font-semibold text-ink-0">
        Backtest not found
      </h1>
      <p className="mt-2 text-[13px] text-ink-3">
        This run doesn&apos;t exist or was deleted.
      </p>
      <div className="mt-6">
        <Link
          href="/backtests"
          className="font-mono text-[12px] text-accent hover:underline"
        >
          ← Back to backtests
        </Link>
      </div>
    </div>
  );
}
