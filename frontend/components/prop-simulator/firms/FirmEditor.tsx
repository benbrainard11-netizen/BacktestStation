"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type ProfileRead = components["schemas"]["FirmRuleProfileRead"];

interface FirmEditorProps {
 initialProfile: ProfileRead;
}

type ActionState =
 | { kind: "idle" }
 | { kind: "saving" }
 | { kind: "verifying" }
 | { kind: "resetting" }
 | { kind: "archiving" }
 | { kind: "error"; message: string };

const TRAILING_OPTIONS: { value: string; label: string }[] = [
 { value: "intraday", label: "Intraday trailing" },
 { value: "end_of_day", label: "End-of-day trailing" },
 { value: "static", label: "Static (no trail)" },
 { value: "none", label: "None" },
];

const PHASE_OPTIONS: { value: string; label: string }[] = [
 { value: "evaluation", label: "Evaluation" },
 { value: "funded", label: "Funded" },
 { value: "payout", label: "Payout" },
];

const CONSISTENCY_OPTIONS: { value: string; label: string }[] = [
 { value: "none", label: "No consistency rule" },
 { value: "best_day_pct_of_total", label: "Best day · % of total" },
 { value: "min_trading_days", label: "Min trading days" },
 { value: "max_daily_swing", label: "Max daily swing %" },
];

