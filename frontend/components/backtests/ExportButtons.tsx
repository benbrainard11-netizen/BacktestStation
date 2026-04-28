import Link from "next/link";

interface ExportButtonsProps {
 runId: number;
 hasMetrics: boolean;
}

/**
 * Three download links that hit the CSV export endpoints. The browser
 * follows the `download` attribute + Content-Disposition from the server,
 * so no client JS is needed.
 */
export default function ExportButtons({ runId, hasMetrics }: ExportButtonsProps) {
 return (
 <div className="flex flex-wrap items-center gap-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 Export CSV
 </span>
 <Button href={`/api/backtests/${runId}/trades.csv`} label="trades" />
 <Button href={`/api/backtests/${runId}/equity.csv`} label="equity" />
 {hasMetrics ? (
 <Button href={`/api/backtests/${runId}/metrics.csv`} label="metrics" />
 ) : null}
 </div>
 );
}

function Button({ href, label }: { href: string; label: string }) {
 return (
 <Link
 href={href}
 download
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt hover:text-text"
 >
 {label} ↓
 </Link>
 );
}
