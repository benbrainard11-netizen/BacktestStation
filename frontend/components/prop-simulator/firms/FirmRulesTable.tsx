import Link from "next/link";

import FirmRuleStatusBadge from "@/components/prop-simulator/shared/FirmRuleStatusBadge";
import type { FirmRuleProfile } from "@/lib/prop-simulator/types";

interface FirmRulesTableProps {
 firms: FirmRuleProfile[];
 /** When true, the Edit cell becomes a real link to the editor route. */
 editable?: boolean;
}

function formatCurrency(value: number | null): string {
 if (value === null) return "—";
 return `$${value.toLocaleString("en-US")}`;
}

function formatDays(value: number | null): string {
 if (value === null) return "—";
 return `${value}d`;
}

function formatTargetDd(firm: FirmRuleProfile): string {
 return `${formatCurrency(firm.profit_target)} / ${formatCurrency(firm.max_drawdown)}`;
}

function formatConsistency(firm: FirmRuleProfile): string {
 if (!firm.consistency_rule_enabled || firm.consistency_rule_value === null) {
 return "—";
 }
 if (firm.consistency_rule_type === "best_day_pct_of_total") {
 return `≤ ${Math.round(firm.consistency_rule_value * 100)}%`;
 }
 return String(firm.consistency_rule_value);
}

function formatPayout(firm: FirmRuleProfile): string {
 const parts: string[] = [`${firm.payout_split}%`];
 if (firm.payout_min_days !== null) parts.push(`${firm.payout_min_days}d`);
 if (firm.payout_min_profit !== null) {
 parts.push(`$${firm.payout_min_profit.toLocaleString()}`);
 }
 return parts.join(" · ");
}

function formatFees(firm: FirmRuleProfile): string {
 return `$${firm.eval_fee} / $${firm.activation_fee} / $${firm.reset_fee}`;
}

function formatTrailing(firm: FirmRuleProfile): string {
 if (!firm.trailing_drawdown_enabled) return "none";
 return firm.trailing_drawdown_type.replace(/_/g, " ");
}

export default function FirmRulesTable({
 firms,
 editable = false,
}: FirmRulesTableProps) {
 return (
 <div className="overflow-x-auto rounded-lg border border-border bg-surface">
 <table className="w-full border-collapse text-left text-[13px] tabular-nums">
 <thead>
 <tr className="text-xs text-text-mute">
 <th className="whitespace-nowrap border-b border-border px-3 py-2 font-normal">Firm</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 text-right font-normal">Size</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 text-right font-normal">Target / DD</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 text-right font-normal">Daily loss</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 font-normal">Trailing</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 text-right font-normal">Min days</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 font-normal">Consistency</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 font-normal">Payout (split·days·min)</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 font-normal">Fees (eval/act/reset)</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 font-normal">Verified</th>
 <th className="whitespace-nowrap border-b border-border px-3 py-2 text-right font-normal">Actions</th>
 </tr>
 </thead>
 <tbody>
 {firms.map((firm) => (
 <tr
 key={firm.profile_id}
 className="border-b border-border text-text-dim last:border-b-0 hover:bg-surface-alt"
 >
 <td className="whitespace-nowrap px-3 py-2">
 <div className="text-text">{firm.firm_name}</div>
 <div className="text-xs text-text-mute">{firm.account_name}</div>
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
 {formatCurrency(firm.account_size)}
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
 {formatTargetDd(firm)}
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
 {formatCurrency(firm.daily_loss_limit)}
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-text-dim">
 {formatTrailing(firm)}
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
 {formatDays(firm.minimum_trading_days)}
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-text-dim">
 {formatConsistency(firm)}
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-text-dim tabular-nums">
 {formatPayout(firm)}
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-text-dim tabular-nums">
 {formatFees(firm)}
 </td>
 <td className="whitespace-nowrap px-3 py-2">
 <FirmRuleStatusBadge
 status={firm.verification_status}
 lastVerifiedAt={firm.rule_last_verified_at}
 />
 </td>
 <td className="whitespace-nowrap px-3 py-2 text-right">
 {editable ? (
 <Link
 href={`/prop-simulator/firms/${firm.profile_id}/edit`}
 className="text-xs text-accent hover:underline"
 >
 Edit →
 </Link>
 ) : (
 <span
 className="cursor-not-allowed text-xs text-text-mute"
 title="Editor needs the live /profiles endpoint"
 >
 —
 </span>
 )}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 );
}
