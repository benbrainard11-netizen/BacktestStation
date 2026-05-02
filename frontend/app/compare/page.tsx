"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { RunPicker } from "@/components/ui/RunPicker";
import { cn } from "@/lib/utils";

type RunMetrics = {
  run_id: number;
  run_name: string;
  total_trades: number;
  win_rate: number | null;
  avg_r: number | null;
  total_r: number | null;
  total_pnl: number | null;
  max_drawdown: number | null;
  sharpe: number | null;
  sortino: number | null;
  profit_factor: number | null;
  avg_win_r: number | null;
  avg_loss_r: number | null;
  expectancy_r: number | null;
  best_trade_r: number | null;
  worst_trade_r: number | null;
};

type RunHeader = {
  id: number;
  name: string;
  symbol: string | null;
  source: string;
  status: string;
  created_at: string;
};

type Phase =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; runs: { header: RunHeader; metrics: RunMetrics }[] };

// Metric definitions: which way is "better" + how to format.
type MetricDef = {
  key: keyof RunMetrics;
  label: string;
  better: "higher" | "lower" | "neither";
  fmt: (v: number | null) => string;
};

function pct(v: number | null): string {
  if (v == null) return "—";
  const n = Math.abs(v) <= 1 ? v * 100 : v;
  return `${n.toFixed(1)}%`;
}

function num(d: number) {
  return (v: number | null): string => {
    if (v == null) return "—";
    return v.toLocaleString(undefined, {
      minimumFractionDigits: d,
      maximumFractionDigits: d,
    });
  };
}

