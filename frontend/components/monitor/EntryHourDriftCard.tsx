"use client";

import StatusDot, { type StatusTone } from "@/components/StatusDot";
import type { components } from "@/lib/api/generated";

type DriftResult = components["schemas"]["DriftResultRead"];

interface Props {
  result: DriftResult | null;
}

/**
 * Entry-hour distribution card: surfaces whether live entry timing has
 * drifted from baseline. The backend returns a chi-square p-value as
 * `live_value` (not yet a histogram). Until the backend exposes per-hour
 * counts, this card shows the chi-square + sample sizes in numeric form
 * and surfaces the WARN/WATCH/OK tone. A future iteration can render a
 * 9-14 ET hour histogram once the backend includes the bucket payload.
 */
export default function EntryHourDriftCard({ result }: Props) {
  if (result === null) {
    return (
      <div className="border border-zinc-800 bg-zinc-950 p-3">
        <Header tone="idle" status="—" />
        <p className="mt-2 font-mono text-xs text-zinc-500">
          No entry-time signal yet.
        </p>
      </div>
    );
  }

  const tone = statusToTone(result.status);
  const pValue =
    result.live_value !== null ? result.live_value.toFixed(4) : "—";

  return (
    <div className="border border-zinc-800 bg-zinc-950 p-3">
      <Header tone={tone} status={result.status} />

      <div className="mt-2 grid grid-cols-3 gap-3 font-mono text-xs">
        <Stat label="χ² p-value" value={pValue} />
        <Stat label="n live" value={String(result.sample_size_live)} />
        <Stat
          label="n baseline"
          value={String(result.sample_size_baseline)}
        />
      </div>

      {result.message ? (
        <p className="mt-2 font-mono text-[11px] text-zinc-400 italic">
          {result.message}
          {result.incomplete ? " · tentative (small sample)" : ""}
        </p>
      ) : null}

      <p className="mt-3 font-mono text-[10px] text-zinc-600">
        Lower p-value = stronger evidence the live entry-hour distribution
        differs from baseline. WATCH at p&nbsp;&lt;&nbsp;0.05, WARN at
        p&nbsp;&lt;&nbsp;0.01.
      </p>
    </div>
  );
}

function Header({ tone, status }: { tone: StatusTone; status: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Entry-time drift
      </span>
      <div className="flex items-center gap-2">
        <StatusDot status={tone} pulse={tone === "live"} />
        <span
          className={`font-mono text-[11px] uppercase tracking-widest ${
            tone === "live"
              ? "text-emerald-300"
              : tone === "warn"
                ? "text-amber-300"
                : tone === "off"
                  ? "text-rose-300"
                  : "text-zinc-400"
          }`}
        >
          {status}
        </span>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span className="font-mono text-sm tabular-nums text-zinc-200">
        {value}
      </span>
    </div>
  );
}

function statusToTone(status: string): StatusTone {
  if (status === "OK") return "live";
  if (status === "WATCH") return "warn";
  if (status === "WARN") return "off";
  return "idle";
}