export default function FirmEditor({ initialProfile }: FirmEditorProps) {
 const router = useRouter();
 const [profile, setProfile] = useState<ProfileRead>(initialProfile);
 const [action, setAction] = useState<ActionState>({ kind: "idle" });

 const dirty = useMemo(
 () => !shallowEqual(profile, initialProfile),
 [profile, initialProfile],
 );

 function set<K extends keyof ProfileRead>(key: K, value: ProfileRead[K]) {
 setProfile((p) => ({ ...p, [key]: value }));
 }

 async function handleSave() {
 setAction({ kind: "saving" });
 const updates = diff(initialProfile, profile);
 if (Object.keys(updates).length === 0) {
 setAction({ kind: "idle" });
 return;
 }
 try {
 const resp = await fetch(
 `/api/prop-firm/profiles/${encodeURIComponent(profile.profile_id)}`,
 {
 method: "PATCH",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify(updates),
 },
 );
 if (!resp.ok) {
 setAction({ kind: "error", message: await describe(resp) });
 return;
 }
 const updated = (await resp.json()) as ProfileRead;
 setProfile(updated);
 setAction({ kind: "idle" });
 router.refresh();
 } catch (e) {
 setAction({
 kind: "error",
 message: e instanceof Error ? e.message : "Network error",
 });
 }
 }

 async function handleMarkVerified() {
 setAction({ kind: "verifying" });
 try {
 const resp = await fetch(
 `/api/prop-firm/profiles/${encodeURIComponent(profile.profile_id)}`,
 {
 method: "PATCH",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({
 verification_status: "verified",
 verified_by: "ben",
 }),
 },
 );
 if (!resp.ok) {
 setAction({ kind: "error", message: await describe(resp) });
 return;
 }
 const updated = (await resp.json()) as ProfileRead;
 setProfile(updated);
 setAction({ kind: "idle" });
 router.refresh();
 } catch (e) {
 setAction({
 kind: "error",
 message: e instanceof Error ? e.message : "Network error",
 });
 }
 }

 async function handleReset() {
 if (!confirm("Reset every field to the seed defaults?")) return;
 setAction({ kind: "resetting" });
 try {
 const resp = await fetch(
 `/api/prop-firm/profiles/${encodeURIComponent(profile.profile_id)}/reset`,
 { method: "POST" },
 );
 if (!resp.ok) {
 setAction({ kind: "error", message: await describe(resp) });
 return;
 }
 const updated = (await resp.json()) as ProfileRead;
 setProfile(updated);
 setAction({ kind: "idle" });
 router.refresh();
 } catch (e) {
 setAction({
 kind: "error",
 message: e instanceof Error ? e.message : "Network error",
 });
 }
 }

 function handleDiscard() {
 setProfile(initialProfile);
 setAction({ kind: "idle" });
 }

 const verifiedAt = profile.verified_at
 ? new Date(profile.verified_at).toISOString().slice(0, 10)
 : null;

 return (
 <div className="flex flex-col gap-4">
 <StatusHeader
 profile={profile}
 verifiedAt={verifiedAt}
 action={action}
 onMarkVerified={handleMarkVerified}
 onReset={handleReset}
 />

 <Panel title="Identity" meta="how the firm shows up everywhere">
 <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
 <TextInput label="Firm name" value={profile.firm_name} onChange={(v) => set("firm_name", v)} />
 <TextInput label="Account name" value={profile.account_name} onChange={(v) => set("account_name", v)} />
 <NumberInput label="Account size ($)" value={profile.account_size} step={1000} onChange={(v) => set("account_size", v)} />
 <SelectInput label="Phase" value={profile.phase_type} options={PHASE_OPTIONS} onChange={(v) => set("phase_type", v)} />
 </div>
 </Panel>

 <Panel title="Rules" meta="sim-relevant pass/fail logic">
 <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
 <NumberInput label="Profit target ($)" value={profile.profit_target} step={100} onChange={(v) => set("profit_target", v)} />
 <NumberInput label="Max drawdown ($)" value={profile.max_drawdown} step={100} onChange={(v) => set("max_drawdown", v)} />
 <NullableNumberInput label="Daily loss limit ($)" value={profile.daily_loss_limit} step={50} onChange={(v) => set("daily_loss_limit", v)} />
 <ToggleInput label="Trailing drawdown enabled" value={profile.trailing_drawdown_enabled} onChange={(v) => set("trailing_drawdown_enabled", v)} />
 <SelectInput label="Trailing type" value={profile.trailing_drawdown_type} options={TRAILING_OPTIONS} onChange={(v) => set("trailing_drawdown_type", v)} />
 <NullableNumberInput label="Min trading days" value={profile.minimum_trading_days} step={1} onChange={(v) => set("minimum_trading_days", v)} />
 <NullableNumberInput label="Max trades / day" value={profile.max_trades_per_day} step={1} onChange={(v) => set("max_trades_per_day", v)} />
 <SelectInput label="Consistency rule" value={profile.consistency_rule_type} options={CONSISTENCY_OPTIONS} onChange={(v) => set("consistency_rule_type", v)} />
 <NullableNumberInput label="Consistency value (0–1)" value={profile.consistency_pct} step={0.05} onChange={(v) => set("consistency_pct", v)} />
 </div>
 </Panel>

 <Panel title="Risk" meta="default per-trade risk for sims">
 <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
 <NumberInput label="Default risk per trade ($)" value={profile.risk_per_trade_dollars} step={25} onChange={(v) => set("risk_per_trade_dollars", v)} />
 </div>
 </Panel>

 <Panel title="Payout" meta="conditions to actually get paid">
 <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
 <NumberInput label="Payout split (0–1)" value={profile.payout_split} step={0.05} onChange={(v) => set("payout_split", v)} />
 <NullableNumberInput label="Min days for payout" value={profile.payout_min_days} step={1} onChange={(v) => set("payout_min_days", v)} />
 <NullableNumberInput label="Min profit per payout ($)" value={profile.payout_min_profit} step={100} onChange={(v) => set("payout_min_profit", v)} />
 </div>
 </Panel>

 <Panel title="Fees" meta="eval / activation / reset / monthly">
 <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
 <NumberInput label="Eval fee ($)" value={profile.eval_fee} step={5} onChange={(v) => set("eval_fee", v)} />
 <NumberInput label="Activation fee ($)" value={profile.activation_fee} step={5} onChange={(v) => set("activation_fee", v)} />
 <NumberInput label="Reset fee ($)" value={profile.reset_fee} step={5} onChange={(v) => set("reset_fee", v)} />
 <NumberInput label="Monthly fee ($)" value={profile.monthly_fee} step={5} onChange={(v) => set("monthly_fee", v)} />
 </div>
 </Panel>

 <Panel title="Provenance" meta="where these numbers came from">
 <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
 <TextInput label="Source URL" value={profile.source_url ?? ""} onChange={(v) => set("source_url", v.length === 0 ? null : v)} />
 <TextInput label="Last known at (yyyy-mm-dd)" value={profile.last_known_at ?? ""} onChange={(v) => set("last_known_at", v.length === 0 ? null : v)} />
 </div>
 <label className="mt-3 flex flex-col gap-1 text-xs">
 <span className="tabular-nums text-text-mute">Notes</span>
 <textarea
 value={profile.notes ?? ""}
 onChange={(e) => set("notes", e.target.value || null)}
 rows={4}
 className="resize-y rounded-md border border-border bg-surface px-2 py-1.5 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 placeholder="Anything worth remembering about this firm — payout history, oddities, recent rule changes."
 />
 </label>
 </Panel>

 <SaveBar
 dirty={dirty}
 action={action}
 onSave={handleSave}
 onDiscard={handleDiscard}
 />
 </div>
 );
}

