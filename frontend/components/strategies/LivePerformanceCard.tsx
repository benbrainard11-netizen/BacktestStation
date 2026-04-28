"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import Panel from "@/components/Panel";
import StatusDot, { type StatusTone } from "@/components/StatusDot";
import { cn } from "@/lib/utils";
import { formatSigned, formatUSD, toneFor } from "@/lib/format";
import type { components } from "@/lib/api/generated";

type LiveStatus = components["schemas"]["LiveMonitorStatus"];
type LiveSignal = components["schemas"]["LiveSignalRead"];

interface LivePerformanceCardProps {
 strategyId: number;
 strategyName: string;
 /** "live" or "forward_test" — used for tone/wording. */
 stage: string;
}

const POLL_LIVE_MS = 5_000;
const POLL_SIGNALS_MS = 30_000;

type LiveState =
 | { kind: "loading" }
 | { kind: "error"; message: string }
 | { kind: "data"; data: LiveStatus };

type SignalsState =
 | { kind: "loading" }
 | { kind: "error" }
 | { kind: "data"; signals: LiveSignal[] };

export default function LivePerformanceCard({
 strategyId,
 strategyName,
 stage,
}: LivePerformanceCardProps) {
 const [live, setLive] = useState<LiveState>({ kind: "loading" });
 const [signals, setSignals] = useState<SignalsState>({ kind: "loading" });

 const todayStartIso = useMemo(() => startOfTodayIso(), []);

 // /api/monitor/live is a singleton (single live strategy on benpc). We
 // surface its KPIs here on the strategy dossier; if the running strategy
 // is something else, the today_* fields aren't strictly THIS strategy's
 // — the per-strategy signal feed below is the ground truth for "this
 // strategy traded today."
 useEffect(() => {
 let cancelled = false;
 async function tick() {
 try {
 const resp = await fetch("/api/monitor/live", { cache: "no-store" });
 if (!resp.ok) {
 if (!cancelled)
 setLive({
 kind: "error",
 message: `${resp.status} ${resp.statusText}`,
 });
 return;
 }
 const data = (await resp.json()) as LiveStatus;
 if (!cancelled) setLive({ kind: "data", data });
 } catch (err) {
 if (!cancelled)
 setLive({
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 });
 }
 }
 void tick();
 const id = setInterval(tick, POLL_LIVE_MS);
 return () => {
 cancelled = true;
 clearInterval(id);
 };
 }, []);

 useEffect(() => {
 let cancelled = false;
 async function tick() {
 try {
 const url = `/api/monitor/signals?strategy_id=${strategyId}&since=${encodeURIComponent(todayStartIso)}&limit=20`;
 const resp = await fetch(url, { cache: "no-store" });
 if (!resp.ok) {
 if (!cancelled) setSignals({ kind: "error" });
 return;
 }
 const data = (await resp.json()) as LiveSignal[];
 if (!cancelled) setSignals({ kind: "data", signals: data });
 } catch {
 if (!cancelled) setSignals({ kind: "error" });
 }
 }
 void tick();
 const id = setInterval(tick, POLL_SIGNALS_MS);
 return () => {
 cancelled = true;
 clearInterval(id);
 };
 }, [strategyId, todayStartIso]);

 const stageLabel = stage === "live" ? "live" : "forward test";
 const stageTone: StatusTone = stage === "live" ? "live" : "warn";

 return (
 <Panel
 title={`Live performance · ${strategyName}`}
 meta={`${stageLabel} · polling 5s`}
 >
 <div className="flex flex-col gap-4">
 <div className="flex items-center gap-2">
 <StatusDot status={stageTone} pulse={stageTone === "live"} />
 <span className="tabular-nums text-[10px] text-text-mute">
 {stageLabel === "live"
 ? "this strategy is live on benpc"
 : "forward-testing — not committing real capital"}
 </span>
 </div>

 <KpiRow live={live} />

 <SignalsBlock signals={signals} />

 <div className="flex items-center justify-between border-t border-border pt-3">
 <span className="tabular-nums text-[10px] text-text-mute">
 Full live view + journal
 </span>
 <Link
 href="/monitor"
 className="rounded-md border border-border-strong bg-surface-alt px-3 py-1 tabular-nums text-[10px] text-text hover:bg-surface-alt"
 >
 Open monitor →
 </Link>
 </div>
 </div>
 </Panel>
 );
}

