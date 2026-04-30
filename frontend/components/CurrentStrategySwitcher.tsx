"use client";

import { useEffect, useState } from "react";

import StrategyPicker from "@/components/StrategyPicker";
import { useCurrentStrategy } from "@/lib/hooks/useCurrentStrategy";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];

/**
 * Compact pill in the TopBar showing the active strategy. Click to open
 * the StrategyPicker. Quietly recovers from a stale id (strategy deleted)
 * by clearing localStorage.
 */
export default function CurrentStrategySwitcher() {
  const { id, loading, clearId } = useCurrentStrategy();
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (id === null) {
      setStrategy(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`/api/strategies/${id}`, { cache: "no-store" });
        if (!r.ok) {
          if (r.status === 404) clearId();
          if (!cancelled) setStrategy(null);
          return;
        }
        const s = (await r.json()) as Strategy;
        if (!cancelled) setStrategy(s);
      } catch {
        if (!cancelled) setStrategy(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, loading, clearId]);

  // Don't render until we've read localStorage — avoids a flash of "Pick
  // strategy" for users who already have one selected.
  if (loading) return <span className="h-6 w-32" aria-hidden />;

  return (
    <>
      <button
        type="button"
        onClick={() => setPickerOpen(true)}
        className="group flex h-7 max-w-[260px] items-center gap-2 rounded-md border border-border bg-surface-alt px-2.5 text-xs text-text-dim transition-colors hover:border-border-strong hover:text-text"
        title="Switch strategy"
      >
        <span className="text-text-mute">strategy</span>
        <span className="truncate text-text">
          {strategy ? strategy.name : id !== null ? "—" : "none selected"}
        </span>
        <svg
          aria-hidden="true"
          width={10}
          height={10}
          viewBox="0 0 10 10"
          className="shrink-0 text-text-mute group-hover:text-text-dim"
        >
          <path
            d="M2 4l3 3 3-3"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      <StrategyPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
      />
    </>
  );
}
