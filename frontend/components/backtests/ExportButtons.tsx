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
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
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
      className="border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-300 hover:bg-zinc-900 hover:text-zinc-100"
    >
      {label} ↓
    </Link>
  );
}
