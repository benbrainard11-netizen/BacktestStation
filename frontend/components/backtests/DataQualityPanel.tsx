import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Report = components["schemas"]["DataQualityReportRead"];
type Issue = components["schemas"]["DataQualityIssue"];

interface DataQualityPanelProps {
 report: Report | null;
 loadError: string | null;
}

const SEVERITY_STYLES: Record<string, string> = {
 low: "border-warn/30 bg-warn/10 text-warn",
 medium: "border-orange-900 bg-orange-950/30 text-orange-200",
 high: "border-neg/30 bg-neg/10 text-neg",
};

export default function DataQualityPanel({
 report,
 loadError,
}: DataQualityPanelProps) {
 if (loadError !== null) {
 return (
 <div className="border border-neg/30 bg-neg/10 p-3 tabular-nums text-xs text-text">
 <p className="tabular-nums text-[10px] text-neg">
 Data quality unavailable
 </p>
 <p className="mt-1">{loadError}</p>
 </div>
 );
 }
 if (report === null) {
 return (
 <p className="tabular-nums text-xs text-text-mute">
 Data quality not computed for this run.
 </p>
 );
 }

 const scoreColor =
 report.reliability_score >= 85
 ? "text-pos"
 : report.reliability_score >= 60
 ? "text-warn"
 : "text-neg";

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
 <p className="tabular-nums text-[10px] text-text-mute">
 Coverage: {report.first_bar_ts.slice(0, 10)} →{" "}
 {report.last_bar_ts.slice(0, 10)}
 </p>
 ) : null}

 {report.issues.length === 0 ? (
 <div className="border border-dashed border-border bg-surface px-3 py-3">
 <p className="tabular-nums text-[10px] text-pos">
 No issues detected
 </p>
 <p className="mt-1 tabular-nums text-xs text-text-mute">
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
 <details className="border border-border bg-surface px-3 py-2">
 <summary className="cursor-pointer tabular-nums text-[10px] text-text-mute">
 Checks deferred to Phase 3+ ({report.deferred_checks.length})
 </summary>
 <ul className="mt-2 flex flex-col gap-1 tabular-nums text-xs text-text-mute">
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
 <div className="flex flex-col gap-1 border border-border bg-surface px-3 py-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span
 className={cn(
 "tabular-nums text-base leading-none text-text",
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
 <li className={cn("border bg-surface px-3 py-2", styles)}>
 <div className="flex items-start justify-between gap-3 tabular-nums text-[10px] ">
 <span>{issue.category}</span>
 <span className="text-text-mute">severity {issue.severity}</span>
 </div>
 <p className="mt-1 tabular-nums text-xs text-text">{issue.message}</p>
 <div className="mt-2 flex flex-wrap gap-3 tabular-nums text-[10px] text-text-mute">
 {issue.count > 0 ? <span>count {issue.count}</span> : null}
 {issue.affected_range !== null ? (
 <span>range {issue.affected_range}</span>
 ) : null}
 <span>distorts backtest: {issue.distort_backtest}</span>
 </div>
 </li>
 );
}