function StatusHeader({
 profile,
 verifiedAt,
 action,
 onMarkVerified,
 onReset,
}: {
 profile: ProfileRead;
 verifiedAt: string | null;
 action: ActionState;
 onMarkVerified: () => void;
 onReset: () => void;
}) {
 const isVerified = profile.verification_status === "verified";
 const verifyTone = isVerified
 ? "border-pos/30 bg-pos/10 text-pos"
 : "border-warn/30 bg-warn/10 text-warn";
 return (
 <div className="flex flex-col gap-3 rounded-md border border-border bg-surface px-4 py-3 md:flex-row md:items-center md:justify-between">
 <div className="flex flex-wrap items-center gap-2">
 <span
 className={cn(
 "inline-flex items-center gap-1.5 rounded-full border px-2 py-[2px] text-xs",
 verifyTone,
 )}
 >
 <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
 {isVerified ? "verified" : profile.verification_status}
 </span>
 {verifiedAt ? (
 <span className="tabular-nums text-[10px] text-text-mute">
 stamped {verifiedAt}
 {profile.verified_by ? ` · by ${profile.verified_by}` : null}
 </span>
 ) : (
 <span className="tabular-nums text-[10px] text-text-mute">
 not stamped — verify against the firm site, then mark verified
 </span>
 )}
 </div>
 <div className="flex flex-wrap items-center gap-2">
 {profile.source_url ? (
 <a
 href={profile.source_url}
 target="_blank"
 rel="noopener noreferrer"
 className="rounded-md border border-border bg-surface px-3 py-1.5 tabular-nums text-[11px] text-text-dim hover:bg-surface-alt"
 >
 ↗ Open firm site
 </a>
 ) : null}
 {profile.is_seed ? (
 <button
 type="button"
 onClick={onReset}
 disabled={action.kind === "resetting"}
 className="rounded-md border border-border bg-surface px-3 py-1.5 tabular-nums text-[11px] text-text-dim hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-50"
 >
 ↺ Reset to seed
 </button>
 ) : null}
 <button
 type="button"
 onClick={onMarkVerified}
 disabled={action.kind === "verifying" || isVerified}
 className={cn(
 "rounded-md border px-3 py-1.5 tabular-nums text-[11px] transition-all duration-150",
 isVerified
 ? "cursor-not-allowed border-border bg-surface text-text-mute"
 : "border-pos/30 bg-pos/10 text-pos hover:bg-pos/10",
 )}
 >
 {action.kind === "verifying" ? "Stamping…" : "✓ Mark verified"}
 </button>
 </div>
 </div>
 );
}

function SaveBar({
 dirty,
 action,
 onSave,
 onDiscard,
}: {
 dirty: boolean;
 action: ActionState;
 onSave: () => void;
 onDiscard: () => void;
}) {
 return (
 <div className="sticky bottom-7 z-10 flex flex-col gap-2 rounded-md border border-border bg-surface px-4 py-3 backdrop-blur md:flex-row md:items-center md:justify-between">
 <div className="tabular-nums text-[10px] ">
 {action.kind === "error" ? (
 <span className="text-neg">{action.message}</span>
 ) : dirty ? (
 <span className="text-warn">Unsaved changes — verification will reset on save if rule fields changed.</span>
 ) : (
 <span className="text-text-mute">No unsaved changes.</span>
 )}
 </div>
 <div className="flex gap-2">
 <button
 type="button"
 onClick={onDiscard}
 disabled={!dirty || action.kind === "saving"}
 className="rounded-md border border-border bg-surface px-3 py-1.5 tabular-nums text-[11px] text-text-dim hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-50"
 >
 Discard
 </button>
 <button
 type="button"
 onClick={onSave}
 disabled={!dirty || action.kind === "saving"}
 className={cn(
 "rounded-md border px-3 py-1.5 tabular-nums text-[11px] transition-all duration-150",
 dirty
 ? "border-border-strong bg-surface-alt text-text hover:bg-surface-alt"
 : "cursor-not-allowed border-border bg-surface text-text-mute",
 )}
 >
 {action.kind === "saving" ? "Saving…" : "Save changes"}
 </button>
 </div>
 </div>
 );
}

