"use client";

import Link from "next/link";

import { Card, Chip } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type LiveSignal = components["schemas"]["LiveSignalRead"];
type LiveHeartbeat = components["schemas"]["LiveHeartbeatRead"];

export type LoadState<T> =
  | { kind: "loading" }
  | { kind: "data"; data: T }
  | { kind: "error"; message: string };

/**
 * Loose typing for the runner's heartbeat payload — runner can evolve
 * the schema without forcing a frontend redeploy. Missing fields render
 * as "—". Position fields are only populated when open_position=true.
 */
export interface BotPayload {
  // Account state (TPT funded)
  balance?: number;
  peak_balance?: number;
  trail_floor?: number;
  locked?: boolean;
  total_withdrawn?: number;
  profit?: number;
  buffer_to_trail?: number;
  // Today's session counters
  trades_today?: number;
  wins_today?: number;
  losses_today?: number;
  consec_losses?: number;
  pnl_today?: number;
  // Halt / kill switches
  halted?: boolean;
  halt_reason?: string | null;
  // Position descriptor
  instrument?: string;
  contracts?: number;
  open_position?: boolean;
  // Mode
  mode?: "PAPER" | "LIVE" | string;
  // Open-position detail (populated by runner only when open_position=true)
  position_side?: "long" | "short" | string;
  entry_price?: number;
  stop_price?: number;
  target_price?: number;
  position_pnl_dollars?: number;
  position_r?: number;
  position_mfe_r?: number;
  position_mae_r?: number;
  fill_state?: "pending" | "filled" | "closing" | string;
  entry_ts?: string;
}

interface Props {
  heartbeatState: LoadState<LiveHeartbeat | null>;
  signals: LiveSignal[];
  signalsLoading: boolean;
  /**
   * Recent heartbeat history for the equity sparkline. Optional — when
   * omitted the sparkline section is hidden. When provided, render a
   * mini balance-over-time line.
   */
  heartbeatHistory?: LiveHeartbeat[];
  /** When true, hide the "view all → /monitor" link (used on /monitor itself). */
  hideViewAll?: boolean;
  /** Show how many recent signals (default 4 for Overview, more for Monitor). */
  signalLimit?: number;
}

/**
 * Live bot status panel. Reads the latest heartbeat — shows mode,
 * running/halted/offline badge, account profit, today's P&L, open
 * position detail when active, and a small list of recent signals.
 *
 * `offline` (>5min stale): hides the misleading P&L numbers from a
 * past run and shows "not currently running" instead — important so
 * a backtest replay's profit never reads as your real account state.
 */
