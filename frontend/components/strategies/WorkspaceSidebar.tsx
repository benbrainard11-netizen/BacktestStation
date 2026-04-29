"use client";

import {
  Activity,
  BarChart3,
  Building2,
  FileText,
  GitCompareArrows,
  LayoutDashboard,
  Lightbulb,
  MessageSquare,
  Notebook,
  Rewind,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

export interface WorkspaceSection {
  /** URL segment under `/strategies/[id]/`. Empty string = home. */
  path: string;
  label: string;
  icon: LucideIcon;
  group: "build" | "validate" | "ship";
}

export const WORKSPACE_SECTIONS: WorkspaceSection[] = [
  // Build
  { path: "",            label: "Overview",      icon: LayoutDashboard,    group: "build" },
  { path: "chat",        label: "Chat",          icon: MessageSquare,      group: "build" },
  { path: "rules",       label: "Rules & idea",  icon: Lightbulb,          group: "build" },
  { path: "build",       label: "Build",         icon: FileText,           group: "build" },
  // Validate
  { path: "backtest",    label: "Backtest",      icon: BarChart3,          group: "validate" },
  { path: "replay",      label: "Replay",        icon: Rewind,             group: "validate" },
  { path: "prop-firm",   label: "Prop firm sim", icon: Building2,          group: "validate" },
  { path: "experiments", label: "Experiments",   icon: GitCompareArrows,   group: "validate" },
  { path: "notes",       label: "Notes",         icon: Notebook,           group: "validate" },
  // Ship
  { path: "live",        label: "Live",          icon: Activity,           group: "ship" },
];

const GROUP_LABELS: Record<WorkspaceSection["group"], string> = {
  build: "Build",
  validate: "Validate",
  ship: "Ship",
};

/**
 * Per-strategy left sub-sidebar. Lists workflow sections grouped by
 * phase. Each item is a Next.js route under `/strategies/[id]/`;
 * the active item is highlighted from `usePathname()`.
 *
 * Active-state matching:
 *   - "" (Overview) is active iff the path is exactly `/strategies/[id]`
 *   - any other section is active iff the path is exactly
 *     `/strategies/[id]/{path}` (or a deeper child of it).
 *
 * Pattern: nested layout sidebar — persists across sub-routes via
 * `app/strategies/[id]/layout.tsx`.
 */
export default function WorkspaceSidebar({
  strategyId,
}: {
  strategyId: number;
}) {
  const pathname = usePathname() ?? "";
  const base = `/strategies/${strategyId}`;
  const sub = pathname.startsWith(`${base}/`)
    ? pathname.slice(base.length + 1)
    : pathname === base
      ? ""
      : "";
  const activeSegment = sub.split("/")[0] ?? "";

  return (
    <aside className="sticky top-0 hidden h-fit w-48 shrink-0 self-start py-2 lg:block">
      <nav aria-label="Strategy workspace">
        {(["build", "validate", "ship"] as const).map((group) => {
          const items = WORKSPACE_SECTIONS.filter((s) => s.group === group);
          return (
            <div key={group} className="mb-4 last:mb-0">
              <p className="px-2 pb-1.5 text-[10px] uppercase tracking-wider text-text-mute">
                {GROUP_LABELS[group]}
              </p>
              <ul className="m-0 list-none p-0">
                {items.map((s) => {
                  const Icon = s.icon;
                  const active = s.path === activeSegment;
                  const href = s.path === "" ? base : `${base}/${s.path}`;
                  return (
                    <li key={s.path || "_overview"}>
                      <Link
                        href={href}
                        className={cn(
                          "group relative flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] transition-colors",
                          active
                            ? "bg-surface-alt text-text"
                            : "text-text-dim hover:bg-surface-alt hover:text-text",
                        )}
                      >
                        {active ? (
                          <span
                            aria-hidden="true"
                            className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-accent"
                          />
                        ) : null}
                        <Icon
                          className={cn(
                            "h-3.5 w-3.5 shrink-0",
                            active ? "text-accent" : "text-text-mute",
                          )}
                          strokeWidth={1.5}
                          aria-hidden="true"
                        />
                        <span>{s.label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
