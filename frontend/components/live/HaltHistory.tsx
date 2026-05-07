"use client";

import { useMemo } from "react";

import { Card, CardHead, Chip } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

import type { BotPayload } from "./LiveBotPanel";

type LiveHeartbeat = components["schemas"]["LiveHeartbeatRead"];

interface HaltEpisode {
  startedTs: string;
  endedTs: string | null; // null = still halted at end of window
  durationMin: number; // null treated as live -> compute against now
  reason: string;
}

/**
 * Compute halt episodes from a heartbeat window. An episode begins on
 * the first beat with `payload.halted === true` after a non-halted beat
 * (or at window start), and ends on the first non-halted beat after.
 *
 * Heartbeat history arrives newest-first from the API; we walk it in
 * chronological order so transitions read correctly.
 */
function computeHaltEpisodes(history: LiveHeartbeat[]): HaltEpisode[] {
  if (history.length === 0) return [];
  const ordered = [...history].reverse();
  const episodes: HaltEpisode[] = [];
  let active: { startedTs: string; reason: string } | null = null;

  for (const hb of ordered) {
    const p = (hb.payload ?? {}) as BotPayload;
    const isHalted = !!p.halted;
    if (isHalted && active === null) {
      active = {
        startedTs: hb.ts,
        reason: p.halt_reason ?? "(unspecified)",
      };
    } else if (!isHalted && active !== null) {
      const startMs = new Date(active.startedTs).getTime();
      const endMs = new Date(hb.ts).getTime();
      episodes.push({
        startedTs: active.startedTs,
        endedTs: hb.ts,
        durationMin: Math.max(0, (endMs - startMs) / 60_000),
        reason: active.reason,
      });
      active = null;
    } else if (isHalted && active !== null) {
      // Update reason if it changed mid-halt (rare but possible)
      const newReason = p.halt_reason ?? active.reason;
      active.reason = newReason;
    }
  }

  if (active !== null) {
    const startMs = new Date(active.startedTs).getTime();
    episodes.push({
      startedTs: active.startedTs,
      endedTs: null,
      durationMin: Math.max(0, (Date.now() - startMs) / 60_000),
      reason: active.reason,
    });
  }

  // Reverse so newest-first matches the rest of the page
  return episodes.reverse();
}

/**
 * Halt history + reason summary. Computes everything client-side from
 * the heartbeat window already fetched on /monitor — no new endpoints.
 *
 * Layout:
 *   - Card head with total halt count + "X reasons" chip count
 *   - Reason summary (counts per distinct halt_reason) when ≥1 episode
 *   - Episode timeline (newest-first table) with start, duration,
 *     end-or-"still halted", reason
 *   - Empty state when no halts in the window
 */
export function HaltHistory({ history }: { history: LiveHeartbeat[] }) {
  const episodes = useMemo(() => computeHaltEpisodes(history), [history]);
  const reasonCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const ep of episodes) m.set(ep.reason, (m.get(ep.reason) ?? 0) + 1);
    return Array.from(m.entries()).sort((a, b) => b[1] - a[1]);
  }, [episodes]);

  const oldestTs = history.length > 0 ? history[history.length - 1].ts : null;
  const stillHalted = episodes.some((ep) => ep.endedTs === null);

  return (
    <Card>
      <CardHead
        eyebrow="halt history"
        title={
          episodes.length === 0
            ? "0 halts in window"
            : `${episodes.length} halt${episodes.length === 1 ? "" : "s"} in window`
        }
        right={
          stillHalted ? (
            <Chip tone="neg">currently halted</Chip>
          ) : episodes.length > 0 ? (
            <Chip tone="warn">{reasonCounts.length} reason{reasonCounts.length === 1 ? "" : "s"}</Chip>
          ) : (
            <Chip tone="pos">clean</Chip>
          )
        }
      />

      {episodes.length === 0 ? (
        <div className="px-4 py-4 font-mono text-[11.5px] text-ink-3">
          {oldestTs
            ? `No halts since ${fmtDate(oldestTs)}.`
            : "No heartbeats yet."}
        </div>
      ) : (
        <>
          {/* Reason summary */}
          <div className="border-b border-line px-4 py-3">
            <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
              Reason breakdown
            </div>
            <ul className="mt-1.5 flex flex-wrap gap-2">
              {reasonCounts.map(([reason, count]) => (
                <li
                  key={reason}
                  className="rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[11px] text-ink-2"
                >
                  <span className="text-ink-1">{count}×</span>{" "}
                  <span className="text-neg/80">{reason}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Episode list */}
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["Started", "Duration", "Ended", "Reason"].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {episodes.map((ep, i) => (
                <tr
                  key={`${ep.startedTs}-${i}`}
                  className={cn(
                    "hover:bg-bg-2",
                    i !== episodes.length - 1 && "border-b border-line",
                  )}
                >
                  <td className="px-4 py-2 font-mono text-[11px] text-ink-2">
                    {fmtDate(ep.startedTs)}
                  </td>
                  <td className="px-4 py-2 font-mono text-[11px] tabular-nums text-ink-1">
                    {fmtDuration(ep.durationMin)}
                  </td>
                  <td className="px-4 py-2 font-mono text-[11px] text-ink-2">
                    {ep.endedTs ? (
                      fmtDate(ep.endedTs)
                    ) : (
                      <span className="text-neg">still halted</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-[11.5px] text-ink-2">
                    {ep.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Card>
  );
}

function fmtDuration(minutes: number): string {
  if (minutes < 1) return `${Math.round(minutes * 60)}s`;
  if (minutes < 60) return `${minutes.toFixed(1)}m`;
  return `${(minutes / 60).toFixed(1)}h`;
}