export function LiveBotPanel({
  heartbeatState,
  signals,
  signalsLoading,
  heartbeatHistory,
  hideViewAll,
  signalLimit = 4,
}: Props) {
  if (heartbeatState.kind === "loading") {
    return (
      <Card>
        <div className="px-4 py-6 text-[12.5px] text-ink-3">Loading bot status…</div>
      </Card>
    );
  }
  if (heartbeatState.kind === "error") {
    return (
      <Card className="border-neg-line bg-neg-soft">
        <div className="px-4 py-3 font-mono text-[12px] text-neg">
          Failed to load heartbeat: {heartbeatState.message}
        </div>
      </Card>
    );
  }
  if (heartbeatState.data === null) {
    return (
      <Card>
        <div className="px-4 py-6 text-[12.5px] text-ink-3">
          Bot has never reported in. Once{" "}
          <code className="font-mono text-ink-2">pre10_live_runner</code>
          {" "}starts on ben-247 with telemetry on, status + P&amp;L stream here.
        </div>
      </Card>
    );
  }

  const hb = heartbeatState.data;
  const p: BotPayload = (hb.payload ?? {}) as BotPayload;
  const ageSec = Math.max(0, (Date.now() - new Date(hb.ts).getTime()) / 1000);
  const isStale = ageSec > 300;
  const halted = !!p.halted;
  const mode = p.mode ?? "PAPER";

  const statusTone: "pos" | "neg" | "warn" | "default" = isStale
    ? "warn"
    : halted
      ? "neg"
      : "pos";
  const statusLabel = isStale ? "offline" : halted ? "halted" : "running";

  const profit = typeof p.profit === "number" ? p.profit : null;
  const pnlToday = typeof p.pnl_today === "number" ? p.pnl_today : null;

  return (
    <Card>
      {/* Header strip */}
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <Chip tone={mode === "LIVE" ? "pos" : "default"}>{mode}</Chip>
          <Chip tone={statusTone}>{statusLabel}</Chip>
          {!isStale && p.locked && <Chip tone="accent">locked</Chip>}
          {!isStale && halted && p.halt_reason && (
            <span className="font-mono text-[10.5px] text-neg">
              · {p.halt_reason}
            </span>
          )}
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
          last seen {fmtAge(ageSec)} ago
        </span>
      </div>

      {isStale ? (
        <div className="px-4 py-5">
          <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-3">
            Bot is not currently running
          </div>
          <div className="mt-1 text-[12.5px] text-ink-2">
            No live trades right now. The last heartbeat was at{" "}
            <span className="font-mono text-ink-1">{fmtDate(hb.ts)}</span> —
            once <code className="mx-1 font-mono text-ink-2">pre10_live_runner</code>
            starts a session, P&amp;L and trade activity will stream here.
          </div>
        </div>
      ) : (
        <>
          {/* Big P&L tiles */}
          <div className="grid grid-cols-2 gap-px bg-line">
            <div className="bg-bg-1 px-4 py-3">
              <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
                Account profit
              </div>
              <div
                className={cn(
                  "mt-1 font-mono text-[22px] font-semibold tabular-nums",
                  profit === null
                    ? "text-ink-3"
                    : profit > 0
                      ? "text-pos"
                      : profit < 0
                        ? "text-neg"
                        : "text-ink-1",
                )}
              >
                {profit === null
                  ? "—"
                  : `${profit >= 0 ? "+" : ""}$${profit.toFixed(0)}`}
              </div>
              <div className="mt-0.5 font-mono text-[10.5px] text-ink-4">
                balance {fmtUsd(p.balance)} · peak {fmtUsd(p.peak_balance)}
              </div>
            </div>
            <div className="bg-bg-1 px-4 py-3">
              <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
                Today
              </div>
              <div
                className={cn(
                  "mt-1 font-mono text-[22px] font-semibold tabular-nums",
                  pnlToday === null
                    ? "text-ink-3"
                    : pnlToday > 0
                      ? "text-pos"
                      : pnlToday < 0
                        ? "text-neg"
                        : "text-ink-1",
                )}
              >
                {pnlToday === null
                  ? "—"
                  : `${pnlToday >= 0 ? "+" : ""}$${pnlToday.toFixed(0)}`}
              </div>
              <div className="mt-0.5 font-mono text-[10.5px] text-ink-4">
                {p.trades_today ?? 0} trade
                {(p.trades_today ?? 0) === 1 ? "" : "s"} ·{" "}
                <span className="text-pos">{p.wins_today ?? 0}W</span> /{" "}
                <span className="text-neg">{p.losses_today ?? 0}L</span>
              </div>
            </div>
          </div>

          {/* Equity sparkline (when history is available + has variance) */}
          {heartbeatHistory && heartbeatHistory.length >= 4 && (
            <div className="border-t border-line bg-bg-1 px-4 py-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
                  Account balance · last {heartbeatHistory.length} heartbeats
                </span>
              </div>
              <EquitySparkline heartbeats={heartbeatHistory} />
            </div>
          )}

          {/* Open-position detail — only renders when there's a live position */}
          {p.open_position && <OpenPositionDetail payload={p} />}

          {/* Sub-stats grid */}
          <div className="grid grid-cols-3 gap-px bg-line">
            <BotStat
              label="Trail floor"
              value={fmtUsd(p.trail_floor)}
              sub={`${fmtUsd(p.buffer_to_trail)} buffer`}
            />
            <BotStat
              label="Withdrawn"
              value={fmtUsd(p.total_withdrawn)}
              sub={p.locked ? "lock active" : "pre-lock"}
            />
            <BotStat
              label="Position"
              value={
                p.open_position
                  ? `${p.contracts ?? "?"} ${p.instrument ?? ""}`.trim()
                  : "flat"
              }
              sub={`consec L: ${p.consec_losses ?? 0}`}
            />
          </div>
        </>
      )}

      {/* Recent signals */}
      <div className="border-t border-line">
        <div className="flex items-center justify-between px-4 pt-3 pb-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
            Recent signals
          </span>
          {!hideViewAll && signals.length > 0 && (
            <Link
              href="/monitor"
              className="font-mono text-[10px] uppercase tracking-[0.08em] text-accent hover:underline"
            >
              view all →
            </Link>
          )}
        </div>
        {signalsLoading ? (
          <div className="px-4 pb-3 text-[12px] text-ink-3">Loading…</div>
        ) : signals.length === 0 ? (
          <div className="px-4 pb-3 text-[12px] text-ink-3">
            No entries or exits yet.
          </div>
        ) : (
          <table className="w-full border-collapse text-[12px]">
            <tbody>
              {signals.slice(0, signalLimit).map((s, i) => (
                <tr
                  key={s.id}
                  className={cn(
                    "hover:bg-bg-2",
                    i !== Math.min(signals.length, signalLimit) - 1 &&
                      "border-b border-line",
                  )}
                >
                  <td className="px-4 py-2 font-mono text-[10.5px] text-ink-3">
                    {fmtDate(s.ts)}
                  </td>
                  <td className="px-2 py-2 font-mono text-[11px] text-ink-1">
                    {s.side}
                  </td>
                  <td className="px-2 py-2 font-mono text-[11px] tabular-nums text-ink-1">
                    {s.price.toFixed(2)}
                  </td>
                  <td className="px-2 py-2 text-[11.5px] text-ink-2">
                    {s.reason ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {s.executed ? (
                      <Chip tone="pos">live</Chip>
                    ) : (
                      <Chip tone="default">paper</Chip>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}

/**
 * Open position detail. Renders when payload.open_position is true and
 * the runner has filled in the position fields. Shows entry/stop/target,
 * live P&L in dollars and R, and MFE/MAE so far.
 */
function OpenPositionDetail({ payload }: { payload: BotPayload }) {
  const sideTone =
    payload.position_side === "long"
      ? "text-pos"
      : payload.position_side === "short"
        ? "text-neg"
        : "text-ink-1";
  const pnlR = payload.position_r;
  const pnlDollars = payload.position_pnl_dollars;
  return (
    <div className="border-t border-line bg-accent-soft/40 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
            Open position
          </span>
          <span className={cn("font-mono text-[12px] font-semibold", sideTone)}>
            {(payload.position_side ?? "?").toUpperCase()}
          </span>
          <span className="font-mono text-[11px] text-ink-2">
            {payload.contracts ?? "?"} {payload.instrument ?? ""}
          </span>
          {payload.fill_state && payload.fill_state !== "filled" && (
            <Chip tone="warn">{payload.fill_state}</Chip>
          )}
        </div>
        <div className="flex items-baseline gap-3 font-mono text-[11.5px]">
          {typeof pnlR === "number" && (
            <span
              className={cn(
                "tabular-nums",
                pnlR > 0 ? "text-pos" : pnlR < 0 ? "text-neg" : "text-ink-1",
              )}
            >
              {pnlR >= 0 ? "+" : ""}
              {pnlR.toFixed(2)}R
            </span>
          )}
          {typeof pnlDollars === "number" && (
            <span
              className={cn(
                "tabular-nums",
                pnlDollars > 0
                  ? "text-pos"
                  : pnlDollars < 0
                    ? "text-neg"
                    : "text-ink-1",
              )}
            >
              {pnlDollars >= 0 ? "+" : ""}${pnlDollars.toFixed(0)}
            </span>
          )}
        </div>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-[11px] text-ink-3 sm:grid-cols-4">
        <span>
          entry{" "}
          <span className="tabular-nums text-ink-1">
            {fmtPx(payload.entry_price)}
          </span>
        </span>
        <span>
          stop{" "}
          <span className="tabular-nums text-ink-1">
            {fmtPx(payload.stop_price)}
          </span>
        </span>
        {typeof payload.target_price === "number" && (
          <span>
            target{" "}
            <span className="tabular-nums text-ink-1">
              {fmtPx(payload.target_price)}
            </span>
          </span>
        )}
        {typeof payload.position_mfe_r === "number" && (
          <span>
            MFE{" "}
            <span className="tabular-nums text-pos">
              {payload.position_mfe_r.toFixed(2)}R
            </span>
          </span>
        )}
        {typeof payload.position_mae_r === "number" && (
          <span>
            MAE{" "}
            <span className="tabular-nums text-neg">
              {payload.position_mae_r.toFixed(2)}R
            </span>
          </span>
        )}
        {payload.entry_ts && (
          <span>
            opened{" "}
            <span className="text-ink-1">
              {fmtDate(payload.entry_ts)}
            </span>
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Mini SVG sparkline of account balance over the last N heartbeats.
 * Returns null if all values are flat (no point drawing a horizontal
 * line for an idle bot).
 */
function EquitySparkline({ heartbeats }: { heartbeats: LiveHeartbeat[] }) {
  // Heartbeats arrive newest-first from the API; reverse so x-axis is time.
  const series = [...heartbeats]
    .reverse()
    .map((h) => {
      const p = (h.payload ?? {}) as BotPayload;
      return typeof p.balance === "number" ? p.balance : null;
    })
    .filter((v): v is number => v !== null);

  if (series.length < 2) return null;
  const min = Math.min(...series);
  const max = Math.max(...series);
  if (max === min) {
    return (
      <div className="mt-1 font-mono text-[10.5px] text-ink-4">
        flat at ${min.toLocaleString(undefined, { maximumFractionDigits: 0 })}
      </div>
    );
  }

  const w = 600;
  const h = 60;
  const xs = series.map((_, i) => (i / (series.length - 1)) * w);
  const ys = series.map((v) => h - ((v - min) / (max - min)) * h);
  const path = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(" ");
  const last = series[series.length - 1];
  const first = series[0];
  const delta = last - first;

  return (
    <div className="mt-1">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="none"
        className="h-12 w-full"
      >
        <path
          d={path}
          fill="none"
          stroke={delta >= 0 ? "var(--pos)" : "var(--neg)"}
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="mt-0.5 flex items-center justify-between font-mono text-[10px] text-ink-4">
        <span>${first.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        <span
          className={cn(
            "tabular-nums",
            delta > 0 ? "text-pos" : delta < 0 ? "text-neg" : "text-ink-3",
          )}
        >
          {delta >= 0 ? "+" : ""}${delta.toFixed(0)}
        </span>
        <span>${last.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
      </div>
    </div>
  );
}

function BotStat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-bg-1 px-4 py-2.5">
      <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
        {label}
      </div>
      <div className="mt-0.5 font-mono text-[12.5px] tabular-nums text-ink-1">
        {value}
      </div>
      {sub && <div className="font-mono text-[10px] text-ink-4">{sub}</div>}
    </div>
  );
}

function fmtUsd(v: number | undefined | null): string {
  if (typeof v !== "number") return "—";
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtPx(v: number | undefined | null): string {
  if (typeof v !== "number") return "—";
  return v.toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

function fmtAge(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}
