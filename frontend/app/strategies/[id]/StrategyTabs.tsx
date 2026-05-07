"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const TABS: { id: string; label: string; suffix: string }[] = [
  { id: "sims",      label: "Sims & Results", suffix: "" },
  { id: "replay",    label: "Replay",         suffix: "/replay" },
  { id: "backtests", label: "Backtests",      suffix: "/backtests" },
  { id: "builder",   label: "Builder",        suffix: "/build" },
];

/**
 * Sub-nav rendered ABOVE the strategy detail content. Lives in
 * /strategies/[id]/layout.tsx so every nested route (replay, backtests,
 * builder) inherits the same header. Active tab = longest path-suffix
 * match.
 */
export function StrategyTabs({ strategyId }: { strategyId: string }) {
  const pathname = usePathname();
  const base = `/strategies/${strategyId}`;
  // longest-suffix match (tabs with longer suffix beat empty suffix)
  const activeTab =
    [...TABS]
      .sort((a, b) => b.suffix.length - a.suffix.length)
      .find((t) => pathname === base + t.suffix || pathname.startsWith(base + t.suffix + "/")) ??
    TABS[0];

  return (
    <div className="border-b border-line bg-bg-1">
      <div className="mx-auto flex max-w-[1280px] items-center gap-1 px-6">
        <Link
          href="/strategies"
          className="mr-3 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3 hover:text-ink-1"
        >
          ← Catalog
        </Link>
        {TABS.map((t) => {
          const href = base + t.suffix;
          const active = activeTab.id === t.id;
          return (
            <Link
              key={t.id}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative flex h-10 items-center px-3 font-mono text-[11px] uppercase tracking-[0.06em] transition-colors",
                active
                  ? "text-accent"
                  : "text-ink-3 hover:text-ink-1",
              )}
            >
              <span>{t.label}</span>
              {active && (
                <span className="absolute bottom-[-1px] left-0 right-0 h-[2px] bg-accent" />
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
