"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];

interface NewStrategyButtonProps {
 stages: string[];
}

// Hand-listed plugin choices that match the engine resolver. When a
// new plugin lands in `app.services.strategy_registry.STRATEGY_DEFINITIONS`,
// add it here too. "composable" gets the visual feature builder on the
// /build sub-page; the others use the markdown rules editor.
const PLUGIN_OPTIONS: { value: string; label: string; hint: string }[] = [
 {
 value: "composable",
 label: "Composable (visual builder)",
 hint: "Stack pre-made features into a recipe. No Python.",
 },
 {
 value: "fractal_amd",
 label: "Fractal AMD",
 hint: "Trusted-style SMT + FVG setup with the live bot's gates.",
 },
 {
 value: "fractal_amd_trusted",
 label: "Fractal AMD (trusted port)",
 hint: "Byte-faithful port of the trusted multi-year backtest.",
 },
 {
 value: "moving_average_crossover",
 label: "Moving average crossover",
 hint: "Smoke-test plugin. Two MAs, fixed-tick stop / target.",
 },
];

type Phase =
 | { kind: "closed" }
 | { kind: "open" }
 | { kind: "saving" }
 | { kind: "error"; message: string };

export default function NewStrategyButton({ stages }: NewStrategyButtonProps) {
 const router = useRouter();
 const [phase, setPhase] = useState<Phase>({ kind: "closed" });
 const [name, setName] = useState("");
 const [slug, setSlug] = useState("");
 const [description, setDescription] = useState("");
 const [status, setStatus] = useState<string>(stages[0] ?? "idea");
 const [plugin, setPlugin] = useState<string>(PLUGIN_OPTIONS[0].value);

 function open() {
 setName("");
 setSlug("");
 setDescription("");
 setStatus(stages[0] ?? "idea");
 setPlugin(PLUGIN_OPTIONS[0].value);
 setPhase({ kind: "open" });
 }

 function close() {
 setPhase({ kind: "closed" });
 }

 async function submit(event: React.FormEvent<HTMLFormElement>) {
 event.preventDefault();
 if (name.trim() === "" || slug.trim() === "") return;
 setPhase({ kind: "saving" });
 try {
 const response = await fetch("/api/strategies", {
 method: "POST",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({
 name: name.trim(),
 slug: slug.trim().toLowerCase(),
 description: description.trim() || null,
 status,
 plugin,
 }),
 });
 if (!response.ok) {
 setPhase({ kind: "error", message: await describe(response) });
 return;
 }
 const created = (await response.json()) as Strategy;
 setPhase({ kind: "closed" });
 router.refresh();
 // Jump straight into the new strategy.
 router.push(`/strategies/${created.id}`);
 } catch (e) {
 setPhase({
 kind: "error",
 message: e instanceof Error ? e.message : "Network error",
 });
 }
 }

 if (phase.kind === "closed") {
 return (
 <button
 type="button"
 onClick={open}
 className="border border-pos/30 bg-pos/10 px-2.5 py-1 tabular-nums text-[10px] text-pos hover:bg-pos/10"
 >
 + new strategy
 </button>
 );
 }

 const saving = phase.kind === "saving";

 return (
 <form
 onSubmit={submit}
 className="flex flex-col gap-2 border border-border-strong bg-surface p-3"
 >
 <div className="flex gap-2">
 <label className="flex flex-1 flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Name
 <input
 type="text"
 value={name}
 onChange={(e) => {
 setName(e.target.value);
 if (slug === "") {
 setSlug(autoSlug(e.target.value));
 }
 }}
 placeholder="ORB Fade"
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-1 flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Slug
 <input
 type="text"
 value={slug}
 onChange={(e) => setSlug(e.target.value)}
 placeholder="orb-fade"
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Stage
 <select
 value={status}
 onChange={(e) => setStatus(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 >
 {stages.map((s) => (
 <option key={s} value={s}>
 {s}
 </option>
 ))}
 </select>
 </label>
 </div>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Engine plugin
 <select
 value={plugin}
 onChange={(e) => setPlugin(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 >
 {PLUGIN_OPTIONS.map((p) => (
 <option key={p.value} value={p.value}>
 {p.label}
 </option>
 ))}
 </select>
 <span className="tabular-nums text-[10px] text-text-mute">
 {PLUGIN_OPTIONS.find((p) => p.value === plugin)?.hint}
 </span>
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Description
 <textarea
 value={description}
 onChange={(e) => setDescription(e.target.value)}
 rows={3}
 placeholder="Optional — one-paragraph thesis."
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <div className="flex items-center gap-2">
 <button
 type="submit"
 disabled={saving || name.trim() === "" || slug.trim() === ""}
 className={cn(
 "border border-pos/30 bg-pos/10 px-2.5 py-1 tabular-nums text-[10px] ",
 saving || name.trim() === "" || slug.trim() === ""
 ? "cursor-not-allowed text-text-mute"
 : "text-pos hover:bg-pos/10",
 )}
 >
 {saving ? "saving…" : "create"}
 </button>
 <button
 type="button"
 onClick={close}
 disabled={saving}
 className="border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt disabled:opacity-50"
 >
 cancel
 </button>
 {phase.kind === "error" ? (
 <span className="tabular-nums text-[11px] text-neg">
 {phase.message}
 </span>
 ) : null}
 </div>
 </form>
 );
}

function autoSlug(name: string): string {
 return name
 .toLowerCase()
 .replace(/[^a-z0-9]+/g, "-")
 .replace(/^-+|-+$/g, "");
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
