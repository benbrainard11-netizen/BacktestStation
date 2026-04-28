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
 <div className="border border-neg/30 bg-neg/10 p-3 tabular-nums text-xs text-text">
 <p className="tabular-nums text-[10px] text-neg">
 Config snapshot unavailable
 </p>
 <p className="mt-1">{loadError}</p>
 </div>
 );
 }
 if (config === null) {
 return (
 <p className="tabular-nums text-xs text-text-mute">
 No config.json was uploaded with this run.
 </p>
 );
 }
 return (
 <details className="tabular-nums text-xs" open>
 <summary className="cursor-pointer tabular-nums text-[10px] text-text-mute">
 payload · imported {formatDateTime(config.created_at)}
 </summary>
 <pre className="mt-3 overflow-x-auto border border-border bg-surface p-3 text-[11px] leading-5 text-text">
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
