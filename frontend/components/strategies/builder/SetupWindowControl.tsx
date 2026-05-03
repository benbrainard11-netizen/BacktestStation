"use client";

import { cn } from "@/lib/utils";

export type WindowSpec =
  | { type: "bars"; n: number }
  | { type: "minutes"; n: number }
  | { type: "until_clock"; end_hour: number; tz: string };

/**
 * Per-direction setup arming window control.
 *
 * Three variants the engine understands (matches backend WindowSpec):
 *  - persistent (null) — arms until end of trading day, the safe default
 *  - bars        — arm for N bars after firing
 *  - minutes     — arm for N minutes (wall clock) after firing
 *  - until_clock — arm until a specific local time on the firing bar's
 *                  trading day (e.g., "10:00 ET")
 *
 * Tabs select the active variant; "until close" toggles persistent.
 */
export function SetupWindowControl({
  direction,
  value,
  onChange,
}: {
  direction: "long" | "short";
  value: WindowSpec | null;
  onChange: (next: WindowSpec | null) => void;
}) {
  const persistent = value === null;
  const kind = value?.type ?? "bars";

  function setKind(next: "bars" | "minutes" | "until_clock") {
    if (next === "bars") onChange({ type: "bars", n: value?.type === "bars" ? value.n : 5 });
    else if (next === "minutes")
      onChange({ type: "minutes", n: value?.type === "minutes" ? value.n : 30 });
    else
      onChange({
        type: "until_clock",
        end_hour: value?.type === "until_clock" ? value.end_hour : 11.0,
        tz: value?.type === "until_clock" ? value.tz : "America/New_York",
      });
  }

  return (
    <div className="grid gap-1.5">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[9.5px] uppercase tracking-[0.08em] text-ink-3">
          Window
        </span>
        <label className="inline-flex items-center gap-1 font-mono text-[9.5px] text-ink-3">
          <input
            type="checkbox"
            checked={persistent}
            onChange={(e) => onChange(e.target.checked ? null : { type: "bars", n: 5 })}
            className="h-3 w-3"
          />
          until close
        </label>
      </div>
      {!persistent && (
        <>
          <div className="inline-flex rounded border border-line bg-bg-2 p-0.5">
            {(["bars", "minutes", "until_clock"] as const).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                className={cn(
                  "rounded px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.06em] transition",
                  kind === k
                    ? "bg-accent-soft text-accent"
                    : "text-ink-3 hover:text-ink-1",
                )}
              >
                {k === "until_clock" ? "until time" : k}
              </button>
            ))}
          </div>
          {kind === "bars" && value?.type === "bars" && (
            <input
              type="number"
              min={1}
              step={1}
              value={value.n}
              onChange={(e) => {
                const v = e.target.value;
                if (v === "") return;
                const n = Number.parseInt(v, 10);
                if (Number.isNaN(n) || n < 1) return;
                onChange({ type: "bars", n });
              }}
              placeholder="bars"
              className="w-16 rounded border border-line bg-bg-2 px-1.5 py-0.5 font-mono text-[11px]"
              aria-label={`Setup window bars (${direction})`}
            />
          )}
          {kind === "minutes" && value?.type === "minutes" && (
            <input
              type="number"
              min={1}
              step={1}
              value={value.n}
              onChange={(e) => {
                const v = e.target.value;
                if (v === "") return;
                const n = Number.parseInt(v, 10);
                if (Number.isNaN(n) || n < 1) return;
                onChange({ type: "minutes", n });
              }}
              placeholder="minutes"
              className="w-16 rounded border border-line bg-bg-2 px-1.5 py-0.5 font-mono text-[11px]"
              aria-label={`Setup window minutes (${direction})`}
            />
          )}
          {kind === "until_clock" && value?.type === "until_clock" && (
            <div className="flex items-center gap-1">
              <input
                type="time"
                value={hourFracToHHMM(value.end_hour)}
                onChange={(e) => {
                  const h = hhmmToHourFrac(e.target.value);
                  if (h == null) return;
                  onChange({ ...value, end_hour: h });
                }}
                className="rounded border border-line bg-bg-2 px-1.5 py-0.5 font-mono text-[11px]"
                aria-label={`Setup window end time (${direction})`}
              />
              <select
                value={value.tz}
                onChange={(e) => onChange({ ...value, tz: e.target.value })}
                className="rounded border border-line bg-bg-2 px-1 py-0.5 font-mono text-[10px]"
              >
                <option value="America/New_York">ET</option>
                <option value="America/Chicago">CT</option>
                <option value="America/Denver">MT</option>
                <option value="America/Los_Angeles">PT</option>
                <option value="Europe/London">London</option>
                <option value="UTC">UTC</option>
              </select>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function hourFracToHHMM(h: number): string {
  const hh = Math.floor(h);
  const mm = Math.round((h - hh) * 60);
  return `${hh.toString().padStart(2, "0")}:${mm.toString().padStart(2, "0")}`;
}

function hhmmToHourFrac(s: string): number | null {
  const parts = s.split(":");
  if (parts.length !== 2) return null;
  const h = Number.parseInt(parts[0], 10);
  const m = Number.parseInt(parts[1], 10);
  if (!Number.isFinite(h) || !Number.isFinite(m)) return null;
  if (h < 0 || h > 24 || m < 0 || m >= 60) return null;
  return h + m / 60;
}
