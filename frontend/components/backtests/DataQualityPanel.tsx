import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Report = components["schemas"]["DataQualityReportRead"];
type Issue = components["schemas"]["DataQualityIssue"];

interface DataQualityPanelProps {
  report: Report | null;
  loadError: string | null;
}

const SEVERITY_STYLES: Record<string, string> = {
  low: "border-amber-900 bg-amber-950/30 text-amber-200",
  medium: "border-orange-900 bg-orange-950/30 text-orange-200",
  high: "border-rose-900 bg-rose-950/40 text-rose-200",
};

export default function DataQualityPanel({
  report,
  loadError,
}: DataQualityPanelProps) {
  if (loadError !== null) {
    return (
      <div className="border border-rose-900 bg-rose-950/40 p-3 font-mono text-xs text-zinc-200">
        <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
          Data quality unavailable
        </p>
        <p className="mt-1">{loadError}</p>
      </div>
    );
  }
  if (report === null) {
    return (
      <p className="font-mono text-xs text-zinc-500">
        Data quality not computed for this run.
      </p>
    );
  }

  const scoreColor =
    report.reliability_score >= 85
      ? "text-emerald-400"
      : report.reliability_score >= 60
        ? "text-amber-400"
        : "text-rose-400";

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCell
          label="Reliability"
          value={`${report.reliability_score}/100`}
          valueClass={scoreColor}
        />
        <StatCell label="Dataset" value={report.dataset_status} />
        <StatCell label="Bars loaded" value={report.total_bars.toLocaleString()} />
        <StatCell label="Issues" value={report.issues.length.toString()} />
      </div>

      {report.first_bar_ts !== null && report.last_bar_ts !== null ? (
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          Coverage: {report.first_bar_ts.slice(0, 10)} →{" "}
          {report.last_bar_ts.slice(0, 10)}
        </p>
      ) : null}

      {report.issues.length === 0 ? (
        <div className="border border-dashed border-zinc-800 bg-zinc-950 px-3 py-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-emerald-400">
            No issues detected
          </p>
          <p className="mt-1 font-mono text-xs text-zinc-500">
            Candles match expected shape for this run&apos;s window.
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {report.issues.map((issue, i) => (
            <IssueRow key={`${issue.category}-${i}`} issue={issue} />
          ))}
        </ul>
      )}

      {report.deferred_checks.length > 0 ? (
        <details className="border border-zinc-800 bg-zinc-950 px-3 py-2">
          <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Checks deferred to Phase 3+ ({report.deferred_checks.length})
          </summary>
          <ul className="mt-2 flex flex-col gap-1 font-mono text-xs text-zinc-500">
            {report.deferred_checks.map((check, i) => (
              <li key={i}>· {check}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function StatCell({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex flex-col gap-1 border border-zinc-800 bg-zinc-950 px-3 py-2">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-base leading-none text-zinc-100",
          valueClass,
        )}
      >
        {value}
      </span>
    </div>
  );
}

function IssueRow({ issue }: { issue: Issue }) {
  const styles = SEVERITY_STYLES[issue.severity] ?? SEVERITY_STYLES.low;
  return (
    <li className={cn("border bg-zinc-950 px-3 py-2", styles)}>
      <div className="flex items-start justify-between gap-3 font-mono text-[10px] uppercase tracking-widest">
        <span>{issue.category}</span>
        <span className="text-zinc-500">severity {issue.severity}</span>
      </div>
      <p className="mt-1 font-mono text-xs text-zinc-200">{issue.message}</p>
      <div className="mt-2 flex flex-wrap gap-3 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {issue.count > 0 ? <span>count {issue.count}</span> : null}
        {issue.affected_range !== null ? (
          <span>range {issue.affected_range}</span>
        ) : null}
        <span>distorts backtest: {issue.distort_backtest}</span>
      </div>
    </li>
  );
}
