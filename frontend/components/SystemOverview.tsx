"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Pill from "@/components/ui/Pill";
import StatTile from "@/components/ui/StatTile";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type Note = components["schemas"]["NoteRead"];
type LiveStatus = components["schemas"]["LiveMonitorStatus"];

interface Aggregate {
  strategies: Strategy[];
  runs: BacktestRun[];
  notes: Note[];
  monitor: LiveStatus | null;
}

/**
 * Compact "across the system" strip that sits above the strategy-scoped
 * dashboard. Shows live bot status, today's P&L, strategy + run counts.
 * Refreshes every 30s — live P&L on the same cadence as the rest of the
 * dashboard's polling.
 */
export default function SystemOverview() {
  const [agg, setAgg] = useState<Aggregate | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const [strategies, runs, notes, monitor] = await Promise.all([
          fetch("/api/strategies", { cache: "no-store" }).then((r) =>
            r.ok ? (r.json() as Promise<Strategy[]>) : ([] as Strategy[]),
          ),
          fetch("/api/backtests", { cache: "no-store" }).then((r) =>
            r.ok ? (r.json() as Promise<BacktestRun[]>) : ([] as BacktestRun[]),
          ),
          fetch("/api/notes", { cache: "no-store" }).then((r) =>
            r.ok ? (r.json() as Promise<Note[]>) : ([] as Note[]),
          ),
          fetch("/api/monitor/live", { cache: "no-store" })
            .then((r) => (r.ok ? (r.json() as Promise<LiveStatus>) : null))
            .catch(() => null) as Promise<LiveStatus | null>,
        ]);
        if (!cancelled) setAgg({ strategies, runs, notes, monitor });
      } catch {
        // best-effort; leave previous state
      }
    }
    void tick();
    const id = setInterval(tick, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (agg === null) {
    return (
      <div className="mb-4 flex items-center justify-between rounded-lg border border-border bg-surface px-[18px] py-3">
        <p className="m-0 text-xs text-text-mute">across the system · loading…</p>
        <Link href="/monitor" className="text-xs text-accent hover:underline">
          Full overview →
        </Link>
      </div>
    );
  }

  const liveRunning =
    agg.monitor?.source_exists === true &&
    agg.monitor.strategy_status === "running";
  const todayPnl = liveRunning ? agg.monitor?.today_pnl ?? null : null;
  const tradesToday = liveRunning ? agg.monitor?.trades_today ?? null : null;
  const liveStrategies = agg.strategies.filter(
    (s) => s.status === "live" || s.status === "forward_test",
  ).length;

  return (
    <div className="mb-6 rounded-lg border border-border bg-surface px-[18px] py-3">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-mute">across the system</span>
          {liveRunning ? (
            <Pill tone="pos">live · running</Pill>
          ) : agg.monitor?.source_exists ? (
            <Pill tone="warn">live · {agg.monitor.strategy_status}</Pill>
          ) : (
            <Pill tone="neutral">no live bot</Pill>
          )}
        </div>
        <Link href="/monitor" className="text-xs text-accent hover:underline">
          Full overview →
        </Link>
      </div>
      <div className="grid grid-cols-4 gap-3">
        <MiniTile
          label="Today P&L"
          value={
            todayPnl === null
              ? "—"
              : `${todayPnl >= 0 ? "+" : "-"}$${Math.abs(todayPnl).toFixed(2)}`
          }
          sub={
            liveRunning && tradesToday !== null
              ? `${tradesToday} trade${tradesToday === 1 ? "" : "s"}`
              : "no live data"
          }
          tone={
            todayPnl === null ? "neutral" : todayPnl >= 0 ? "pos" : "neg"
          }
        />
        <MiniTile
          label="Strategies"
          value={String(agg.strategies.length)}
          sub={
            liveStrategies > 0
              ? `${liveStrategies} deployed`
              : "none deployed"
          }
          tone="neutral"
          href="/strategies"
        />
        <MiniTile
          label="Runs"
          value={String(agg.runs.length)}
          sub="imported backtests"
          tone="neutral"
          href="/backtests"
        />
        <MiniTile
          label="Notes"
          value={String(agg.notes.length)}
          sub="research workspace"
          tone="neutral"
          href="/journal"
        />
      </div>
    </div>
  );
}

function MiniTile({
  label,
  value,
  sub,
  tone,
  href,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "pos" | "neg" | "warn" | "neutral";
  href?: string;
}) {
  // Reuse StatTile but scale it down — same primitive, smaller value.
  return (
    <StatTile
      label={label}
      value={
        <span className="text-[20px] tabular-nums leading-none">{value}</span>
      }
      sub={sub}
      tone={tone}
      href={href}
      className="px-3 py-2.5"
    />
  );
}
