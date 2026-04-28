// Editorial pull-quote — set massive, italic, off-grid. Names the modal
// failure mode in plain language.

import { cn } from "@/lib/utils";
import type {
 FailureReason,
 SimulationAggregatedStats,
} from "@/lib/prop-simulator/types";

interface PullQuoteProps {
 stats: SimulationAggregatedStats;
}

const REASON_PHRASE: Record<NonNullable<FailureReason>, string> = {
 daily_loss_limit: "the daily loss limit",
 trailing_drawdown: "trailing drawdown",
 max_drawdown: "the static drawdown ceiling",
 consistency_rule: "the consistency rule",
 payout_blocked: "blocked payout gates",
 min_days_not_met: "the minimum-days requirement",
 account_expired: "running out of trading days",
 max_trades_reached: "hitting the trade ceiling",
 other: "an unclassified rule",
};

function rateForReason(
 reason: NonNullable<FailureReason>,
 stats: SimulationAggregatedStats,
): number {
 switch (reason) {
 case "daily_loss_limit":
 return stats.daily_loss_failure_rate;
 case "trailing_drawdown":
 return stats.trailing_drawdown_failure_rate;
 case "consistency_rule":
 return stats.consistency_failure_rate;
 case "payout_blocked":
 return stats.payout_blocked_rate;
 default:
 return 0;
 }
}

export default function PullQuote({ stats }: PullQuoteProps) {
 const reason = stats.most_common_failure_reason;
 if (reason === null) return null;

 const phrase = REASON_PHRASE[reason] ?? "an unclassified rule";
 const rate = rateForReason(reason, stats);
 const ratePct = (rate * 100).toFixed(1);

 return (
 <section className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:gap-12">
 <div className="hidden items-center lg:col-span-1 lg:flex">
 <span aria-hidden="true" className="block h-px w-full bg-text-dim" />
 </div>
 <blockquote
 className={cn(
 "lg:col-span-9",
 "font-extralight italic leading-[1.15] tracking-tight text-text",
 )}
 style={{ fontSize: "clamp(1.6rem, 3vw, 2.6rem)" }}
 >
 <span className="text-text-mute">“</span>The modal failure at this risk
 level is{" "}
 <span className="text-neg">{phrase}</span>
 <span className="text-text-mute"> — </span>
 <span className="tabular-nums text-text">{ratePct}%</span> of
 sequences die there.<span className="text-text-mute">”</span>
 </blockquote>
 <div className="hidden flex-col items-end justify-end lg:col-span-2 lg:flex">
 <span className="text-[10px] tracking-[0.32em] text-text-mute">
 Annotation
 </span>
 <span className="text-[10px] tracking-[0.32em] text-text-mute">
 0001
 </span>
 </div>
 </section>
 );
}
