"use client";

import { useEffect, useMemo, useState } from "react";

import PageHeader from "@/components/PageHeader";
import BarChart from "@/components/trade-replay/BarChart";
import TickChart from "@/components/trade-replay/TickChart";
import TradePicker from "@/components/trade-replay/TradePicker";
import type { components } from "@/lib/api/generated";
import { parseUtcLoose } from "@/lib/trade-replay/etFormat";
import type { Timeframe } from "@/lib/trade-replay/resampleBars";

type Run = components["schemas"]["TradeReplayRunRead"];
type Trade = components["schemas"]["TradeReplayTradeRead"];
type TickWindow = components["schemas"]["TradeReplayWindowRead"];
type ReplayPayload = components["schemas"]["ReplayPayload"];
type Anchor = components["schemas"]["TradeReplayAnchor"];

type Mode = "1s" | Timeframe;
const MODES: Mode[] = ["1s", "1m", "5m", "15m", "30m"];
const DEFAULT_MODE: Mode = "1m";

type RunsState =
 | { kind: "loading" }
 | { kind: "error"; message: string }
 | { kind: "data"; runs: Run[] };

type TickState =
 | { kind: "idle" }
 | { kind: "loading" }
 | { kind: "error"; message: string }
 | { kind: "data"; payload: TickWindow };

type BarsState =
 | { kind: "idle" }
 | { kind: "loading" }
 | { kind: "error"; message: string }
 | { kind: "data"; payload: ReplayPayload; anchor: Anchor };

export default function TradeReplayPage() {
 const [runs, setRuns] = useState<RunsState>({ kind: "loading" });
 const [selected, setSelected] = useState<{
 runId: number;
 tradeId: number;
 } | null>(null);
 const [mode, setMode] = useState<Mode>(DEFAULT_MODE);

 const [tickState, setTickState] = useState<TickState>({ kind: "idle" });
 const [barsState, setBarsState] = useState<BarsState>({ kind: "idle" });

 // Load all live runs once.
 useEffect(() => {
 let cancelled = false;
 (async () => {
 try {
 const res = await fetch("/api/trade-replay/runs", {
 cache: "no-store",
 });
 if (!res.ok) {
 if (!cancelled)
 setRuns({
 kind: "error",
 message: `${res.status} ${res.statusText}`,
 });
 return;
 }
 const data = (await res.json()) as Run[];
 if (!cancelled) setRuns({ kind: "data", runs: data });
 } catch (err) {
 if (!cancelled)
 setRuns({
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 });
 }
 })();
 return () => {
 cancelled = true;
 };
 }, []);

 const selectedTrade = useMemo<{
 run: Run;
 trade: Trade;
 } | null>(() => {
 if (selected === null || runs.kind !== "data") return null;
 const run = runs.runs.find((r) => r.run_id === selected.runId);
 if (!run) return null;
 const trade = run.trades.find((t) => t.trade_id === selected.tradeId);
 if (!trade) return null;
 return { run, trade };
 }, [selected, runs]);

 // Fetch ticks (1s mode).
 useEffect(() => {
 if (selected === null || mode !== "1s") {
 setTickState({ kind: "idle" });
 return;
 }
 let cancelled = false;
 setTickState({ kind: "loading" });
 (async () => {
 try {
 // 1s mode: ±15 min around entry. Cap is 30 min each side.
 const url = `/api/trade-replay/${selected.runId}/${selected.tradeId}/ticks?lead_seconds=900&trail_seconds=900`;
 const res = await fetch(url, { cache: "no-store" });
 if (!res.ok) {
 if (!cancelled)
 setTickState({
 kind: "error",
 message: `${res.status} ${res.statusText}`,
 });
 return;
 }
 const data = (await res.json()) as TickWindow;
 if (!cancelled) setTickState({ kind: "data", payload: data });
 } catch (err) {
 if (!cancelled)
 setTickState({
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 });
 }
 })();
 return () => {
 cancelled = true;
 };
 }, [selected, mode]);

 // Fetch bars (1m+ modes). One fetch per (symbol, date); resample
 // happens client-side in BarChart.
 useEffect(() => {
 if (selected === null || mode === "1s" || selectedTrade === null) {
 setBarsState({ kind: "idle" });
 return;
 }
 let cancelled = false;
 setBarsState({ kind: "loading" });
 const { run, trade } = selectedTrade;
 // Parse as UTC (entry_ts comes through tz-naive); local-time
 // parsing would shift the date for late-day trades.
 const date = parseUtcLoose(trade.entry_ts).toISOString().slice(0, 10);
 const url = `/api/replay/${encodeURIComponent(run.symbol)}/${date}?backtest_run_id=${run.run_id}`;
 (async () => {
 try {
 const res = await fetch(url, { cache: "no-store" });
 if (!res.ok) {
 if (!cancelled)
 setBarsState({
 kind: "error",
 message: `${res.status} ${res.statusText}`,
 });
 return;
 }
 const payload = (await res.json()) as ReplayPayload;
 const anchor: Anchor = {
 entry_ts: trade.entry_ts,
 exit_ts: trade.exit_ts,
 side: trade.side,
 entry_price: trade.entry_price,
 exit_price: trade.exit_price,
 stop_price: trade.stop_price,
 target_price: trade.target_price,
 r_multiple: trade.r_multiple,
 };
 if (!cancelled) setBarsState({ kind: "data", payload, anchor });
 } catch (err) {
 if (!cancelled)
 setBarsState({
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 });
 }
 })();
 return () => {
 cancelled = true;
 };
 }, [selected, mode, selectedTrade]);

 return (
 <div className="pb-10">
 <PageHeader
 title="Trade replay"
 description="Replay live trades for review and analysis. Times in ET. Pick a trade, scrub through the day at any timeframe."
 meta="research · review-only"
 />
 <div className="flex flex-col gap-4 px-8 pb-6">
 {runs.kind === "loading" ? (
 <div className="rounded-lg border border-border bg-surface p-4 text-xs text-text-mute">
 Loading live runs…
 </div>
 ) : runs.kind === "error" ? (
 <div className="rounded-lg border border-neg/30 bg-neg/10 p-4 text-xs text-neg">
 Failed to load runs: {runs.message}
 </div>
 ) : (
 <TradePicker
 runs={runs.runs}
 selected={selected}
 onSelect={setSelected}
 />
 )}

 {selected !== null ? (
 <TimeframePicker mode={mode} onChange={setMode} />
 ) : null}

 {selected === null ? (
 <div className="rounded-lg border border-border bg-surface p-6 text-xs text-text-mute">
 Pick a trade above to load its replay.
 </div>
 ) : mode === "1s" ? (
 <TickPanel state={tickState} />
 ) : (
 <BarsPanel state={barsState} timeframe={mode as Timeframe} />
 )}
 </div>
 </div>
 );
}

