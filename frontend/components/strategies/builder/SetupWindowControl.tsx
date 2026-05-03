"use client";

import { cn } from "@/lib/utils";

/**
 * Per-direction setup arming window control.
 *
 * `null` = persistent (setup arms until end of trading day, the safe
 * default). A positive integer = arm for that many bars after the
 * setup fires (refreshed if setup re-fires while armed).
 */
export function SetupWindowControl({
  direction,
  value,
  onChange,
}: {
  direction: "long" | "short";
  value: number | null;
  onChange: (next: number | null) => void;
}) {
  const persistent = value === null;
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[9.5px] uppercase tracking-[0.08em] text-ink-3">
        Window
      </span>
      <input
        type="number"
        min={1}
        step={1}
        value={persistent ? "" : value}
        disabled={persistent}
        onChange={(e) => {
          const v = e.target.value;
          if (v === "") return;
          const n = Number.parseInt(v, 10);
          if (Number.isNaN(n)) return;
          onChange(n);
        }}
        placeholder="bars"
        className={cn(
          "w-16 rounded border border-line bg-bg-2 px-1.5 py-0.5 font-mono text-[11px]",
          persistent && "opacity-40",
        )}
        aria-label={`Setup window bars (${direction})`}
      />
      <label className="inline-flex items-center gap-1 font-mono text-[9.5px] text-ink-3">
        <input
          type="checkbox"
          checked={persistent}
          onChange={(e) => onChange(e.target.checked ? null : 5)}
          className="h-3 w-3"
        />
        until close
      </label>
    </div>
  );
}
