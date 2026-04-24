import {
  Activity,
  Clock,
  Download,
  Files,
  HardDrive,
  ShieldCheck,
  Signal,
  Rows3,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import StatusDot from "@/components/StatusDot";
import {
  MOCK_DISK_PERCENT,
  MOCK_SYSTEM_STATUS,
  type MockSystemStatusRow,
} from "@/lib/mocks/commandCenter";
import { cn } from "@/lib/utils";

const ICONS: Record<string, LucideIcon> = {
  latest_import: Download,
  latest_signal: Signal,
  live_monitor: Activity,
  imported_files: Files,
  rows_imported: Rows3,
  data_quality: ShieldCheck,
  disk_usage: HardDrive,
  uptime: Clock,
};

function ValueCell({ row }: { row: MockSystemStatusRow }) {
  if (row.key === "live_monitor") {
    return (
      <span className="inline-flex items-center gap-2 font-mono text-xs text-emerald-400">
        <StatusDot status="live" pulse />
        {row.value.toUpperCase()}
      </span>
    );
  }
  return (
    <span
      className={cn(
        "font-mono text-xs",
        row.tone === "positive" ? "text-emerald-400" : "text-zinc-200",
      )}
    >
      {row.value}
    </span>
  );
}

export default function SystemStatusPanel() {
  return (
    <section className="flex flex-col border border-zinc-800 bg-zinc-950">
      <header className="border-b border-zinc-800 px-4 py-3">
        <h3 className="font-mono text-[11px] uppercase tracking-widest text-zinc-300">
          Latest Import / System Status
        </h3>
      </header>

      <ul className="divide-y divide-zinc-800/60">
        {MOCK_SYSTEM_STATUS.map((row) => {
          const Icon = ICONS[row.key];
          const isDisk = row.key === "disk_usage";
          return (
            <li key={row.key} className="px-4 py-2.5">
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2.5 text-zinc-400">
                  {Icon ? (
                    <Icon className="h-3.5 w-3.5 text-zinc-500" strokeWidth={1.5} aria-hidden="true" />
                  ) : null}
                  <span className="text-xs">{row.label}</span>
                </span>
                <ValueCell row={row} />
              </div>
              {isDisk ? <DiskBar percent={MOCK_DISK_PERCENT} /> : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function DiskBar({ percent }: { percent: number }) {
  return (
    <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-zinc-900">
      <div
        className="h-full bg-emerald-500/60"
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}
