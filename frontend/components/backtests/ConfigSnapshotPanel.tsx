import type { components } from "@/lib/api/generated";

type Config = components["schemas"]["ConfigSnapshotRead"];

interface ConfigSnapshotPanelProps {
  config: Config | null;
  loadError: string | null;
}

export default function ConfigSnapshotPanel({
  config,
  loadError,
}: ConfigSnapshotPanelProps) {
  if (loadError !== null) {
    return (
      <div className="border border-rose-900 bg-rose-950/40 p-3 font-mono text-xs text-zinc-200">
        <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
          Config snapshot unavailable
        </p>
        <p className="mt-1">{loadError}</p>
      </div>
    );
  }
  if (config === null) {
    return (
      <p className="font-mono text-xs text-zinc-500">
        No config.json was uploaded with this run.
      </p>
    );
  }
  return (
    <details className="font-mono text-xs" open>
      <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        payload · imported {formatDateTime(config.created_at)}
      </summary>
      <pre className="mt-3 overflow-x-auto border border-zinc-800 bg-zinc-950 p-3 text-[11px] leading-5 text-zinc-200">
        {JSON.stringify(config.payload, null, 2)}
      </pre>
    </details>
  );
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)}`;
}
