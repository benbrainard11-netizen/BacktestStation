import type { components } from "@/lib/api/generated";

type RunMetrics = components["schemas"]["RunMetricsRead"];
import { cn } from "@/lib/utils";

type Tone = "positive" | "negative" | "neutral";

interface MetricsGridProps {
 metrics: RunMetrics | null;
}

export default function MetricsGrid({ metrics }: MetricsGridProps) {
 if (metrics === null) {
 return (
 <div className="border border-dashed border-border bg-surface px-4 py-6">
 <p className="tabular-nums text-[10px] text-text-mute">
 Metrics not imported
 </p>
 <p className="mt-2 text-xs text-text-mute">
 Include a metrics.json file on the next import to populate this panel.
 </p>
 </div>
 );
 }

 const cards = [
 cardFor("Net PnL", metrics.net_pnl, formatDollars, signedTone),
 cardFor("Net R", metrics.net_r, formatR, signedTone),
 cardFor("Win Rate", metrics.win_rate, formatPercentFraction, neutralTone),
 cardFor(
 "Profit Factor",
 metrics.profit_factor,
 (v) => v.toFixed(2),
 (v) => (v >= 1 ? "positive" : "negative"),
 ),
 cardFor(
 "Max Drawdown",
 metrics.max_drawdown,
 formatR,
 (v) => (v < 0 ? "negative" : "neutral"),
 ),
 cardFor("Avg R", metrics.avg_r, formatR, signedTone),
 cardFor("Avg Win", metrics.avg_win, formatR, signedTone),
 cardFor("Avg Loss", metrics.avg_loss, formatR, signedTone),
 cardFor("Trades", metrics.trade_count, (v) => v.toFixed(0), neutralTone),
 cardFor(
 "Longest Loss Streak",
 metrics.longest_losing_streak,
 (v) => v.toFixed(0),
 neutralTone,
 ),
 cardFor("Best Trade", metrics.best_trade, formatDollars, signedTone),
 cardFor("Worst Trade", metrics.worst_trade, formatDollars, signedTone),
 ];

 return (
 <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
 {cards.map((card) => (
 <Card key={card.label} {...card} />
 ))}
 </div>
 );
}

interface CardProps {
 label: string;
 display: string;
 tone: Tone;
}

function Card({ label, display, tone }: CardProps) {
 return (
 <div className="flex min-w-0 flex-col gap-2 border border-border bg-surface px-3 py-3">
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span className={cn("tabular-nums text-lg leading-none", TONE[tone])}>
 {display}
 </span>
 </div>
 );
}

const TONE: Record<Tone, string> = {
 positive: "text-pos",
 negative: "text-neg",
 neutral: "text-text",
};

function cardFor(
 label: string,
 value: number | null,
 format: (v: number) => string,
 toneFn: (v: number) => Tone,
): CardProps {
 if (value === null) return { label, display: "—", tone: "neutral" };
 return { label, display: format(value), tone: toneFn(value) };
}

function signedTone(value: number): Tone {
 if (value > 0) return "positive";
 if (value < 0) return "negative";
 return "neutral";
}

function neutralTone(): Tone {
 return "neutral";
}

function formatDollars(value: number): string {
 const sign = value < 0 ? "-" : value > 0 ? "+" : "";
 const abs = Math.abs(value).toLocaleString("en-US", {
 style: "currency",
 currency: "USD",
 minimumFractionDigits: 2,
 maximumFractionDigits: 2,
 });
 return `${sign}${abs}`;
}

function formatR(value: number): string {
 const sign = value > 0 ? "+" : "";
 return `${sign}${value.toFixed(2)}R`;
}

function formatPercentFraction(value: number): string {
 return `${(value * 100).toFixed(2)}%`;
}
