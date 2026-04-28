"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import SystemInfoPanel from "@/components/settings/SystemInfoPanel";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Settings = components["schemas"]["SystemSettingsRead"];

const ENDPOINT = "/api/settings/system";

type FetchState =
 | { kind: "loading" }
 | { kind: "error"; message: string }
 | { kind: "data"; data: Settings };

export default function SettingsPage() {
 const [state, setState] = useState<FetchState>({ kind: "loading" });

 useEffect(() => {
 let cancelled = false;
 (async () => {
 const next = await fetchSettings();
 if (!cancelled) setState(next);
 })();
 return () => {
 cancelled = true;
 };
 }, []);

 return (
 <div className="pb-10">
 <PageHeader
 title="Settings"
 description="System info + (later) editable preferences"
 meta="v1 · read-only"
 />
 <div className="flex flex-col gap-4 px-8 pb-6">
 <Body state={state} />
 <Panel title="Editable preferences" meta="coming later">
 <p className="m-0 text-[13px] text-text-mute">
 Theme, contract specs, session-hour overrides, keyboard
 shortcuts, and telemetry toggles will land in a follow-up
 PR with their own settings store. For now, anything you
 see above is read-only inspection of how the app is
 currently running.
 </p>
 </Panel>
 </div>
 </div>
 );
}

function Body({ state }: { state: FetchState }) {
 if (state.kind === "loading") {
 return (
 <div className="flex items-center gap-3 rounded-lg border border-border bg-surface p-4 text-text-dim">
 <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} aria-hidden />
 <span className="text-xs">Loading system info…</span>
 </div>
 );
 }
 if (state.kind === "error") {
 return (
 <div className="rounded-lg border border-neg/30 bg-neg/10 p-4">
 <div className="flex items-center gap-2 text-xs text-neg">
 <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
 <span>Failed to load settings</span>
 </div>
 <p className="m-0 mt-2 text-[13px] text-text">{state.message}</p>
 </div>
 );
 }
 return <SystemInfoPanel settings={state.data} />;
}

async function fetchSettings(): Promise<FetchState> {
 try {
 const response = await fetch(ENDPOINT, { cache: "no-store" });
 if (!response.ok) {
 return { kind: "error", message: await readDetail(response) };
 }
 const data = (await response.json()) as Settings;
 return { kind: "data", data };
 } catch (err) {
 return {
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 };
 }
}

async function readDetail(response: Response): Promise<string> {
 try {
 const body = (await response.json()) as BackendErrorBody;
 if (typeof body.detail === "string" && body.detail.length > 0) {
 return body.detail;
 }
 } catch {
 /* fall through */
 }
 return `${response.status} ${response.statusText || "Request failed"}`;
}
