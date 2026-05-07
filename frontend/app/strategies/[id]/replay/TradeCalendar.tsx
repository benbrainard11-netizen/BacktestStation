"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo } from "react";

import { cn } from "@/lib/utils";

export interface CalendarTrade {
  date: string; // YYYY-MM-DD
  side: string;
  realized_r: number | null | undefined;
  pnl: number | null | undefined;
  exit_reason: string | null | undefined;
}

/**
 * Month-grid trade calendar. Each day cell shows the trade's R value
 * color-coded (green win, red loss, grey no trade). Click a day to
 * select it (controlled by parent via `selectedDate`).
 */
export function TradeCalendar({
  trades,
  selectedDate,
  onSelectDate,
  monthDate,
  onMonthChange,
  minMonth,
  maxMonth,
}: {
  trades: CalendarTrade[];
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
  monthDate: Date;
  onMonthChange: (date: Date) => void;
  minMonth?: Date;
  maxMonth?: Date;
}) {
  // Index trades by date for fast lookup
  const tradesByDate = useMemo(() => {
    const map = new Map<string, CalendarTrade[]>();
    for (const t of trades) {
      const arr = map.get(t.date) ?? [];
      arr.push(t);
      map.set(t.date, arr);
    }
    return map;
  }, [trades]);

  const monthStart = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
  const monthEnd = new Date(
    monthDate.getFullYear(),
    monthDate.getMonth() + 1,
    0,
  );
  const startDayOfWeek = monthStart.getDay(); // 0 = Sun
  const daysInMonth = monthEnd.getDate();

  // Build the cells (35 or 42, sun-first)
  const cells: { date: Date | null; key: string }[] = [];
  for (let i = 0; i < startDayOfWeek; i++) {
    cells.push({ date: null, key: `pad-${i}` });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const date = new Date(monthDate.getFullYear(), monthDate.getMonth(), d);
    cells.push({ date, key: `d-${d}` });
  }
  while (cells.length % 7 !== 0) {
    cells.push({ date: null, key: `tail-${cells.length}` });
  }

  function isoDate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  function navMonth(delta: number) {
    const next = new Date(monthDate.getFullYear(), monthDate.getMonth() + delta, 1);
    onMonthChange(next);
  }

  // Month-level summary for the header
  const monthIsoPrefix = isoDate(monthStart).slice(0, 7);
  const monthTrades = trades.filter((t) => t.date.startsWith(monthIsoPrefix));
  const monthWins = monthTrades.filter((t) => (t.realized_r ?? 0) > 0).length;
  const monthLosses = monthTrades.filter((t) => (t.realized_r ?? 0) < 0).length;
  const monthR = monthTrades.reduce((a, b) => a + (b.realized_r ?? 0), 0);
  const monthPnl = monthTrades.reduce((a, b) => a + (b.pnl ?? 0), 0);

  const monthLabel = monthStart.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
  const today = new Date();
  const todayIso = isoDate(today);
  const canPrev = !minMonth || monthStart > minMonth;
  const canNext = !maxMonth || monthStart < maxMonth;

  return (
    <div className="rounded-lg border border-line bg-bg-1">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navMonth(-1)}
            disabled={!canPrev}
            className="inline-flex h-7 w-7 items-center justify-center rounded border border-line bg-bg-2 text-ink-2 transition-colors hover:border-line-3 hover:text-ink-0 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Previous month"
          >
            <ChevronLeft size={14} />
          </button>
          <span className="font-mono text-[12.5px] font-semibold uppercase tracking-[0.06em] text-ink-0">
            {monthLabel}
          </span>
          <button
            type="button"
            onClick={() => navMonth(1)}
            disabled={!canNext}
            className="inline-flex h-7 w-7 items-center justify-center rounded border border-line bg-bg-2 text-ink-2 transition-colors hover:border-line-3 hover:text-ink-0 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Next month"
          >
            <ChevronRight size={14} />
          </button>
        </div>
        <div className="flex flex-wrap items-baseline gap-3 font-mono text-[10.5px] text-ink-3">
          <span>
            {monthTrades.length} trade{monthTrades.length === 1 ? "" : "s"}
          </span>
          {monthTrades.length > 0 && (
            <>
              <span>
                <span className="text-pos">{monthWins}W</span> /{" "}
                <span className="text-neg">{monthLosses}L</span>
              </span>
              <span
                className={cn(
                  "tabular-nums",
                  monthR > 0
                    ? "text-pos"
                    : monthR < 0
                      ? "text-neg"
                      : "text-ink-2",
                )}
              >
                {monthR >= 0 ? "+" : ""}
                {monthR.toFixed(2)}R
              </span>
              {monthPnl !== 0 && (
                <span
                  className={cn(
                    "tabular-nums",
                    monthPnl > 0
                      ? "text-pos"
                      : monthPnl < 0
                        ? "text-neg"
                        : "text-ink-2",
                  )}
                >
                  {monthPnl >= 0 ? "+" : ""}${monthPnl.toFixed(0)}
                </span>
              )}
            </>
          )}
        </div>
      </div>

      {/* Day-of-week headers */}
      <div className="grid grid-cols-7 border-b border-line bg-bg-2">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div
            key={d}
            className="px-2 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-4"
          >
            {d}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7">
        {cells.map(({ date, key }) => {
          if (!date) {
            return <div key={key} className="h-20 border-b border-r border-line bg-bg-1" />;
          }
          const iso = isoDate(date);
          const dayTrades = tradesByDate.get(iso) ?? [];
          const isToday = iso === todayIso;
          const isSelected = iso === selectedDate;
          const isWeekend = date.getDay() === 0 || date.getDay() === 6;
          const r = dayTrades.reduce((a, b) => a + (b.realized_r ?? 0), 0);
          const hasTrades = dayTrades.length > 0;
          const allWin = hasTrades && dayTrades.every((t) => (t.realized_r ?? 0) > 0);
          const allLoss = hasTrades && dayTrades.every((t) => (t.realized_r ?? 0) < 0);
          return (
            <button
              key={key}
              type="button"
              onClick={() => onSelectDate(iso)}
              className={cn(
                "relative flex h-20 flex-col items-stretch justify-between border-b border-r border-line px-2 py-1.5 text-left transition-colors",
                "hover:border-line-3 hover:bg-bg-2",
                isSelected && "bg-accent-soft border-accent-line",
                !hasTrades && isWeekend && "bg-bg-1/60",
              )}
            >
              <div className="flex items-center justify-between">
                <span
                  className={cn(
                    "text-[11.5px] font-medium tabular-nums",
                    isToday
                      ? "rounded bg-accent px-1 text-bg-0"
                      : hasTrades
                        ? "text-ink-1"
                        : "text-ink-4",
                  )}
                >
                  {date.getDate()}
                </span>
                {hasTrades && (
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      allWin ? "bg-pos" : allLoss ? "bg-neg" : "bg-warn",
                    )}
                  />
                )}
              </div>
              {hasTrades && (
                <div className="flex flex-col gap-0.5">
                  <div
                    className={cn(
                      "font-mono text-[11px] font-semibold tabular-nums",
                      r > 0 ? "text-pos" : r < 0 ? "text-neg" : "text-ink-2",
                    )}
                  >
                    {r >= 0 ? "+" : ""}
                    {r.toFixed(2)}R
                  </div>
                  {dayTrades.length > 1 && (
                    <div className="font-mono text-[9px] text-ink-3">
                      {dayTrades.length} trades
                    </div>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
