import { cn } from "@/lib/utils";
import Panel from "@/components/Panel";
import type { CompareSetupRow } from "@/lib/prop-simulator/types";
import {
 failureReasonLabel,
 formatCurrencySigned,
 formatDays,
 formatPercent,
 samplingModeLabel,
} from "@/lib/prop-simulator/format";

interface SetupHighlightPanelProps {
 title: string;
 subtitle: string;
 setup: CompareSetupRow | null;
}

function Row({
 label,
 value,
 tone,
}: {
 label: string;
 value: string;
 tone?: "positive" | "negative" | "neutral";
}) {
 const toneClass =
 tone === "positive"
 ? "text-pos"
 : tone === "negative"
 ? "text-neg"
 : "text-text";
 return (
 <div className="flex items-center justify-between border-b border-border py-1.5 last:border-b-0">
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span className={cn("tabular-nums text-xs tabular-nums", toneClass)}>
 {value}
 </span>
 </div>
 );
}

export default function SetupHighlightPanel({
 title,
 subtitle,
 setup,
}: SetupHighlightPanelProps) {
 return (
 <Panel title={title} meta={subtitle}>
 {setup === null ? (
 <p className="tabular-nums text-xs text-text-mute">No simulations yet.</p>
 ) : (
 <div className="flex flex-col gap-3">
 <p className="text-sm text-text">{setup.setup_label}</p>
 <p className="tabular-nums text-[11px] text-text-mute">
 {setup.firm_name} · {samplingModeLabel(setup.sampling_mode)} · {setup.risk_label}
 </p>
 <div>
 <Row label="Pass" value={formatPercent(setup.pass_rate)} />
 <Row label="Payout" value={formatPercent(setup.payout_rate)} />
 <Row
 label="EV after fees"
 value={formatCurrencySigned(setup.ev_after_fees)}
 tone={
 setup.ev_after_fees > 0
 ? "positive"
 : setup.ev_after_fees < 0
 ? "negative"
 : "neutral"
 }
 />
 <Row label="Avg days" value={formatDays(setup.avg_days_to_pass)} />
 <Row label="DD usage" value={formatPercent(setup.average_dd_usage_percent)} />
 <Row label="Confidence" value={`${setup.confidence} / 100`} />
 <Row
 label="Main fail reason"
 value={failureReasonLabel(setup.main_failure_reason)}
 />
 </div>
 </div>
 )}
 </Panel>
 );
}
