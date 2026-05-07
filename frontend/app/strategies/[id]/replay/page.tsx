"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { use } from "react";

import { Card, Chip, PageHeader } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

import { TradeCalendar, type CalendarTrade } from "./TradeCalendar";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type TradeRead = components["schemas"]["TradeRead"];

type LoadState<T> =
  | { kind: "loading" }
  | { kind: "data"; data: T }
  | { kind: "error"; message: string };

interface TradeWithRun extends TradeRead {
  _run_id: number;
  _run_name: string;
  _run_kind: "canonical" | "paper" | "live" | "verification" | "other";
}

function classifyRun(r: BacktestRun): TradeWithRun["_run_kind"] {
  const n = (r.name ?? "").toLowerCase();
  if (n.includes("paper")) return "paper";
  if (n.includes("engine_replay") || n.includes("verification")) return "verification";
  if (n.includes("backtest") || n.includes("canonical")) return "canonical";
  if (r.source === "live") return "live";
  return "other";
}

const KIND_TONE: Record<TradeWithRun["_run_kind"], "pos" | "accent" | "default"> = {
  canonical: "pos",
  paper: "accent",
  live: "pos",
  verification: "default",
  other: "default",
};

function isoDateOf(ts: string | null | undefined): string | null {
  if (!ts) return null;
  return ts.slice(0, 10);
}

