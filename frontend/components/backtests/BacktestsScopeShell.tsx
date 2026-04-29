"use client";

import { useEffect, useMemo, useState } from "react";

import RunsExplorer from "@/components/backtests/RunsExplorer";
import { useCurrentStrategy } from "@/lib/hooks/useCurrentStrategy";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Strategy = components["schemas"]["StrategyRead"];

const SCOPE_KEY = "bts.backtests.scope";

interface BacktestsScopeShellProps {
  runs: BacktestRun[];
  strategies: Strategy[];
}

/**
 * Wraps the runs explorer with a "current strategy only" toggle. The
 * toggle is hidden when there's no active strategy in localStorage —
 * filtering is meaningless then. Choice persists in localStorage so the
 * preference sticks per user.
 */
export default function BacktestsScopeShell({
  runs,
  strategies,
}: BacktestsScopeShellProps) {
  const { id: currentId, loading } = useCurrentStrategy();
  const [scope, setScope] = useState<"all" | "current">("all");

  // Read persisted preference, default to "current" when an active
  // strategy exists so the new dashboard mental model carries over here.
  useEffect(() => {
    if (loading) return;
    const stored = window.localStorage.getItem(SCOPE_KEY);
    if (stored === "all" || stored === "current") {
      setScope(stored);
    } else if (currentId !== null) {
      setScope("current");
    }
  }, [loading, currentId]);

  const persist = (next: "all" | "current") => {
    setScope(next);
    window.localStorage.setItem(SCOPE_KEY, next);
  };

  const currentStrategy = useMemo(
    () => (currentId === null ? null : strategies.find((s) => s.id === currentId) ?? null),
    [currentId, strategies],
  );

  const versionIds = useMemo(
    () =>
      currentStrategy === null
        ? new Set<number>()
        : new Set(currentStrategy.versions.map((v) => v.id)),
    [currentStrategy],
  );

  const filtered = useMemo(() => {
    if (scope === "all" || currentStrategy === null) return runs;
    return runs.filter((r) => versionIds.has(r.strategy_version_id));
  }, [scope, runs, currentStrategy, versionIds]);

  // Counts for the toggle labels.
  const currentCount = useMemo(
    () =>
      currentStrategy === null
        ? 0
        : runs.filter((r) => versionIds.has(r.strategy_version_id)).length,
    [currentStrategy, runs, versionIds],
  );

  // Don't render the toggle while localStorage is being read (avoids flash)
  // or when there's no active strategy at all.
  const showToggle = !loading && currentStrategy !== null;

  return (
    <div className="flex flex-col gap-3">
      {showToggle ? (
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-1">
            <ToggleBtn
              active={scope === "all"}
              onClick={() => persist("all")}
            >
              All runs · {runs.length}
            </ToggleBtn>
            <ToggleBtn
              active={scope === "current"}
              onClick={() => persist("current")}
            >
              {currentStrategy?.name ?? "Current"} · {currentCount}
            </ToggleBtn>
          </div>
          <span className="text-xs text-text-mute">
            scope · localStorage
          </span>
        </div>
      ) : null}
      <RunsExplorer runs={filtered} />
    </div>
  );
}

function ToggleBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md border px-2.5 py-1 text-xs transition-colors",
        active
          ? "border-border-strong bg-surface-alt text-text"
          : "border-border bg-surface text-text-dim hover:bg-surface-alt",
      )}
    >
      {children}
    </button>
  );
}
