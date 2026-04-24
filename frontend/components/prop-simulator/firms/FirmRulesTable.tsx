import FirmRuleStatusBadge from "@/components/prop-simulator/shared/FirmRuleStatusBadge";
import type { FirmRuleProfile } from "@/lib/prop-simulator/types";

interface FirmRulesTableProps {
  firms: FirmRuleProfile[];
}

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return `$${value.toLocaleString("en-US")}`;
}

function formatDays(value: number | null): string {
  if (value === null) return "—";
  return `${value}`;
}

function formatConsistency(firm: FirmRuleProfile): string {
  if (!firm.consistency_rule_enabled || firm.consistency_rule_value === null) {
    return "—";
  }
  if (firm.consistency_rule_type === "best_day_pct_of_total") {
    return `best day ≤ ${Math.round(firm.consistency_rule_value * 100)}%`;
  }
  return String(firm.consistency_rule_value);
}

function formatPayoutRule(firm: FirmRuleProfile): string {
  const parts: string[] = [`${firm.payout_split}% split`];
  if (firm.payout_min_days !== null) parts.push(`${firm.payout_min_days}d min`);
  if (firm.payout_min_profit !== null) {
    parts.push(`$${firm.payout_min_profit.toLocaleString()} min`);
  }
  return parts.join(" · ");
}

function formatFees(firm: FirmRuleProfile): string {
  return `eval $${firm.eval_fee} · act $${firm.activation_fee} · reset $${firm.reset_fee}`;
}

function formatTrailing(firm: FirmRuleProfile): string {
  if (!firm.trailing_drawdown_enabled) return "none";
  return firm.trailing_drawdown_type.replace(/_/g, " ");
}

export default function FirmRulesTable({ firms }: FirmRulesTableProps) {
  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full border-collapse text-left font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/40 text-[10px] uppercase tracking-widest text-zinc-500">
            <th className="px-3 py-2">Firm</th>
            <th className="px-3 py-2 text-right">Size</th>
            <th className="px-3 py-2">Phase</th>
            <th className="px-3 py-2 text-right">Target</th>
            <th className="px-3 py-2 text-right">Max DD</th>
            <th className="px-3 py-2 text-right">Daily loss</th>
            <th className="px-3 py-2">Trailing</th>
            <th className="px-3 py-2 text-right">Min days</th>
            <th className="px-3 py-2">Consistency</th>
            <th className="px-3 py-2">Payout</th>
            <th className="px-3 py-2">Fees</th>
            <th className="px-3 py-2">Verified</th>
            <th className="px-3 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {firms.map((firm) => (
            <tr
              key={firm.profile_id}
              className="border-b border-zinc-900/80 text-zinc-300 last:border-b-0 hover:bg-zinc-900/40"
            >
              <td className="px-3 py-2">
                <div className="text-zinc-100">{firm.firm_name}</div>
                <div className="text-[10px] text-zinc-500">{firm.account_name}</div>
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatCurrency(firm.account_size)}
              </td>
              <td className="px-3 py-2 text-zinc-400">{firm.phase_type}</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatCurrency(firm.profit_target)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatCurrency(firm.max_drawdown)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatCurrency(firm.daily_loss_limit)}
              </td>
              <td className="px-3 py-2 text-zinc-400">{formatTrailing(firm)}</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatDays(firm.minimum_trading_days)}
              </td>
              <td className="px-3 py-2 text-zinc-400">{formatConsistency(firm)}</td>
              <td className="px-3 py-2 text-zinc-400">{formatPayoutRule(firm)}</td>
              <td className="px-3 py-2 text-zinc-400">{formatFees(firm)}</td>
              <td className="px-3 py-2">
                <FirmRuleStatusBadge
                  status={firm.verification_status}
                  lastVerifiedAt={firm.rule_last_verified_at}
                />
              </td>
              <td className="px-3 py-2 text-right">
                <button
                  type="button"
                  disabled
                  className="cursor-not-allowed border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-600"
                  title="Editor lands with firm-rule persistence"
                >
                  edit
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