function TimeframePicker({
 mode,
 onChange,
}: {
 mode: Mode;
 onChange: (m: Mode) => void;
}) {
 return (
 <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface p-3 text-xs">
 <span className="text-text-mute">Timeframe</span>
 {MODES.map((m) => (
 <button
 key={m}
 type="button"
 onClick={() => onChange(m)}
 className={
 mode === m
 ? "rounded-md border border-text bg-text px-3 py-1 text-bg"
 : "rounded-md border border-border bg-surface px-3 py-1 text-text-dim hover:bg-surface-alt"
 }
 >
 {m}
 </button>
 ))}
 <span className="ml-3 text-text-mute">
 {mode === "1s"
 ? "Tick-level (TBBO) · ±15 min around entry"
 : "Full-day 1m bars resampled to selected timeframe"}
 </span>
 </div>
 );
}

function TickPanel({ state }: { state: TickState }) {
 if (state.kind === "loading")
 return (
 <div className="rounded-lg border border-border bg-surface p-4 text-xs text-text-mute">
 Loading TBBO window…
 </div>
 );
 if (state.kind === "error")
 return (
 <div className="rounded-lg border border-neg/30 bg-neg/10 p-4 text-xs text-neg">
 Failed to load ticks: {state.message}
 </div>
 );
 if (state.kind === "idle") return null;
 return <TickChart payload={state.payload} />;
}

function BarsPanel({
 state,
 timeframe,
}: {
 state: BarsState;
 timeframe: Timeframe;
}) {
 if (state.kind === "loading")
 return (
 <div className="rounded-lg border border-border bg-surface p-4 text-xs text-text-mute">
 Loading bars…
 </div>
 );
 if (state.kind === "error")
 return (
 <div className="rounded-lg border border-neg/30 bg-neg/10 p-4 text-xs text-neg">
 Failed to load bars: {state.message}
 </div>
 );
 if (state.kind === "idle") return null;
 const bars = state.payload.bars ?? [];
 if (bars.length === 0) {
 return (
 <div className="rounded-lg border border-border bg-surface p-6 text-xs text-text-mute">
 No 1m bars in the warehouse for this trade&apos;s date. The bars
 partition may not be backfilled yet.
 </div>
 );
 }
 return (
 <BarChart
 bars={bars}
 anchor={state.anchor}
 timeframe={timeframe}
 fvgZones={state.payload.fvg_zones ?? []}
 />
 );
}
