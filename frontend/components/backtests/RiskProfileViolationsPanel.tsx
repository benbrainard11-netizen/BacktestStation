"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/generated";

type RiskProfile = components["schemas"]["RiskProfileRead"];
type RiskEvaluation = components["schemas"]["RiskEvaluationRead"];

interface RiskProfileViolationsPanelProps {
 runId: number;
}

type ProfileEvaluation = {
 profile: RiskProfile;
 evaluation: RiskEvaluation | null;
 error: string | null;
};

type FetchState =
 | { kind: "loading" }
 | { kind: "no_profiles" }
 | { kind: "error"; message: string }
 | { kind: "data"; rows: ProfileEvaluation[] };

export default function RiskProfileViolationsPanel({
 runId,
}: RiskProfileViolationsPanelProps) {
 const [state, setState] = useState<FetchState>({ kind: "loading" });

 useEffect(() => {
 let cancelled = false;
 (async () => {
 const next = await loadAll(runId);
 if (!cancelled) setState(next);
 })();
 return () => {
 cancelled = true;
 };
 }, [runId]);

 if (state.kind === "loading") {
 return (
 <div className="flex items-center gap-3 text-text-dim">
 <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} aria-hidden />
 <span className="tabular-nums text-xs ">
 Evaluating risk profiles…
 </span>
 </div>
 );
 }

 if (state.kind === "no_profiles") {
 return (
 <div className="flex flex-col gap-2">
 <p className="tabular-nums text-xs text-text-mute">
 No risk profiles defined yet.
 </p>
 <Link
 href="/risk-profiles"
 className="tabular-nums text-[11px] text-text-dim underline-offset-2 hover:underline"
 >
 Create one →
 </Link>
 </div>
 );
 }

 if (state.kind === "error") {
 return (
 <div className="flex flex-col gap-2">
 <div className="flex items-center gap-2 tabular-nums text-[11px] text-neg">
 <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
 <span>Failed to load risk profiles</span>
 </div>
 <p className="tabular-nums text-xs text-text">{state.message}</p>
 </div>
 );
 }

 return (
 <div className="flex flex-col gap-3">
 {state.rows.map((row) => (
 <ProfileRow key={row.profile.id} row={row} />
 ))}
 </div>
 );
}

function ProfileRow({ row }: { row: ProfileEvaluation }) {
 const [expanded, setExpanded] = useState(false);
 const { profile, evaluation, error } = row;

 if (error) {
 return (
 <div className="border border-neg/30 bg-neg/10 px-3 py-2.5">
 <div className="flex items-center justify-between gap-3">
 <span className="tabular-nums text-xs text-text">{profile.name}</span>
 <span className="tabular-nums text-[11px] text-neg">
 evaluation failed
 </span>
 </div>
 <p className="mt-1 tabular-nums text-[11px] text-neg">{error}</p>
 </div>
 );
 }

 if (!evaluation) return null;

 const violationCount = evaluation.violations.length;
 const clean = violationCount === 0;
 const tone = clean ? "border-pos/30" : "border-warn/30";

 return (
 <div className={`border ${tone} bg-surface px-3 py-2.5`}>
 <div className="flex items-center justify-between gap-3">
 <div className="flex items-center gap-2 min-w-0">
 {clean ? (
 <CheckCircle2
 className="h-4 w-4 shrink-0 text-pos"
 strokeWidth={1.5}
 aria-hidden
 />
 ) : (
 <AlertTriangle
 className="h-4 w-4 shrink-0 text-warn"
 strokeWidth={1.5}
 aria-hidden
 />
 )}
 <Link
 href={`/risk-profiles/${profile.id}`}
 className="truncate tabular-nums text-xs text-text hover:underline"
 >
 {profile.name}
 </Link>
 {profile.status !== "active" ? (
 <span className="border border-border bg-surface px-1.5 py-0.5 tabular-nums text-[9px] text-text-mute">
 {profile.status}
 </span>
 ) : null}
 </div>
 <div className="flex items-center gap-3">
 <span
 className={`tabular-nums text-[11px] ${
 clean ? "text-pos" : "text-warn"
 }`}
 >
 {clean
 ? "no violations"
 : `${violationCount} violation${violationCount === 1 ? "" : "s"}`}
 </span>
 <span className="tabular-nums text-[10px] text-text-mute">
 {evaluation.total_trades_evaluated} trades
 </span>
 {!clean ? (
 <button
 type="button"
 onClick={() => setExpanded((e) => !e)}
 className="border border-border bg-surface-alt px-2 py-0.5 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 {expanded ? "hide" : "show"}
 </button>
 ) : null}
 </div>
 </div>

 {expanded && !clean ? (
 <ul className="mt-2 flex flex-col gap-1.5 border-t border-border pt-2">
 {evaluation.violations.map((v, i) => (
 <li
 key={`${v.at_trade_id}-${v.kind}-${i}`}
 className="grid grid-cols-[auto_auto_1fr] gap-x-3 tabular-nums text-[11px]"
 >
 <span className="text-text-mute">#{v.at_trade_index + 1}</span>
 <span className="text-warn ">
 {v.kind}
 </span>
 <span className="text-text break-words">{v.message}</span>
 </li>
 ))}
 </ul>
 ) : null}
 </div>
 );
}

async function loadAll(runId: number): Promise<FetchState> {
 let profiles: RiskProfile[];
 try {
 const res = await fetch("/api/risk-profiles", { cache: "no-store" });
 if (!res.ok) {
 return {
 kind: "error",
 message: `${res.status} ${res.statusText || "Risk profile list failed"}`,
 };
 }
 profiles = (await res.json()) as RiskProfile[];
 } catch (err) {
 return {
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 };
 }

 if (profiles.length === 0) return { kind: "no_profiles" };

 const rows: ProfileEvaluation[] = await Promise.all(
 profiles.map(async (profile) => {
 try {
 const url = `/api/risk-profiles/${profile.id}/evaluate?run_id=${runId}`;
 const res = await fetch(url, { method: "POST", cache: "no-store" });
 if (!res.ok) {
 return {
 profile,
 evaluation: null,
 error: `${res.status} ${res.statusText || "evaluation failed"}`,
 };
 }
 const evaluation = (await res.json()) as RiskEvaluation;
 return { profile, evaluation, error: null };
 } catch (err) {
 return {
 profile,
 evaluation: null,
 error: err instanceof Error ? err.message : "Network error",
 };
 }
 }),
 );

 return { kind: "data", rows };
}
