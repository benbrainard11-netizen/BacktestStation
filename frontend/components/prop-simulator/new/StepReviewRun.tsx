"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { WorkflowState } from "./NewSimulationWorkflow";
import { MOCK_POOL_BACKTESTS, findMockFirm } from "@/lib/prop-simulator/mocks";
import { samplingModeLabel } from "@/lib/prop-simulator/format";
import type { BackendErrorBody } from "@/lib/api/client";
import type { FirmRuleProfile } from "@/lib/prop-simulator/types";

interface StepReviewRunProps {
 state: WorkflowState;
 firms?: FirmRuleProfile[];
}

type SubmitState =
 | { kind: "idle" }
 | { kind: "running" }
 | { kind: "error"; message: string };

function SummaryRow({ label, value }: { label: string; value: string }) {
 return (
 <div className="flex items-center justify-between border-b border-border py-1.5 last:border-b-0">
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span className="tabular-nums text-xs tabular-nums text-text">
 {value}
 </span>
 </div>
 );
}

export default function StepReviewRun({ state, firms }: StepReviewRunProps) {
 const router = useRouter();
 const [submitState, setSubmitState] = useState<SubmitState>({ kind: "idle" });

 const firm = state.firmProfileId
 ? (firms ?? []).find((f) => f.profile_id === state.firmProfileId) ??
 findMockFirm(state.firmProfileId)
 : null;
 const selectedBacktests = MOCK_POOL_BACKTESTS.filter((bt) =>
 state.selectedBacktestIds.includes(bt.backtest_id),
 );

 async function handleRun() {
 if (!state.firmProfileId) {
 setSubmitState({ kind: "error", message: "Pick a firm profile first." });
 return;
 }
 if (state.selectedBacktestIds.length === 0) {
 setSubmitState({ kind: "error", message: "Select at least one backtest." });
 return;
 }
 setSubmitState({ kind: "running" });
 const body = {
 name: `${firm?.firm_name ?? "Sim"} ${new Date().toISOString().slice(0, 16)}`,
 selected_backtest_ids: state.selectedBacktestIds,
 firm_profile_id: state.firmProfileId,
 account_size: firm?.account_size ?? 50_000,
 starting_balance: firm?.account_size ?? 50_000,
 phase_mode: state.phaseMode,
 sampling_mode: state.samplingMode,
 simulation_count: state.simulationCount,
 use_replacement: state.useReplacement,
 random_seed: state.randomSeed,
 risk_mode: state.riskMode,
 risk_per_trade: state.riskPerTrade,
 risk_sweep_values:
 state.riskMode === "risk_sweep" ? state.riskSweepValues : null,
 daily_trade_limit: state.rules.dailyTradeLimit,
 daily_loss_stop: state.rules.dailyLossStop,
 daily_profit_stop: state.rules.dailyProfitStop,
 walkaway_after_winner: state.rules.walkawayAfterWinner,
 reduce_risk_after_loss: state.rules.reduceRiskAfterLoss,
 max_losses_per_day: state.rules.maxLossesPerDay,
 copy_trade_accounts: 1,
 fees_enabled: state.rules.feesEnabled,
 payout_rules_enabled: state.rules.payoutRulesEnabled,
 notes: "",
 };
 try {
 const resp = await fetch("/api/prop-firm/simulations", {
 method: "POST",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify(body),
 });
 if (!resp.ok) {
 const message = await extractErrorMessage(resp);
 setSubmitState({ kind: "error", message });
 return;
 }
 const created = await resp.json();
 const simId = created?.config?.simulation_id;
 if (typeof simId === "string" || typeof simId === "number") {
 router.push(`/prop-simulator/runs/${simId}`);
 } else {
 router.push("/prop-simulator/runs");
 }
 } catch (err) {
 setSubmitState({
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 });
 }
 }
 const totalTrades = selectedBacktests.reduce((sum, bt) => sum + bt.trade_count, 0);
 const totalDays = selectedBacktests.reduce((sum, bt) => sum + bt.day_count, 0);

 const risk =
 state.riskMode === "risk_sweep"
 ? `sweep · ${state.riskSweepValues.join(", ")}`
 : `$${state.riskPerTrade} / trade`;

 return (
 <div className="flex flex-col gap-4">
 <p className="text-xs text-text-dim">
 Review the configuration below. The simulation engine is not yet wired —
 the Run button is intentionally disabled until the Monte Carlo backend
 lands.
 </p>

 <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
 <div className="border border-border bg-surface p-3">
 <p className="mb-2 tabular-nums text-[10px] text-text-mute">
 Inputs
 </p>
 <SummaryRow
 label="Backtests"
 value={`${selectedBacktests.length} · ${totalTrades.toLocaleString()} trades · ${totalDays} days`}
 />
 <SummaryRow
 label="Strategy pool"
 value={
 selectedBacktests
 .map((bt) => bt.strategy_name)
 .filter((v, i, a) => a.indexOf(v) === i)
 .join(", ") || "—"
 }
 />
 <SummaryRow
 label="Firm"
 value={firm ? `${firm.firm_name} · ${firm.account_name}` : "—"}
 />
 <SummaryRow
 label="Account size"
 value={firm ? `$${firm.account_size.toLocaleString()}` : "—"}
 />
 <SummaryRow label="Phase mode" value={state.phaseMode} />
 </div>

 <div className="border border-border bg-surface p-3">
 <p className="mb-2 tabular-nums text-[10px] text-text-mute">
 Simulation
 </p>
 <SummaryRow
 label="Sampling"
 value={samplingModeLabel(state.samplingMode)}
 />
 <SummaryRow
 label="Sequences"
 value={state.simulationCount.toLocaleString()}
 />
 <SummaryRow
 label="Replacement"
 value={state.useReplacement ? "with" : "without"}
 />
 <SummaryRow label="Random seed" value={String(state.randomSeed)} />
 <SummaryRow label="Risk" value={risk} />
 </div>

 <div className="border border-border bg-surface p-3 lg:col-span-2">
 <p className="mb-2 tabular-nums text-[10px] text-text-mute">
 Personal rules
 </p>
 <SummaryRow
 label="Daily loss stop"
 value={
 state.rules.dailyLossStop === null
 ? "—"
 : `$${state.rules.dailyLossStop}`
 }
 />
 <SummaryRow
 label="Daily profit stop"
 value={
 state.rules.dailyProfitStop === null
 ? "—"
 : `$${state.rules.dailyProfitStop}`
 }
 />
 <SummaryRow
 label="Daily trade limit"
 value={
 state.rules.dailyTradeLimit === null
 ? "—"
 : state.rules.dailyTradeLimit.toString()
 }
 />
 <SummaryRow
 label="Max losses / day"
 value={
 state.rules.maxLossesPerDay === null
 ? "—"
 : state.rules.maxLossesPerDay.toString()
 }
 />
 <SummaryRow
 label="Reduce risk after loss"
 value={state.rules.reduceRiskAfterLoss ? "on" : "off"}
 />
 <SummaryRow
 label="Walk away after winner"
 value={state.rules.walkawayAfterWinner ? "on" : "off"}
 />
 <SummaryRow
 label="Fees enabled"
 value={state.rules.feesEnabled ? "on" : "off"}
 />
 <SummaryRow
 label="Payout rules enabled"
 value={state.rules.payoutRulesEnabled ? "on" : "off"}
 />
 </div>
 </div>

 <div className="flex flex-col gap-2">
 <button
 type="button"
 onClick={handleRun}
 disabled={submitState.kind === "running"}
 className={
 submitState.kind === "running"
 ? "cursor-not-allowed border border-border bg-surface px-4 py-2 tabular-nums text-[11px] text-text-mute"
 : "border border-border-strong bg-surface-alt px-4 py-2 tabular-nums text-[11px] text-text hover:bg-surface-alt"
 }
 >
 {submitState.kind === "running"
 ? "Running…"
 : `Run ${state.simulationCount.toLocaleString()} simulations`}
 </button>
 {submitState.kind === "error" ? (
 <p className="tabular-nums text-[11px] text-neg">
 {submitState.message}
 </p>
 ) : null}
 {submitState.kind === "running" ? (
 <p className="tabular-nums text-[10px] text-text-mute">
 Bootstrapping {state.simulationCount.toLocaleString()} sequences,
 aggregating distributions, persisting run. Redirects on success.
 </p>
 ) : null}
 </div>
 </div>
 );
}

async function extractErrorMessage(response: Response): Promise<string> {
 try {
 const parsed = (await response.json()) as BackendErrorBody & {
 detail?: unknown;
 };
 if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
 return parsed.detail;
 }
 if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
 return parsed.detail
 .map((e: unknown) => {
 if (
 e &&
 typeof e === "object" &&
 "msg" in e &&
 typeof (e as { msg: unknown }).msg === "string"
 ) {
 return (e as { msg: string }).msg;
 }
 return JSON.stringify(e);
 })
 .join("; ");
 }
 } catch {
 // fall through
 }
 return `${response.status} ${response.statusText || "Request failed"}`;
}
