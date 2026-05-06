"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Collapsible section using native <details>. Used in the strategy
 * builder to fold completed sections (long pipeline, stop, target,
 * advanced) into 1-line summaries while keeping them one click away.
 *
 * Native <details> trades smooth height-animation for zero-JS
 * simplicity. If smoothness becomes a real complaint, swap for a
 * Collapsible primitive.
 */
export function CollapsibleSection({
  title,
  eyebrow,
  summary,
  defaultOpen = false,
  tone,
  children,
  className,
}: {
  title: string;
  eyebrow?: string;
  /** One-line summary shown on the right of the header when collapsed. */
  summary?: ReactNode;
  defaultOpen?: boolean;
  /** Optional tint for the left border / chips. */
  tone?: "pos" | "neg" | "accent" | "warn";
  children: ReactNode;
  className?: string;
}) {
  const toneBorder =
    tone === "pos"
      ? "border-l-pos"
      : tone === "neg"
        ? "border-l-neg"
        : tone === "warn"
          ? "border-l-warn"
          : tone === "accent"
            ? "border-l-accent-line"
            : "border-l-line";
  return (
    <details
      open={defaultOpen}
      className={cn(
        "group rounded-lg border border-line border-l-4 bg-bg-1 [&>summary::-webkit-details-marker]:hidden",
        toneBorder,
        className,
      )}
    >
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 hover:bg-bg-2/40">
        <span
          className="font-mono text-[10px] text-ink-4 transition group-open:rotate-90"
          aria-hidden
        >
          ▸
        </span>
        <div className="flex flex-col">
          {eyebrow && (
            <span className="font-mono text-[9.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              {eyebrow}
            </span>
          )}
          <span className="font-mono text-[12px] font-semibold text-ink-0">
            {title}
          </span>
        </div>
        {summary !== undefined && (
          <div className="ml-auto font-mono text-[11px] text-ink-2 group-open:hidden">
            {summary}
          </div>
        )}
      </summary>
      <div className="border-t border-line px-4 py-3">{children}</div>
    </details>
  );
}