// ---------------------------------------------------------------------------
// Inline form-field primitives
// ---------------------------------------------------------------------------

function TextInput({
 label,
 value,
 onChange,
}: {
 label: string;
 value: string;
 onChange: (v: string) => void;
}) {
 return (
 <label className="flex flex-col gap-1 text-xs">
 <span className="tabular-nums text-text-mute">{label}</span>
 <input
 type="text"
 value={value}
 onChange={(e) => onChange(e.target.value)}
 className="rounded-md border border-border bg-surface px-2 py-1.5 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 />
 </label>
 );
}

function NumberInput({
 label,
 value,
 step,
 onChange,
}: {
 label: string;
 value: number;
 step: number;
 onChange: (v: number) => void;
}) {
 return (
 <label className="flex flex-col gap-1 text-xs">
 <span className="tabular-nums text-text-mute">{label}</span>
 <input
 type="number"
 value={value}
 step={step}
 onChange={(e) => onChange(Number(e.target.value))}
 className="rounded-md border border-border bg-surface px-2 py-1.5 tabular-nums text-xs text-text tabular-nums focus:border-border focus:outline-none"
 />
 </label>
 );
}

function NullableNumberInput({
 label,
 value,
 step,
 onChange,
}: {
 label: string;
 value: number | null;
 step: number;
 onChange: (v: number | null) => void;
}) {
 return (
 <label className="flex flex-col gap-1 text-xs">
 <span className="tabular-nums text-text-mute">{label}</span>
 <input
 type="text"
 value={value === null ? "" : value.toString()}
 placeholder="off"
 inputMode="numeric"
 onChange={(e) => {
 const raw = e.target.value.trim();
 if (raw === "") {
 onChange(null);
 return;
 }
 const n = Number(raw);
 onChange(Number.isFinite(n) ? n : null);
 }}
 className="rounded-md border border-border bg-surface px-2 py-1.5 tabular-nums text-xs text-text tabular-nums focus:border-border focus:outline-none"
 />
 <span className="tabular-nums text-[10px] text-text-mute">empty = disabled · step {step}</span>
 </label>
 );
}

function ToggleInput({
 label,
 value,
 onChange,
}: {
 label: string;
 value: boolean;
 onChange: (v: boolean) => void;
}) {
 return (
 <div className="flex flex-col gap-1 text-xs">
 <span className="tabular-nums text-text-mute">{label}</span>
 <button
 type="button"
 onClick={() => onChange(!value)}
 className={cn(
 "rounded-md border px-2 py-1.5 text-left tabular-nums text-xs",
 value
 ? "border-pos/30 bg-pos/10 text-pos"
 : "border-border bg-surface text-text-dim hover:bg-surface-alt",
 )}
 >
 {value ? "on" : "off"}
 </button>
 </div>
 );
}

function SelectInput({
 label,
 value,
 options,
 onChange,
}: {
 label: string;
 value: string;
 options: { value: string; label: string }[];
 onChange: (v: string) => void;
}) {
 return (
 <label className="flex flex-col gap-1 text-xs">
 <span className="tabular-nums text-text-mute">{label}</span>
 <select
 value={value}
 onChange={(e) => onChange(e.target.value)}
 className="rounded-md border border-border bg-surface px-2 py-1.5 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 >
 {options.map((o) => (
 <option key={o.value} value={o.value}>
 {o.label}
 </option>
 ))}
 </select>
 </label>
 );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function shallowEqual(a: ProfileRead, b: ProfileRead): boolean {
 const ka = Object.keys(a) as (keyof ProfileRead)[];
 for (const k of ka) {
 if (a[k] !== b[k]) return false;
 }
 return true;
}

function diff(
 before: ProfileRead,
 after: ProfileRead,
): Partial<ProfileRead> {
 const result: Partial<ProfileRead> = {};
 const keys = Object.keys(after) as (keyof ProfileRead)[];
 for (const k of keys) {
 if (before[k] !== after[k]) {
 // Strip readonly/server-only fields the patch endpoint rejects.
 if (k === "id" || k === "profile_id" || k === "is_seed" || k === "is_archived" || k === "created_at" || k === "updated_at" || k === "verified_at") {
 continue;
 }
 // @ts-expect-error narrow union per key
 result[k] = after[k];
 }
 }
 return result;
}

async function describe(response: Response): Promise<string> {
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
