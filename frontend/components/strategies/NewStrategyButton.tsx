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

  function open() {
    setName("");
    setSlug("");
    setDescription("");
    setStatus(stages[0] ?? "idea");
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
        className="border border-emerald-900 bg-emerald-950/40 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-emerald-300 hover:bg-emerald-950/60"
      >
        + new strategy
      </button>
    );
  }

  const saving = phase.kind === "saving";

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-2 border border-zinc-700 bg-zinc-950 p-3"
    >
      <div className="flex gap-2">
        <label className="flex flex-1 flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
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
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Slug
          <input
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="orb-fade"
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Stage
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 focus:border-zinc-600 focus:outline-none"
          >
            {stages.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Description
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          placeholder="Optional — one-paragraph thesis."
          className="resize-y border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
        />
      </label>
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={saving || name.trim() === "" || slug.trim() === ""}
          className={cn(
            "border border-emerald-900 bg-emerald-950/40 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest",
            saving || name.trim() === "" || slug.trim() === ""
              ? "cursor-not-allowed text-zinc-600"
              : "text-emerald-200 hover:bg-emerald-950/60",
          )}
        >
          {saving ? "saving…" : "create"}
        </button>
        <button
          type="button"
          onClick={close}
          disabled={saving}
          className="border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900 disabled:opacity-50"
        >
          cancel
        </button>
        {phase.kind === "error" ? (
          <span className="font-mono text-[11px] text-rose-400">
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
