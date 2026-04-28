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
 <div className="border border-border bg-surface p-3">
 <Header tone="idle" status="—" />
 <p className="mt-2 tabular-nums text-xs text-text-mute">
 No entry-time signal yet.
 </p>
 </div>
 );
 }

 const tone = statusToTone(result.status);
 const pValue =
 result.live_value !== null ? result.live_value.toFixed(4) : "—";

 return (
 <div className="border border-border bg-surface p-3">
 <Header tone={tone} status={result.status} />

 <div className="mt-2 grid grid-cols-3 gap-3 tabular-nums text-xs">
 <Stat label="χ² p-value" value={pValue} />
 <Stat label="n live" value={String(result.sample_size_live)} />
 <Stat
 label="n baseline"
 value={String(result.sample_size_baseline)}
 />
 </div>

 {result.message ? (
 <p className="mt-2 tabular-nums text-[11px] text-text-dim italic">
 {result.message}
 {result.incomplete ? " · tentative (small sample)" : ""}
 </p>
 ) : null}

 <p className="mt-3 tabular-nums text-[10px] text-text-mute">
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
 <span className="tabular-nums text-[10px] text-text-mute">
 Entry-time drift
 </span>
 <div className="flex items-center gap-2">
 <StatusDot status={tone} pulse={tone === "live"} />
 <span
 className={`tabular-nums text-[11px] ${
 tone === "live"
 ? "text-pos"
 : tone === "warn"
 ? "text-warn"
 : tone === "off"
 ? "text-neg"
 : "text-text-dim"
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
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span className="tabular-nums text-sm tabular-nums text-text">
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
