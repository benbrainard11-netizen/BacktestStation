import Link from "next/link";
import { ArrowUpRight, Plus } from "lucide-react";

import Panel from "@/components/Panel";
import SimulationCoreVisual from "@/components/prop-simulator/SimulationCoreVisual";
import { cn } from "@/lib/utils";
import type { DashboardSummary } from "@/lib/prop-simulator/types";
import {
  formatCurrencySigned,
  formatPercent,
} from "@/lib/prop-simulator/format";

interface SimulationCorePanelProps {
  summary: DashboardSummary;
}

interface CoreStat {
  label: string;
  value: string;
  tone?: "neutral" | "positive" | "negative";
}

function buildCoreStats(summary: SimulationCorePanelProps["summary"]): CoreStat[] {
  const featured = summary.best_setup ?? summary.highest_ev_setup;
  const recent = summary.recent_runs[0] ?? null;
  const evTone =
    featured && featured.ev_after_fees > 0
      ? "positive"
      : featured && featured.ev_after_fees < 0
        ? "negative"
        : "neutral";
  return [
    { label: "Paths", value: "10,000" },
    {
      label: "Pass probability",
      value: featured ? formatPercent(featured.pass_rate) : "—",
    },
    {
      label: "Payout probability",
      value: featured ? formatPercent(featured.payout_rate) : "—",
    },
    {
      label: "EV after fees",
      value: featured ? formatCurrencySigned(featured.ev_after_fees) : "—",
      tone: evTone,
    },
    {
      label: "Confidence",
      value: recent ? `${recent.confidence} / 100` : "—",
    },
  ];
}

const TONE_CLASS: Record<NonNullable<CoreStat["tone"]>, string> = {
  positive: "text-emerald-400",
  negative: "text-rose-400",
  neutral: "text-zinc-100",
};

function StatBlock({ stat }: { stat: CoreStat }) {
  const toneClass = TONE_CLASS[stat.tone ?? "neutral"];
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-zinc-800/80 bg-zinc-950/40 px-3 py-2.5 shadow-edge-top">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {stat.label}
      </span>
      <span
        className={cn(
          "font-mono text-xl leading-none tracking-tight tabular-nums",
          toneClass,
        )}
      >
        {stat.value}
      </span>
    </div>
  );
}

export default function SimulationCorePanel({ summary }: SimulationCorePanelProps) {
  const stats = buildCoreStats(summary);
  return (
    <Panel
      title="Monte Carlo Simulation Core"
      meta="research instrument · mock"
      tone="hero"
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_240px]">
        <div className="flex min-w-0 flex-col gap-5">
          <p className="max-w-2xl text-sm text-zinc-400">
            Probability distribution from{" "}
            <span className="font-mono text-zinc-200">10,000</span>{" "}
            randomized account sequences sampled through firm rules,
            daily limits, trailing drawdown, and payout gates. Numbers
            below preview the most recent saved run.
          </p>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
            {stats.map((stat) => (
              <StatBlock key={stat.label} stat={stat} />
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/prop-simulator/new"
              className="inline-flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 shadow-dim transition-all duration-150 hover:-translate-y-px hover:border-zinc-600 hover:bg-zinc-800 hover:shadow-dim-hover"
            >
              <Plus className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
              New simulation
            </Link>
            <Link
              href="/prop-simulator/runs"
              className="inline-flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-400 transition-all duration-150 hover:-translate-y-px hover:border-zinc-700 hover:text-zinc-100"
            >
              <ArrowUpRight
                className="h-3 w-3"
                strokeWidth={1.75}
                aria-hidden="true"
              />
              Open runs
            </Link>
            <Link
              href="/prop-simulator/compare"
              className="inline-flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-400 transition-all duration-150 hover:-translate-y-px hover:border-zinc-700 hover:text-zinc-100"
            >
              <ArrowUpRight
                className="h-3 w-3"
                strokeWidth={1.75}
                aria-hidden="true"
              />
              Compare setups
            </Link>
          </div>
        </div>
        <div className="flex items-center justify-center">
          <SimulationCoreVisual />
        </div>
      </div>
    </Panel>
  );
}
