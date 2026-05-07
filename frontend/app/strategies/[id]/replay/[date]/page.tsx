"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { use } from "react";

import { Card, Chip } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

// Lightweight-charts uses window APIs; load on client only.
const ReplayChart = dynamic(() => import("@/components/replay/ReplayChart"), {
  ssr: false,
});

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type TradeRead = components["schemas"]["TradeRead"];
type ReplayPayload = components["schemas"]["ReplayPayload"];

type LoadState<T> =
  | { kind: "loading" }
  | { kind: "data"; data: T }
  | { kind: "error"; message: string };

interface DayTrade extends TradeRead {
  _run_name: string;
  _run_kind: "canonical" | "paper" | "live" | "verification" | "other";
}

function classifyRun(r: BacktestRun): DayTrade["_run_kind"] {
  const n = (r.name ?? "").toLowerCase();
  if (n.includes("paper")) return "paper";
  if (n.includes("engine_replay") || n.includes("verification")) return "verification";
  if (n.includes("backtest") || n.includes("canonical")) return "canonical";
  if (r.source === "live") return "live";
  return "other";
}

const KIND_TONE: Record<DayTrade["_run_kind"], "pos" | "accent" | "default"> = {
  canonical: "pos",
  paper: "accent",
  live: "pos",
  verification: "default",
  other: "default",
};

// BacktestStation's internal bar warehouse is keyed by contract symbol
// (NQM6, NQU6 etc.) not continuous (NQ.c.0). We use NQM6 as the default
// for now — for dates outside that contract's window, the chart will
// show empty until parquet_mirror is fixed to also write continuous
// partitions. See production/backfill_promotion_check_strategy_links.py
// commentary + the ben-247 followups.
const REPLAY_SYMBOL = "NQM6";

