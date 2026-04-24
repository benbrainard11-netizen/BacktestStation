import Panel from "@/components/Panel";
import type { RuleViolationEventType } from "@/lib/prop-simulator/types";

interface RuleViolationPanelProps {
  counts: Record<RuleViolationEventType, number>;
  sequenceCount: number;
}

const EVENT_LABELS: Record<RuleViolationEventType, string> = {
  daily_loss_limit: "Daily loss limit hit",
  trailing_drawdown: "Trailing drawdown hit",
  profit_target_hit: "Profit target hit",
  consistency_rule: "Consistency rule failed",
  payout_eligible: "Payout eligible",
  payout_blocked: "Payout blocked",
  max_contracts_exceeded: "Max contracts exceeded",
  minimum_days_not_met: "Min days not met",
};

const EVENT_ORDER: RuleViolationEventType[] = [
  "profit_target_hit",
  "payout_eligible",
  "payout_blocked",
  "trailing_drawdown",
  "daily_loss_limit",
  "consistency_rule",
  "minimum_days_not_met",
  "max_contracts_exceeded",
];

export default function RuleViolationPanel({
  counts,
  sequenceCount,
}: RuleViolationPanelProps) {
  return (
    <Panel title="Rule violation events" meta={`${sequenceCount.toLocaleString()} sequences`}>
      <table className="w-full text-left font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-widest text-zinc-500">
            <th className="py-2 pr-3">Event</th>
            <th className="py-2 pr-3 text-right">Count</th>
            <th className="py-2 pr-3 text-right">Per sequence</th>
          </tr>
        </thead>
        <tbody>
          {EVENT_ORDER.map((key) => {
            const count = counts[key];
            const perSeq = sequenceCount > 0 ? count / sequenceCount : 0;
            return (
              <tr
                key={key}
                className="border-b border-zinc-900/80 text-zinc-300 last:border-b-0"
              >
                <td className="py-2 pr-3 text-zinc-200">{EVENT_LABELS[key]}</td>
                <td className="py-2 pr-3 text-right tabular-nums">
                  {count.toLocaleString()}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums text-zinc-500">
                  {perSeq.toFixed(2)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
        Events can fire multiple times within a sequence. Per-sequence column =
        count ÷ sequences.
      </p>
    </Panel>
  );
}
