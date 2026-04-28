// Three-column breakdown — outcome rates · risk sweep · confidence
// subscores. Each column has its own little numbered header.

import { cn } from "@/lib/utils";
import type {
 RiskSweepRow,
 SimulationAggregatedStats,
 SimulatorConfidenceScore,
} from "@/lib/prop-simulator/types";

interface BreakdownColumnsProps {
 stats: SimulationAggregatedStats;
 riskSweep: RiskSweepRow[] | null;
 confidence: SimulatorConfidenceScore;
}

function ColumnHeader({
 number,
 title,
}: {
 number: string;
 title: string;
}) {
 return (
 <header className="mb-4 flex items-baseline gap-3 border-b border-border-strong pb-2">
 <span className="text-[10px] tabular-nums text-text-mute">{number}</span>
 <h3 className="text-xs text-text-dim">
 {title}
 </h3>
 </header>
 );
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
 <div className="flex items-baseline justify-between gap-3 border-b border-border py-1.5 last:border-b-0">
 <span className="text-[10px] tracking-[0.32em] text-text-mute">
 {label}
 </span>
 <span className={cn("font-light tabular-nums", toneClass)}>{value}</span>
 </div>
 );
}

function pct(v: number): string {
 return `${(v * 100).toFixed(1)}%`;
}

function dollar(v: number): string {
 const sign = v < 0 ? "-" : v > 0 ? "+" : "";
 return `${sign}$${Math.abs(Math.round(v)).toLocaleString("en-US")}`;
}

export default function BreakdownColumns({
 stats,
 riskSweep,
 confidence,
}: BreakdownColumnsProps) {
 const sweepRows = (riskSweep ?? []).slice(0, 5);

 const subscoreRows: { label: string; score: number }[] = [
 { label: "Monte Carlo stability", score: confidence.subscores.monte_carlo_stability },
 { label: "Trade pool quality", score: confidence.subscores.trade_pool_quality },
 { label: "Day pool quality", score: confidence.subscores.day_pool_quality },
 { label: "Firm rule accuracy", score: confidence.subscores.firm_rule_accuracy },
 { label: "Risk model accuracy", score: confidence.subscores.risk_model_accuracy },
 { label: "Backtest input quality", score: confidence.subscores.backtest_input_quality },
 ];

 return (
 <section className="grid grid-cols-1 gap-10 lg:grid-cols-3 lg:gap-14">
 <div>
 <ColumnHeader number="01" title="Outcome rates" />
 <Row label="Pass" value={pct(stats.pass_rate.value)} tone="positive" />
 <Row label="Payout" value={pct(stats.payout_rate.value)} />
 <Row label="Fail" value={pct(stats.fail_rate.value)} tone="negative" />
 <Row label="Profit-target hit" value={pct(stats.profit_target_hit_rate)} />
 <Row label="Payout blocked" value={pct(stats.payout_blocked_rate)} />
 <Row label="Trailing-DD fail" value={pct(stats.trailing_drawdown_failure_rate)} />
 <Row label="Daily-loss fail" value={pct(stats.daily_loss_failure_rate)} />
 </div>

 <div>
 <ColumnHeader number="02" title="Risk sweep" />
 {sweepRows.length === 0 ? (
 <p className="text-[10px] tracking-[0.32em] text-text-mute">
 No sweep on this run.
 </p>
 ) : (
 sweepRows.map((row) => (
 <Row
 key={row.risk_per_trade}
 label={`$${row.risk_per_trade}/tr · pass`}
 value={`${pct(row.pass_rate)} · ${dollar(row.ev_after_fees)}`}
 tone={
 row.ev_after_fees > 0
 ? "positive"
 : row.ev_after_fees < 0
 ? "negative"
 : "neutral"
 }
 />
 ))
 )}
 </div>

 <div>
 <ColumnHeader number="03" title="Confidence subscores" />
 {subscoreRows.map((r) => (
 <Row key={r.label} label={r.label} value={`${r.score} / 100`} />
 ))}
 <p className="mt-3 text-[10px] tracking-[0.32em] text-text-mute">
 {confidence.weaknesses[0] ?? "—"}
 </p>
 </div>
 </section>
 );
}
