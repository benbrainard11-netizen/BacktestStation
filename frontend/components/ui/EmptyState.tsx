"use client";

import { cn } from "@/lib/utils";

/**
 * EmptyState — promote the PageStub-style empty card into a reusable atom.
 *
 * Use inside a Card for "no data yet" / "no results" / "filter returned
 * nothing" states. Drop it as a top-level page when the whole page has
 * nothing to show.
 */
export function EmptyState({
  title,
  blurb,
  action,
  className,
}: {
  title: string;
  blurb?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-12 text-center",
        className,
      )}
    >
      <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-4">
        {title}
      </div>
      {blurb && <div className="max-w-sm text-sm text-ink-2">{blurb}</div>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
