"use client";

import { CheckCircle2, XCircle } from "lucide-react";

import Panel from "@/components/Panel";
import type { components } from "@/lib/api/generated";

type Settings = components["schemas"]["SystemSettingsRead"];

interface Props {
  settings: Settings;
}

export default function SystemInfoPanel({ settings }: Props) {
  const freeGB = (settings.free_disk_bytes / 1e9).toFixed(0);
  return (
    <Panel title="System info" meta="read-only">
      <dl className="grid grid-cols-1 gap-x-6 gap-y-2 font-mono text-xs sm:grid-cols-[auto_1fr]">
        <Row label="App version" value={settings.version} />
        <Row
          label="Git SHA"
          value={
            settings.git_sha
              ? `${settings.git_sha}${settings.git_dirty ? " (dirty)" : ""}`
              : "unknown"
          }
        />
        <Row label="Platform" value={settings.platform} />
        <Row label="Python" value={settings.python_version} />

        <Divider />

        <Row label="BS_DATA_ROOT" value={settings.bs_data_root} />
        <Row
          label="Warehouse exists"
          valueNode={
            <BoolPill value={settings.bs_data_root_exists} />
          }
        />
        <Row label="Free disk" value={`${freeGB} GB`} />

        <Divider />

        <Row
          label="DATABENTO_API_KEY"
          valueNode={
            <BoolPill
              value={settings.databento_api_key_set}
              trueLabel="set"
              falseLabel="missing"
            />
          }
        />

        <Divider />

        <Row
          label="Server time (UTC)"
          value={formatIso(settings.server_time_utc)}
        />
        <Row
          label="Server time (ET)"
          value={formatIso(settings.server_time_et)}
        />
      </dl>
    </Panel>
  );
}

function Row({
  label,
  value,
  valueNode,
}: {
  label: string;
  value?: string;
  valueNode?: React.ReactNode;
}) {
  return (
    <>
      <dt className="text-zinc-500">{label}</dt>
      <dd className="text-zinc-200 break-all">
        {valueNode ?? <span className="tabular-nums">{value}</span>}
      </dd>
    </>
  );
}

function Divider() {
  return (
    <div
      aria-hidden
      className="col-span-full my-1 border-t border-zinc-800/60"
    />
  );
}

function BoolPill({
  value,
  trueLabel = "yes",
  falseLabel = "no",
}: {
  value: boolean;
  trueLabel?: string;
  falseLabel?: string;
}) {
  if (value) {
    return (
      <span className="inline-flex items-center gap-1 text-emerald-300">
        <CheckCircle2 className="h-3 w-3" strokeWidth={1.5} aria-hidden />
        <span className="uppercase tracking-widest text-[10px]">
          {trueLabel}
        </span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-rose-300">
      <XCircle className="h-3 w-3" strokeWidth={1.5} aria-hidden />
      <span className="uppercase tracking-widest text-[10px]">
        {falseLabel}
      </span>
    </span>
  );
}

function formatIso(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  // Strip milliseconds + render in clock-readable form. Keep TZ offset
  // by formatting via Intl with explicit options.
  return iso.replace(/\.\d+/, "");
}