function money(v: number | null): string {
  if (v == null) return "—";
  return v.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

const METRICS: MetricDef[] = [
  { key: "total_trades", label: "Trades", better: "neither", fmt: num(0) },
  { key: "win_rate", label: "Win rate", better: "higher", fmt: pct },
  { key: "avg_r", label: "Avg R", better: "higher", fmt: num(2) },
  { key: "total_r", label: "Total R", better: "higher", fmt: num(2) },
  { key: "total_pnl", label: "Total P&L", better: "higher", fmt: money },
  { key: "expectancy_r", label: "Expectancy R", better: "higher", fmt: num(3) },
  { key: "max_drawdown", label: "Max drawdown", better: "lower", fmt: num(2) },
  { key: "sharpe", label: "Sharpe", better: "higher", fmt: num(2) },
  { key: "sortino", label: "Sortino", better: "higher", fmt: num(2) },
  {
    key: "profit_factor",
    label: "Profit factor",
    better: "higher",
    fmt: num(2),
  },
  { key: "avg_win_r", label: "Avg win R", better: "higher", fmt: num(2) },
  {
    key: "avg_loss_r",
    label: "Avg loss R",
    better: "higher",
    fmt: num(2),
  },
  { key: "best_trade_r", label: "Best trade R", better: "higher", fmt: num(2) },
  {
    key: "worst_trade_r",
    label: "Worst trade R",
    better: "higher",
    fmt: num(2),
  },
];

async function fetchRunBundle(
  id: number,
): Promise<{ header: RunHeader; metrics: RunMetrics }> {
  const [hRes, mRes] = await Promise.all([
    fetch(`/api/backtests/${id}`),
    fetch(`/api/backtests/${id}/metrics`),
  ]);
  if (!hRes.ok) throw new Error(`run #${id} header: ${hRes.status}`);
  const header = (await hRes.json()) as RunHeader;
  // Metrics 404 is expected for runs without computed metrics (live
  // imports, in-flight runs, etc). Don't fail the whole comparison;
  // render the run with all-null metric cells.
  const metricsRaw = mRes.ok
    ? ((await mRes.json()) as Partial<RunMetrics>)
    : {};
  return {
    header,
    metrics: {
      run_id: id,
      run_name: header.name,
      total_trades: 0,
      win_rate: null,
      avg_r: null,
      total_r: null,
      total_pnl: null,
      max_drawdown: null,
      sharpe: null,
      sortino: null,
      profit_factor: null,
      avg_win_r: null,
      avg_loss_r: null,
      expectancy_r: null,
      best_trade_r: null,
      worst_trade_r: null,
      ...metricsRaw,
    },
  };
}

function findWinner(
  values: (number | null)[],
  better: MetricDef["better"],
): number | null {
  if (better === "neither") return null;
  const indexed = values
    .map((v, i) => ({ v, i }))
    .filter((x) => x.v != null) as { v: number; i: number }[];
  if (indexed.length < 2) return null;
  if (better === "higher") {
    return indexed.reduce((a, b) => (b.v > a.v ? b : a)).i;
  }
  return indexed.reduce((a, b) => (b.v < a.v ? b : a)).i;
}

export default function ComparePage() {
  const [picked, setPicked] = useState<number[]>([]);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  // Refetch whenever the picked set changes (debounced via simple effect).
  useEffect(() => {
    if (picked.length === 0) {
      setPhase({ kind: "idle" });
      return;
    }
    let cancelled = false;
    setPhase({ kind: "loading" });
    Promise.all(picked.map(fetchRunBundle))
      .then((runs) => {
        if (cancelled) return;
        // Preserve picker order
        runs.sort(
          (a, b) => picked.indexOf(a.header.id) - picked.indexOf(b.header.id),
        );
        setPhase({ kind: "data", runs });
      })
      .catch((err) => {
        if (cancelled) return;
        setPhase({
          kind: "error",
          message: err instanceof Error ? err.message : "Network error",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [picked]);

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={`COMPARE · ${picked.length} OF 4 RUNS`}
        title="Compare runs"
        sub="Pick 2 to 4 backtest runs and see metrics side-by-side. Winner per row is highlighted (best for higher-is-better metrics, lowest for drawdown, etc)."
      />

      <Card className="mt-2">
        <CardHead title="Pick runs" eyebrow="up to 4" />
        <div className="px-4 py-4">
          <RunPicker
            multi
            value={picked}
            onChange={(ids) => setPicked(ids as number[])}
            max={4}
            placeholder="Add a run…"
          />
          {picked.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {picked.map((id) => (
                <span
                  key={id}
                  className="inline-flex items-center gap-1 rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[11px]"
                >
                  #{id}
                  <button
                    type="button"
                    onClick={() => setPicked(picked.filter((x) => x !== id))}
                    className="ml-1 text-ink-3 hover:text-neg"
                    aria-label={`Remove run ${id}`}
                  >
                    ×
                  </button>
                </span>
              ))}
              {picked.length > 0 && (
                <button
                  type="button"
                  onClick={() => setPicked([])}
                  className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3 hover:text-neg"
                >
                  clear all
                </button>
              )}
            </div>
          )}
        </div>
      </Card>

      <div className="mt-4">
        {phase.kind === "idle" && (
          <Card>
            <EmptyState
              title="no runs picked"
              blurb="Pick at least 2 runs above to see them side-by-side."
            />
          </Card>
        )}
        {phase.kind === "loading" && (
          <Card className="px-6 py-12 text-center text-[12px] text-ink-3">
            Loading metrics…
          </Card>
        )}
        {phase.kind === "error" && (
          <Card className="border-neg/30 px-6 py-12 text-center text-[12px] text-neg">
            {phase.message}
          </Card>
        )}
        {phase.kind === "data" && phase.runs.length === 1 && (
          <Card>
            <EmptyState
              title="add another run"
              blurb="Comparison needs at least 2 runs."
            />
          </Card>
        )}
        {phase.kind === "data" && phase.runs.length >= 2 && (
          <ComparisonTable runs={phase.runs} />
        )}
      </div>
    </div>
  );
}

function ComparisonTable({
  runs,
}: {
  runs: { header: RunHeader; metrics: RunMetrics }[];
}) {
  return (
    <Card>
      <CardHead title="Side-by-side" eyebrow={`${runs.length} runs`} />
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-line">
              <th className="px-3 py-2 text-left font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
                Metric
              </th>
              {runs.map((r) => (
                <th
                  key={r.header.id}
                  className="px-3 py-2 text-right font-mono text-[10.5px] font-semibold text-ink-2"
                >
                  <Link
                    href={`/backtests/${r.header.id}`}
                    className="hover:text-accent"
                  >
                    {r.header.name}
                  </Link>
                  <div className="mt-0.5 flex items-center justify-end gap-1">
                    <Chip>{r.header.source}</Chip>
                    {r.header.symbol && (
                      <span className="font-mono text-[10.5px] text-ink-3">
                        {r.header.symbol}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map((m) => {
              const values = runs.map(
                (r) => (r.metrics[m.key] as number | null) ?? null,
              );
              const winner = findWinner(values, m.better);
              return (
                <tr
                  key={String(m.key)}
                  className="border-b border-line last:border-b-0 hover:bg-bg-2"
                >
                  <td className="px-3 py-2 text-ink-2">{m.label}</td>
                  {values.map((v, i) => (
                    <td
                      key={i}
                      className={cn(
                        "px-3 py-2 text-right font-mono",
                        winner === i ? "font-semibold text-pos" : "text-ink-1",
                      )}
                    >
                      {m.fmt(v)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
