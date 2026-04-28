"use client";

import StatusDot, { type StatusTone } from "@/components/StatusDot";
import type { components } from "@/lib/api/generated";

type DriftResult = components["schemas"]["DriftResultRead"];

interface Props {
  result: DriftResult | null;
}

export default function WinRateDriftCard({ result }: Props) {
  if (result === null) {
    return (
      <div className="border border-zinc-800 bg-zinc-950 p-3">
        <Header tone="idle" status="—" />
        <p className="mt-2 font-mono text-xs text-zinc-500">
          No win-rate signal yet.
        </p>
      </div>
    );
  }

  const tone = statusToTone(result.status);
  const livePct =
    result.live_value !== null ? formatPct(result.live_value) : "—";
  const baselinePct =
    result.baseline_value !== null ? formatPct(result.baseline_value) : "—";
  const deviationPp =
    result.deviation !== null ? formatSignedPp(result.deviation) : "—";

  return (
    <div className="border border-zinc-800 bg-zinc-950 p-3">
      <Header tone={tone} status={result.status} />

      <div className="mt-2 grid grid-cols-3 gap-3 font-mono text-xs">
        <Stat label="Live WR" value={livePct} />
        <Stat label="Baseline" value={baselinePct} />
        <Stat
          label="Δ"
          value={deviationPp}
          tone={
            result.deviation === null
              ? "default"
              : Math.abs(result.deviation) >= 0.15
                ? "fail"
                : Math.abs(result.deviation) >= 0.07
                  ? "warn"
                  : "ok"
          }
        />
      </div>

      <div className="mt-2 grid grid-cols-2 gap-3 font-mono text-[10px] text-zinc-500">
        <span>n live = {result.sample_size_live}</span>
        <span>n baseline = {result.sample_size_baseline}</span>
      </div>

      {result.message ? (
        <p className="mt-2 font-mono text-[11px] text-zinc-400 italic">
          {result.message}
          {result.incomplete ? " · tentative (small sample)" : ""}
        </p>
      ) : null}
    </div>
  );
}

function Header({ tone, status }: { tone: StatusTone; status: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Win rate drift
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

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "ok" | "warn" | "fail";
}) {
  const c =
    tone === "ok"
      ? "text-emerald-300"
      : tone === "warn"
        ? "text-amber-300"
        : tone === "fail"
          ? "text-rose-300"
          : "text-zinc-200";
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span className={`font-mono text-sm tabular-nums ${c}`}>{value}</span>
    </div>
  );
}

function statusToTone(status: string): StatusTone {
  if (status === "OK") return "live";
  if (status === "WATCH") return "warn";
  if (status === "WARN") return "off";
  return "idle";
}

function formatPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function formatSignedPp(v: number): string {
  // deviation is in raw rate space (e.g. 0.05 = 5pp). Express as signed
  // percentage points so it reads naturally next to live/baseline %.
  const pp = v * 100;
  return `${pp >= 0 ? "+" : ""}${pp.toFixed(1)}pp`;
}
