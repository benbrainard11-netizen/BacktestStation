"use client";

import { cn } from "@/lib/utils";

export type Tab = { id: string; label: string; disabled?: boolean };

/**
 * Tabs — horizontal tab strip with accent underline on active.
 *
 * Controlled. Caller owns the `value` and decides what to render in the
 * panel. Use with conditional rendering or a switch on `value`.
 */
export function Tabs({
  tabs,
  value,
  onChange,
  className,
}: {
  tabs: Tab[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn("flex items-end gap-1 border-b border-line", className)}
    >
      {tabs.map((tab) => {
        const active = tab.id === value;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active}
            disabled={tab.disabled}
            onClick={() => onChange(tab.id)}
            className={cn(
              "px-4 py-2.5 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition-colors",
              active
                ? "-mb-px border-b-2 border-accent text-accent"
                : "text-ink-2 hover:text-ink-1",
              tab.disabled && "cursor-not-allowed opacity-40 hover:text-ink-2",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