function KpiRow({ live }: { live: LiveState }) {
 if (live.kind === "loading") {
 return (
 <p className="tabular-nums text-xs text-text-mute">Loading live status…</p>
 );
 }
 if (live.kind === "error") {
 return (
 <p className="tabular-nums text-xs text-neg">
 Live status unavailable: {live.message}
 </p>
 );
 }
 if (!live.data.source_exists) {
 return (
 <p className="tabular-nums text-xs text-warn">
 live_status.json not found yet — bot may not have written a heartbeat.
 </p>
 );
 }
 const d = live.data;
 return (
 <dl className="grid grid-cols-3 gap-2">
 <Stat
 label="Today P&L"
 value={d.today_pnl !== null ? formatUSD(d.today_pnl) : "—"}
 tone={d.today_pnl !== null ? toneFor(d.today_pnl) : "neutral"}
 />
 <Stat
 label="Today R"
 value={d.today_r !== null ? formatSigned(d.today_r) : "—"}
 tone={d.today_r !== null ? toneFor(d.today_r) : "neutral"}
 />
 <Stat
 label="Trades today"
 value={d.trades_today !== null ? String(d.trades_today) : "—"}
 tone="neutral"
 />
 </dl>
 );
}

function Stat({
 label,
 value,
 tone,
}: {
 label: string;
 value: string;
 tone: "positive" | "negative" | "neutral";
}) {
 return (
 <div className="flex flex-col gap-1 rounded-md border border-border bg-surface px-3 py-2 ">
 <dt className="tabular-nums text-[10px] text-text-mute">
 {label}
 </dt>
 <dd
 className={cn(
 "tabular-nums text-base tabular-nums",
 tone === "positive" && "text-pos",
 tone === "negative" && "text-neg",
 tone === "neutral" && "text-text",
 )}
 >
 {value}
 </dd>
 </div>
 );
}

function SignalsBlock({ signals }: { signals: SignalsState }) {
 if (signals.kind === "loading") {
 return (
 <div>
 <h4 className="tabular-nums text-[10px] text-text-mute">
 Today&apos;s signals (this strategy)
 </h4>
 <p className="mt-1 tabular-nums text-xs text-text-mute">Loading…</p>
 </div>
 );
 }
 if (signals.kind === "error") {
 return (
 <div>
 <h4 className="tabular-nums text-[10px] text-text-mute">
 Today&apos;s signals (this strategy)
 </h4>
 <p className="mt-1 tabular-nums text-xs text-neg">
 Failed to load signals.
 </p>
 </div>
 );
 }
 const list = signals.signals;
 if (list.length === 0) {
 return (
 <div>
 <h4 className="tabular-nums text-[10px] text-text-mute">
 Today&apos;s signals (this strategy)
 </h4>
 <p className="mt-1 tabular-nums text-xs text-text-mute">
 No signals today for this strategy.
 </p>
 </div>
 );
 }
 return (
 <div className="flex flex-col gap-1.5">
 <h4 className="tabular-nums text-[10px] text-text-mute">
 Today&apos;s signals · {list.length}
 </h4>
 <ul className="flex flex-col gap-1">
 {list.slice(0, 6).map((s) => (
 <li
 key={s.id}
 className="flex items-baseline justify-between gap-3 border-b border-border py-1 last:border-b-0 tabular-nums text-xs"
 >
 <span className="flex items-center gap-2">
 <span className="text-text-mute tabular-nums">
 {clockOnly(s.ts)}
 </span>
 <span
 className={cn(
 "rounded-sm border px-1 py-0 text-[10px] ",
 s.side === "long"
 ? "border-pos/30 bg-pos/10 text-pos"
 : "border-neg/30 bg-neg/10 text-neg",
 )}
 >
 {s.side}
 </span>
 <span className="tabular-nums text-text">
 {s.price.toLocaleString("en-US", { maximumFractionDigits: 2 })}
 </span>
 {!s.executed ? (
 <span className="text-[10px] text-warn">
 skipped
 </span>
 ) : null}
 </span>
 {s.reason ? (
 <span className="truncate text-right text-text-dim">
 {s.reason}
 </span>
 ) : null}
 </li>
 ))}
 {list.length > 6 ? (
 <li className="tabular-nums text-[10px] text-text-mute">
 + {list.length - 6} more · open monitor for full feed
 </li>
 ) : null}
 </ul>
 </div>
 );
}

function startOfTodayIso(): string {
 const now = new Date();
 return new Date(
 now.getFullYear(),
 now.getMonth(),
 now.getDate(),
 0,
 0,
 0,
 0,
 ).toISOString();
}

function clockOnly(iso: string): string {
 const d = new Date(iso);
 if (Number.isNaN(d.getTime())) return iso;
 return d.toLocaleTimeString(undefined, {
 hour: "2-digit",
 minute: "2-digit",
 second: "2-digit",
 hour12: false,
 });
}