export default function StrategyReplayDayPage({
  params,
}: {
  params: Promise<{ id: string; date: string }>;
}) {
  const { id, date } = use(params);
  const strategyId = Number.parseInt(id, 10);
  const router = useRouter();

  const [strategyState, setStrategyState] = useState<LoadState<Strategy>>({ kind: "loading" });
  const [runsState, setRunsState] = useState<LoadState<BacktestRun[]>>({ kind: "loading" });
  const [allTradesState, setAllTradesState] = useState<LoadState<DayTrade[]>>({ kind: "loading" });
  const [payloadState, setPayloadState] = useState<LoadState<ReplayPayload>>({ kind: "loading" });

  // Initial fetch — strategy + runs (so we know which trades belong to it)
  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    async function load() {
      try {
        const [stratRes, runsRes] = await Promise.all([
          fetch(`/api/strategies/${strategyId}`, { cache: "no-store", signal: ctrl.signal }),
          fetch(`/api/backtests`, { cache: "no-store", signal: ctrl.signal }),
        ]);
        if (cancelled) return;
        if (stratRes.ok) setStrategyState({ kind: "data", data: await stratRes.json() });
        if (runsRes.ok) setRunsState({ kind: "data", data: await runsRes.json() });
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : "Network error";
          setStrategyState({ kind: "error", message: msg });
          setRunsState({ kind: "error", message: msg });
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [strategyId]);

  const strategy = strategyState.kind === "data" ? strategyState.data : null;
  const versionIds = useMemo(
    () => new Set((strategy?.versions ?? []).map((v) => v.id)),
    [strategy],
  );
  const allRuns = runsState.kind === "data" ? runsState.data : [];
  const strategyRuns = useMemo(
    () => allRuns.filter((r) => versionIds.has(r.strategy_version_id)),
    [allRuns, versionIds],
  );

  // Fetch trades for all runs of this strategy. We need them all so
  // we can compute prev/next-day navigation across the full history.
  useEffect(() => {
    if (strategyRuns.length === 0) return;
    let cancelled = false;
    const ctrl = new AbortController();
    setAllTradesState({ kind: "loading" });
    async function loadAll() {
      try {
        const out: DayTrade[] = [];
        await Promise.all(
          strategyRuns.map(async (r) => {
            const res = await fetch(`/api/backtests/${r.id}/trades`, {
              cache: "no-store",
              signal: ctrl.signal,
            });
            if (!res.ok) return;
            const list = (await res.json()) as TradeRead[];
            const kind = classifyRun(r);
            for (const t of list) {
              out.push({ ...t, _run_name: r.name ?? `run ${r.id}`, _run_kind: kind });
            }
          }),
        );
        if (!cancelled) setAllTradesState({ kind: "data", data: out });
      } catch (e) {
        if (!cancelled) {
          setAllTradesState({
            kind: "error",
            message: e instanceof Error ? e.message : "Network error",
          });
        }
      }
    }
    void loadAll();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [strategyRuns]);

  // Fetch the bar payload for this date (auto, not behind a form)
  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    setPayloadState({ kind: "loading" });
    async function loadPayload() {
      try {
        const url = `/api/replay/${encodeURIComponent(REPLAY_SYMBOL)}/${encodeURIComponent(date)}`;
        const res = await fetch(url, { cache: "no-store", signal: ctrl.signal });
        if (!cancelled) {
          if (res.ok) {
            setPayloadState({ kind: "data", data: await res.json() });
          } else {
            const body = await res.text();
            setPayloadState({
              kind: "error",
              message: `${res.status} ${res.statusText} — ${body}`,
            });
          }
        }
      } catch (e) {
        if (!cancelled) {
          setPayloadState({
            kind: "error",
            message: e instanceof Error ? e.message : "Network error",
          });
        }
      }
    }
    void loadPayload();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [date]);

  // Trades on this specific day
  const allTrades = allTradesState.kind === "data" ? allTradesState.data : [];
  const dayTrades = useMemo(
    () => allTrades.filter((t) => (t.entry_ts ?? "").slice(0, 10) === date),
    [allTrades, date],
  );

  // Prev/next dates across all trades (excluding verification by default)
  const tradeDates = useMemo(() => {
    const set = new Set<string>();
    for (const t of allTrades) {
      if (t._run_kind === "verification") continue;
      const d = (t.entry_ts ?? "").slice(0, 10);
      if (d) set.add(d);
    }
    return Array.from(set).sort();
  }, [allTrades]);
  const idx = tradeDates.indexOf(date);
  const prevDate = idx > 0 ? tradeDates[idx - 1] : null;
  const nextDate = idx >= 0 && idx < tradeDates.length - 1 ? tradeDates[idx + 1] : null;

  function go(d: string | null) {
    if (!d) return;
    router.push(`/strategies/${strategyId}/replay/${d}`);
  }

  const dateLabel = useMemo(() => {
    const dt = new Date(date);
    return dt.toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }, [date]);

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-6">
      {/* Header strip — back / prev / date / next / close */}
      <div className="flex items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          <Link
            href={`/strategies/${strategyId}/replay`}
            className="inline-flex h-8 items-center gap-1.5 rounded border border-line bg-bg-2 px-2.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-2 transition-colors hover:border-line-3 hover:text-ink-0"
          >
            <ChevronLeft size={12} />
            calendar
          </Link>
          <button
            type="button"
            onClick={() => go(prevDate)}
            disabled={!prevDate}
            className="inline-flex h-8 items-center gap-1.5 rounded border border-line bg-bg-2 px-2.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-2 transition-colors hover:border-line-3 hover:text-ink-0 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ChevronLeft size={12} />
            prev day
          </button>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-[14px] font-semibold text-ink-0">{dateLabel}</span>
          {strategy && (
            <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
              · {strategy.name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => go(nextDate)}
            disabled={!nextDate}
            className="inline-flex h-8 items-center gap-1.5 rounded border border-line bg-bg-2 px-2.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-2 transition-colors hover:border-line-3 hover:text-ink-0 disabled:cursor-not-allowed disabled:opacity-40"
          >
            next day
            <ChevronRight size={12} />
          </button>
          <Link
            href={`/strategies/${strategyId}/replay`}
            className="inline-flex h-8 w-8 items-center justify-center rounded border border-line bg-bg-2 text-ink-3 hover:border-line-3 hover:text-ink-0"
            aria-label="Close"
          >
            <X size={14} />
          </Link>
        </div>
      </div>

      {/* Trade summary row */}
      {dayTrades.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-3">
          {dayTrades.map((t) => (
            <TradeSummaryRow key={`${t.id}-${t._run_name}`} trade={t} />
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="mt-3">
        {payloadState.kind === "loading" && (
          <Card>
            <div className="px-4 py-12 text-center text-[12.5px] text-ink-3">
              Loading bars…
            </div>
          </Card>
        )}
        {payloadState.kind === "error" && (
          <Card className="border-warn-line bg-warn-soft">
            <div className="px-4 py-6 text-[12.5px] text-ink-1">
              <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-warn">
                no bars available for {date}
              </div>
              <div className="mt-2 leading-relaxed text-ink-2">
                {payloadState.message}
              </div>
              <div className="mt-3 text-[11px] text-ink-3">
                The internal bar warehouse only has dates the parquet_mirror
                has processed. See the ben-247 data-pipeline followups
                (continuous-symbol partitions + warehouse sync) for the fix.
              </div>
            </div>
          </Card>
        )}
        {payloadState.kind === "data" && (
          <Card>
            <ReplayChart payload={payloadState.data} />
          </Card>
        )}
      </div>
    </div>
  );
}

function TradeSummaryRow({ trade: t }: { trade: DayTrade }) {
  return (
    <div className="flex flex-1 items-center gap-3 rounded border border-line bg-bg-2 px-3 py-2">
      <Chip tone={KIND_TONE[t._run_kind]}>{t._run_kind}</Chip>
      <span
        className={cn(
          "font-mono text-[11px] font-semibold uppercase",
          t.side === "long" ? "text-pos" : "text-neg",
        )}
      >
        {t.side}
      </span>
      <span className="font-mono text-[11px] tabular-nums text-ink-1">
        {t.entry_price?.toFixed(2)} → {t.exit_price?.toFixed(2)}
      </span>
      <span
        className={cn(
          "ml-auto font-mono text-[12px] font-semibold tabular-nums",
          t.r_multiple == null
            ? "text-ink-3"
            : t.r_multiple > 0
              ? "text-pos"
              : t.r_multiple < 0
                ? "text-neg"
                : "text-ink-2",
        )}
      >
        {t.r_multiple == null
          ? "—"
          : `${t.r_multiple >= 0 ? "+" : ""}${t.r_multiple.toFixed(2)}R`}
      </span>
      {t.pnl != null && (
        <span
          className={cn(
            "font-mono text-[11px] tabular-nums",
            t.pnl > 0 ? "text-pos" : t.pnl < 0 ? "text-neg" : "text-ink-2",
          )}
        >
          {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(0)}
        </span>
      )}
      <span className="font-mono text-[10px] text-ink-4">{t.exit_reason ?? "—"}</span>
    </div>
  );
}
