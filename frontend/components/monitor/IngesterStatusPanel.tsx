"use client";

import { AlertTriangle, FileX, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import MetricCard from "@/components/MetricCard";
import Panel from "@/components/Panel";
import StatusDot from "@/components/StatusDot";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type IngesterStatus = components["schemas"]["IngesterStatus"];

const POLL_INTERVAL_MS = 5_000;
const ENDPOINT = "/api/monitor/ingester";

type FetchState =
 | { kind: "loading" }
 | { kind: "missing" }
 | { kind: "error"; message: string }
 | { kind: "data"; data: IngesterStatus; fetchedAt: number };

export default function IngesterStatusPanel() {
 const [state, setState] = useState<FetchState>({ kind: "loading" });

 useEffect(() => {
 let cancelled = false;
 async function tick() {
 const next = await fetchIngester();
 if (!cancelled) setState(next);
 }
 tick();
 const id = setInterval(tick, POLL_INTERVAL_MS);
 return () => {
 cancelled = true;
 clearInterval(id);
 };
 }, []);

 return (
 <Panel
 title="Ingester (live data feed)"
 meta={metaLabel(state)}
 >
 <Body state={state} />
 </Panel>
 );
}

function Body({ state }: { state: FetchState }) {
 if (state.kind === "loading") {
 return (
 <div className="flex items-center gap-3 text-text-dim">
 <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} aria-hidden />
 <span className="tabular-nums text-xs ">
 Loading ingester status…
 </span>
 </div>
 );
 }
 if (state.kind === "missing") {
 return (
 <div className="flex flex-col gap-2">
 <div className="flex items-center gap-2 tabular-nums text-[11px] text-warn">
 <FileX className="h-4 w-4" strokeWidth={1.5} aria-hidden />
 <span>Ingester not running</span>
 </div>
 <p className="tabular-nums text-xs text-text-mute">
 No heartbeat file found. The 24/7 collection node either has the
 ingester stopped or hasn&apos;t reported in yet.
 </p>
 </div>
 );
 }
 if (state.kind === "error") {
 return (
 <div className="flex flex-col gap-2">
 <div className="flex items-center gap-2 tabular-nums text-[11px] text-neg">
 <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
 <span>Failed to read ingester status</span>
 </div>
 <p className="tabular-nums text-xs text-text">{state.message}</p>
 </div>
 );
 }

 const { data, fetchedAt } = state;
 const tone = data.status === "running" ? "live" : "off";
 const lastTickRel = data.last_tick_ts
 ? formatRelative(data.last_tick_ts, fetchedAt)
 : "—";

 return (
 <div className="flex flex-col gap-4">
 <div className="flex flex-wrap items-center gap-6">
 <div className="flex items-center gap-3">
 <StatusDot status={tone} pulse={tone === "live"} />
 <div>
 <p className="tabular-nums text-[10px] text-text-mute">
 Status
 </p>
 <p className="text-base font-medium text-text">
 {data.status}
 </p>
 </div>
 </div>
 <Stat label="Uptime" value={formatUptime(data.uptime_seconds)} />
 <Stat label="Reconnects" value={String(data.reconnect_count)} />
 <Stat label="Last tick" value={lastTickRel} />
 </div>

 <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
 <MetricCard
 label="Ticks (60s)"
 value={data.ticks_last_60s.toLocaleString()}
 valueTone="neutral"
 />
 <MetricCard
 label="Ticks total"
 value={data.ticks_received.toLocaleString()}
 valueTone="neutral"
 />
 <MetricCard
 label="Schema"
 value={data.schema}
 valueTone="neutral"
 />
 <MetricCard
 label="Symbols"
 value={String(data.symbols.length)}
 valueTone="neutral"
 />
 </div>

 <div className="flex flex-wrap gap-2">
 {data.symbols.map((sym) => (
 <span
 key={sym}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text-dim"
 >
 {sym}
 </span>
 ))}
 </div>

 <p className="tabular-nums text-[10px] text-text-mute">
 <span className="text-text-mute">Dataset · </span>
 {data.dataset} ({data.stype_in})
 </p>
 {data.current_file ? (
 <p className="tabular-nums text-[10px] text-text-mute break-all">
 <span className="text-text-mute">Current file · </span>
 {data.current_file}
 </p>
 ) : null}

 {data.last_error ? (
 <pre className="border border-neg/30 bg-neg/10 p-2 tabular-nums text-[11px] text-neg whitespace-pre-wrap break-words">
 {data.last_error}
 </pre>
 ) : null}
 </div>
 );
}

function Stat({ label, value }: { label: string; value: string }) {
 return (
 <div>
 <p className="tabular-nums text-[10px] text-text-mute">
 {label}
 </p>
 <p className="tabular-nums text-sm text-text">{value}</p>
 </div>
 );
}

function metaLabel(state: FetchState): string {
 if (state.kind === "loading") return "loading…";
 if (state.kind === "missing") return "offline · 5s";
 if (state.kind === "error") return "error · retry 5s";
 return state.data.status === "running"
 ? "live · polling 5s"
 : "errored · 5s";
}

function formatUptime(seconds: number): string {
 if (seconds < 60) return `${seconds}s`;
 if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
 if (seconds < 86400) {
 const h = Math.floor(seconds / 3600);
 const m = Math.floor((seconds % 3600) / 60);
 return `${h}h ${m}m`;
 }
 const d = Math.floor(seconds / 86400);
 const h = Math.floor((seconds % 86400) / 3600);
 return `${d}d ${h}h`;
}

function formatRelative(iso: string, now: number): string {
 const then = new Date(iso).getTime();
 if (Number.isNaN(then)) return iso;
 const diffMs = now - then;
 const absSec = Math.round(Math.abs(diffMs) / 1000);
 let rel: string;
 if (absSec < 60) rel = `${absSec}s`;
 else if (absSec < 3600) rel = `${Math.round(absSec / 60)}m`;
 else if (absSec < 86400) rel = `${Math.round(absSec / 3600)}h`;
 else rel = `${Math.round(absSec / 86400)}d`;
 return diffMs >= 0 ? `${rel} ago` : `${rel} ahead`;
}

async function fetchIngester(): Promise<FetchState> {
 try {
 const response = await fetch(ENDPOINT, { cache: "no-store" });
 if (response.status === 404) {
 return { kind: "missing" };
 }
 if (!response.ok) {
 return { kind: "error", message: await describe(response) };
 }
 const data = (await response.json()) as IngesterStatus;
 return { kind: "data", data, fetchedAt: Date.now() };
 } catch (err) {
 return {
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 };
 }
}

async function describe(response: Response): Promise<string> {
 try {
 const parsed = (await response.json()) as BackendErrorBody;
 if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
 return parsed.detail;
 }
 } catch {
 /* fall through */
 }
 return `${response.status} ${response.statusText || "Request failed"}`;
}