export default function StrategyReplayPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const strategyId = Number.parseInt(id, 10);

  const [strategyState, setStrategyState] = useState<LoadState<Strategy>>({ kind: "loading" });
  const [runsState, setRunsState] = useState<LoadState<BacktestRun[]>>({ kind: "loading" });
  const [tradesState, setTradesState] = useState<LoadState<TradeWithRun[]>>({ kind: "loading" });

  // ------- Filters -------
  const [showVerification, setShowVerification] = useState(false);
  const [includeKinds, setIncludeKinds] = useState<Set<string>>(
    new Set(["canonical", "paper", "live"]),
  );
  // Calendar state
  const [monthDate, setMonthDate] = useState<Date>(() => {
    // Default to most recent month with a trade — set once data loads
    return new Date();
  });
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [showTable, setShowTable] = useState(false);

  // ------- Initial load -------
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
        else setStrategyState({ kind: "error", message: `${stratRes.status}` });
        if (runsRes.ok) setRunsState({ kind: "data", data: await runsRes.json() });
        else setRunsState({ kind: "error", message: `${runsRes.status}` });
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

  // Fetch all trades from all (filtered) runs once we know which runs apply
  useEffect(() => {
    if (strategyRuns.length === 0) return;
    let cancelled = false;
    const ctrl = new AbortController();
    setTradesState({ kind: "loading" });
    async function loadAll() {
      try {
        const out: TradeWithRun[] = [];
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
              out.push({
                ...t,
                _run_id: r.id,
                _run_name: r.name ?? `run ${r.id}`,
                _run_kind: kind,
              });
            }
          }),
        );
        if (!cancelled) setTradesState({ kind: "data", data: out });
      } catch (e) {
        if (!cancelled) {
          setTradesState({
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

  // ------- Filtered trades -------
  const allTrades = tradesState.kind === "data" ? tradesState.data : [];
  const trades = useMemo(() => {
    return allTrades.filter((t) => {
      if (!showVerification && t._run_kind === "verification") return false;
      return includeKinds.has(t._run_kind);
    });
  }, [allTrades, includeKinds, showVerification]);

  const calendarTrades: CalendarTrade[] = useMemo(
    () =>
      trades
        .map((t) => {
          const d = isoDateOf(t.entry_ts);
          if (!d) return null;
          return {
            date: d,
            side: t.side,
            realized_r: t.r_multiple,
            pnl: t.pnl,
            exit_reason: t.exit_reason,
          };
        })
        .filter((t): t is CalendarTrade => t !== null),
    [trades],
  );

  // Default the month to the most recent trade
  useEffect(() => {
    if (calendarTrades.length === 0) return;
    if (selectedDate !== null) return;
    const mostRecentIso = calendarTrades
      .map((t) => t.date)
      .sort()
      .at(-1);
    if (!mostRecentIso) return;
    const d = new Date(mostRecentIso);
    setMonthDate(new Date(d.getFullYear(), d.getMonth(), 1));
    setSelectedDate(mostRecentIso);
  }, [calendarTrades, selectedDate]);

  const dateRange = useMemo(() => {
    if (calendarTrades.length === 0) return null;
    const iso = calendarTrades.map((t) => t.date).sort();
    const min = new Date(iso[0]);
    const max = new Date(iso[iso.length - 1]);
    return {
      min: new Date(min.getFullYear(), min.getMonth(), 1),
      max: new Date(max.getFullYear(), max.getMonth(), 1),
    };
  }, [calendarTrades]);

  // Selected day's trades
  const dayTrades = useMemo(
    () => trades.filter((t) => isoDateOf(t.entry_ts) === selectedDate),
    [trades, selectedDate],
  );

  // Available kinds for filter chips
  const availableKinds = useMemo(() => {
    const set = new Set<string>();
    for (const t of allTrades) set.add(t._run_kind);
    return Array.from(set);
  }, [allTrades]);

  // Prev/next day with trades
  const sortedDates = useMemo(() => {
    const set = new Set(calendarTrades.map((t) => t.date));
    return Array.from(set).sort();
  }, [calendarTrades]);

  function prevTradingDay() {
    if (selectedDate === null || sortedDates.length === 0) return;
    const idx = sortedDates.indexOf(selectedDate);
    const target = idx <= 0 ? sortedDates[0] : sortedDates[idx - 1];
    setSelectedDate(target);
    const d = new Date(target);
    setMonthDate(new Date(d.getFullYear(), d.getMonth(), 1));
  }
  function nextTradingDay() {
    if (selectedDate === null || sortedDates.length === 0) return;
    const idx = sortedDates.indexOf(selectedDate);
    const target = idx === -1 || idx >= sortedDates.length - 1
      ? sortedDates[sortedDates.length - 1]
      : sortedDates[idx + 1];
    setSelectedDate(target);
    const d = new Date(target);
    setMonthDate(new Date(d.getFullYear(), d.getMonth(), 1));
  }

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={`STRATEGY ${strategyId} · REPLAY`}
        title={strategy ? `${strategy.name} — Replay` : "Replay"}
        sub="Browse this strategy's trades by date. Click a day to see the trade and replay the bars."
      />

      {/* Run/kind filter chips */}
      {availableKinds.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
            include:
          </span>
          {availableKinds.map((k) => {
            if (k === "verification" && !showVerification) return null;
            const active = includeKinds.has(k);
            return (
              <button
                key={k}
                type="button"
                onClick={() => {
                  setIncludeKinds((prev) => {
                    const next = new Set(prev);
                    if (next.has(k)) next.delete(k);
                    else next.add(k);
                    return next;
                  });
                }}
                className={cn(
                  "rounded border px-2.5 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.06em] transition-colors",
                  active
                    ? "border-accent-line bg-accent-soft text-accent"
                    : "border-line bg-bg-2 text-ink-3 hover:border-line-3",
                )}
              >
                {k}
              </button>
            );
          })}
          <span className="ml-auto font-mono text-[10px] text-ink-4">
            {trades.length} trade{trades.length === 1 ? "" : "s"} ·{" "}
            {sortedDates.length} day{sortedDates.length === 1 ? "" : "s"} traded
          </span>
        </div>
      )}

      {tradesState.kind === "loading" && (
        <Card className="mt-4">
          <div className="px-4 py-6 text-[12.5px] text-ink-3">Loading trades…</div>
        </Card>
      )}

      {tradesState.kind === "data" && trades.length === 0 && (
        <Card className="mt-4">
          <div className="px-4 py-6 text-[12.5px] text-ink-3">
            No trades match the current filters.
          </div>
        </Card>
      )}

      {trades.length > 0 && (
        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_360px]">
          <TradeCalendar
            trades={calendarTrades}
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            monthDate={monthDate}
            onMonthChange={setMonthDate}
            minMonth={dateRange?.min}
            maxMonth={dateRange?.max}
          />

          <DayDetailPanel
            selectedDate={selectedDate}
            dayTrades={dayTrades}
            onPrev={prevTradingDay}
            onNext={nextTradingDay}
            hasPrev={
              selectedDate !== null && sortedDates.indexOf(selectedDate) > 0
            }
            hasNext={
              selectedDate !== null &&
              sortedDates.indexOf(selectedDate) >= 0 &&
              sortedDates.indexOf(selectedDate) < sortedDates.length - 1
            }
          />
        </div>
      )}

      {/* Optional table view (collapsed by default) */}
      {trades.length > 0 && (
        <details
          className="mt-6"
          open={showTable}
          onToggle={(e) => setShowTable((e.target as HTMLDetailsElement).open)}
        >
          <summary className="cursor-pointer font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3 hover:text-ink-1">
            ▸ Show all trades as table ({trades.length})
          </summary>
          <Card className="mt-3">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[12.5px]">
                <thead>
                  <tr className="border-b border-line text-left">
                    {["Date", "Side", "Entry", "Exit", "R", "PnL $", "Reason", "Run", ""].map(
                      (h) => (
                        <th
                          key={h || "_"}
                          className="px-3 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {[...trades]
                    .sort((a, b) => (b.entry_ts ?? "").localeCompare(a.entry_ts ?? ""))
                    .slice(0, 500)
                    .map((t, i, arr) => (
                      <tr
                        key={`${t._run_id}-${t.id}`}
                        className={cn(
                          "hover:bg-bg-2",
                          i !== arr.length - 1 && "border-b border-line",
                        )}
                      >
                        <td className="px-3 py-2 font-mono text-[10.5px] text-ink-2">
                          {fmtDate(t.entry_ts ?? "")}
                        </td>
                        <td className="px-3 py-2 font-mono text-[11px] text-ink-1">
                          {t.side}
                        </td>
                        <td className="px-3 py-2 font-mono text-[11px] tabular-nums text-ink-1">
                          {t.entry_price?.toFixed(2) ?? "—"}
                        </td>
                        <td className="px-3 py-2 font-mono text-[11px] tabular-nums text-ink-1">
                          {t.exit_price?.toFixed(2) ?? "—"}
                        </td>
                        <td
                          className={cn(
                            "px-3 py-2 font-mono text-[11px] font-semibold tabular-nums",
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
                            : `${t.r_multiple >= 0 ? "+" : ""}${t.r_multiple.toFixed(2)}`}
                        </td>
                        <td
                          className={cn(
                            "px-3 py-2 font-mono text-[11px] tabular-nums",
                            t.pnl == null
                              ? "text-ink-3"
                              : t.pnl > 0
                                ? "text-pos"
                                : t.pnl < 0
                                  ? "text-neg"
                                  : "text-ink-2",
                          )}
                        >
                          {t.pnl == null
                            ? "—"
                            : `${t.pnl >= 0 ? "+" : ""}$${t.pnl.toFixed(0)}`}
                        </td>
                        <td className="px-3 py-2 font-mono text-[10.5px] text-ink-3">
                          {t.exit_reason ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <Chip tone={KIND_TONE[t._run_kind]}>{t._run_kind}</Chip>
                        </td>
                        <td className="px-3 py-2 text-right">
                          <button
                            type="button"
                            onClick={() => {
                              const d = isoDateOf(t.entry_ts);
                              if (d) {
                                setSelectedDate(d);
                                const dt = new Date(d);
                                setMonthDate(new Date(dt.getFullYear(), dt.getMonth(), 1));
                                window.scrollTo({ top: 0, behavior: "smooth" });
                              }
                            }}
                            className="font-mono text-[10.5px] text-accent hover:underline"
                          >
                            view →
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </Card>
        </details>
      )}

      {/* Verification toggle pinned at bottom for power users */}
      <label className="mt-6 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
        <input
          type="checkbox"
          checked={showVerification}
          onChange={(e) => {
            setShowVerification(e.target.checked);
            setIncludeKinds((prev) => {
              const next = new Set(prev);
              if (e.target.checked) next.add("verification");
              else next.delete("verification");
              return next;
            });
          }}
          className="h-3 w-3 accent-accent"
        />
        show verification (engine-replay) trades
      </label>
    </div>
  );
}

// ============================================================
// Day detail panel
// ============================================================

function DayDetailPanel({
  selectedDate,
  dayTrades,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
}: {
  selectedDate: string | null;
  dayTrades: TradeWithRun[];
  onPrev: () => void;
  onNext: () => void;
  hasPrev: boolean;
  hasNext: boolean;
}) {
  const dayLabel = useMemo(() => {
    if (!selectedDate) return "";
    const d = new Date(selectedDate);
    return d.toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }, [selectedDate]);

  if (!selectedDate) {
    return (
      <Card>
        <div className="px-4 py-6 text-[12.5px] text-ink-3">
          Click any day on the calendar to see its trade.
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <button
          type="button"
          onClick={onPrev}
          disabled={!hasPrev}
          className="inline-flex h-7 items-center gap-1 rounded border border-line bg-bg-2 px-2 font-mono text-[10px] uppercase tracking-[0.06em] text-ink-2 hover:border-line-3 hover:text-ink-0 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft size={12} />
          prev day
        </button>
        <span className="font-mono text-[11px] text-ink-1">{dayLabel}</span>
        <button
          type="button"
          onClick={onNext}
          disabled={!hasNext}
          className="inline-flex h-7 items-center gap-1 rounded border border-line bg-bg-2 px-2 font-mono text-[10px] uppercase tracking-[0.06em] text-ink-2 hover:border-line-3 hover:text-ink-0 disabled:cursor-not-allowed disabled:opacity-40"
        >
          next day
          <ChevronRight size={12} />
        </button>
      </div>

      {dayTrades.length === 0 ? (
        <div className="px-4 py-6 text-[12.5px] text-ink-3">
          No trade on this day.
        </div>
      ) : (
        <div className="grid gap-3 px-4 py-3">
          {dayTrades.map((t) => (
            <DayTradeBlock key={`${t._run_id}-${t.id}`} trade={t} />
          ))}
        </div>
      )}
    </Card>
  );
}

function DayTradeBlock({ trade: t }: { trade: TradeWithRun }) {
  const sideTone = t.side === "long" ? "text-pos" : "text-neg";
  const rTone =
    t.r_multiple == null
      ? "text-ink-3"
      : t.r_multiple > 0
        ? "text-pos"
        : t.r_multiple < 0
          ? "text-neg"
          : "text-ink-2";
  const pnlTone =
    t.pnl == null
      ? "text-ink-3"
      : t.pnl > 0
        ? "text-pos"
        : t.pnl < 0
          ? "text-neg"
          : "text-ink-2";

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={cn("font-mono text-[12px] font-semibold uppercase", sideTone)}>
            {t.side}
          </span>
          <Chip tone={KIND_TONE[t._run_kind]}>{t._run_kind}</Chip>
          <span className="font-mono text-[10px] text-ink-4">
            {t.exit_reason ?? "—"}
          </span>
        </div>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <Stat label="Entry" value={t.entry_price?.toFixed(2) ?? "—"} />
        <Stat label="Exit" value={t.exit_price?.toFixed(2) ?? "—"} />
        <Stat
          label="R"
          value={
            t.r_multiple == null
              ? "—"
              : `${t.r_multiple >= 0 ? "+" : ""}${t.r_multiple.toFixed(2)}`
          }
          tone={rTone}
        />
        <Stat
          label="PnL"
          value={
            t.pnl == null
              ? "—"
              : `${t.pnl >= 0 ? "+" : ""}$${t.pnl.toFixed(0)}`
          }
          tone={pnlTone}
        />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Link
          href={(() => {
            const d = isoDateOf(t.entry_ts);
            // Best path: the new per-day chart inside the strategy.
            // Falls back to the legacy /replay only if a date is missing.
            if (d) {
              // Use the strategy id from URL — encoded via Next dynamic params
              // upstream. We derive it from window.location to avoid prop-drilling
              // through three layers; it's safe in client-rendered components.
              const segs =
                typeof window !== "undefined"
                  ? window.location.pathname.split("/")
                  : [];
              const idx = segs.indexOf("strategies");
              const sid = idx >= 0 ? segs[idx + 1] : null;
              if (sid) return `/strategies/${sid}/replay/${d}`;
            }
            return `/replay?backtest_run_id=${t._run_id}&symbol=${encodeURIComponent("NQM6")}&date=${d ?? ""}`;
          })()}
          className="inline-flex h-7 items-center gap-1.5 rounded border border-accent-line bg-accent-soft px-2.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-accent hover:brightness-110"
        >
          Open chart replay
        </Link>
      </div>
      <div className="mt-2 font-mono text-[10px] text-ink-4">
        run: {t._run_name}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="rounded border border-line bg-bg-2 px-2 py-1.5">
      <div className="font-mono text-[9.5px] uppercase tracking-[0.08em] text-ink-4">
        {label}
      </div>
      <div className={cn("mt-0.5 font-mono text-[13px] font-semibold tabular-nums", tone ?? "text-ink-0")}>
        {value}
      </div>
    </div>
  );
}
