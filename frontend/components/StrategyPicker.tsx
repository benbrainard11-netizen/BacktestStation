"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import Btn from "@/components/ui/Btn";
import Pill from "@/components/ui/Pill";
import { useCurrentStrategy } from "@/lib/hooks/useCurrentStrategy";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type Stages = components["schemas"]["StrategyStagesRead"];

const FALLBACK_STAGES = [
  "idea",
  "research",
  "building",
  "backtest_validated",
  "forward_test",
  "live",
  "retired",
  "archived",
];

interface StrategyPickerProps {
  open: boolean;
  onClose: () => void;
  /**
   * When true, the close affordance ("Cancel" + ESC + backdrop click) is
   * hidden — the user must pick or create. Used on the empty dashboard
   * state where there's nothing to fall back to.
   */
  forced?: boolean;
}

/**
 * Modal that lets the user pick or create the active strategy. Sets the
 * current strategy id on selection and closes itself.
 */
export default function StrategyPicker({
  open,
  onClose,
  forced,
}: StrategyPickerProps) {
  const { id: currentId, setId } = useCurrentStrategy();
  const [strategies, setStrategies] = useState<Strategy[] | null>(null);
  const [stages, setStages] = useState<string[]>(FALLBACK_STAGES);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  // Initial load: strategies + stages.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      setLoadError(null);
      try {
        const [s, st] = await Promise.all([
          fetch("/api/strategies", { cache: "no-store" }).then((r) => {
            if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
            return r.json() as Promise<Strategy[]>;
          }),
          fetch("/api/strategies/stages", { cache: "no-store" })
            .then((r) => (r.ok ? r.json() : { stages: FALLBACK_STAGES }))
            .catch(() => ({ stages: FALLBACK_STAGES })) as Promise<Stages>,
        ]);
        if (cancelled) return;
        setStrategies(s);
        setStages(st.stages ?? FALLBACK_STAGES);
        // If there are zero strategies, jump straight into the create form.
        if (s.length === 0) setShowCreate(true);
      } catch (e) {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : "Failed to load");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  // ESC + click-outside (only when not forced).
  useEffect(() => {
    if (!open || forced) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, forced, onClose]);

  const handleSelect = useCallback(
    (strategy: Strategy) => {
      setId(strategy.id);
      onClose();
    },
    [setId, onClose],
  );

  const handleCreated = useCallback(
    (strategy: Strategy) => {
      setStrategies((prev) => (prev ? [strategy, ...prev] : [strategy]));
      setId(strategy.id);
      onClose();
    },
    [setId, onClose],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={(e) => {
        if (forced) return;
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Select a strategy"
        className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl border border-border bg-surface"
      >
        <header className="flex items-baseline justify-between border-b border-border px-[18px] py-[14px]">
          <div>
            <h3 className="m-0 text-[15px] font-medium tracking-[-0.005em] text-text">
              {strategies && strategies.length === 0
                ? "Create your first strategy"
                : "Choose a strategy to work on"}
            </h3>
            <p className="m-0 mt-1 text-xs text-text-mute">
              {strategies && strategies.length === 0
                ? "A strategy is a thesis you'll iterate on with versions, runs, and notes."
                : "Pick one to focus the dashboard on it. You can switch any time from the top bar."}
            </p>
          </div>
          {!forced ? (
            <button
              type="button"
              onClick={onClose}
              className="text-xs text-text-mute hover:text-text"
              aria-label="Close"
            >
              ESC
            </button>
          ) : null}
        </header>

        <div className="flex-1 overflow-y-auto px-[18px] py-4">
          {loadError ? (
            <p className="text-[13px] text-neg">Failed to load — {loadError}</p>
          ) : null}

          {strategies === null && !loadError ? (
            <p className="text-[13px] text-text-dim">Loading…</p>
          ) : null}

          {strategies && strategies.length > 0 && !showCreate ? (
            <ul className="m-0 flex list-none flex-col gap-1 p-0">
              {strategies.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(s)}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2.5 text-left transition-colors",
                      s.id === currentId
                        ? "border-accent/40 bg-accent/[0.06]"
                        : "border-border bg-surface-alt hover:border-border-strong",
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="m-0 truncate text-[14px] text-text">
                        {s.name}
                      </p>
                      <p className="m-0 mt-0.5 truncate text-xs text-text-mute">
                        {s.slug} · {s.versions.length} version
                        {s.versions.length === 1 ? "" : "s"}
                      </p>
                    </div>
                    <Pill tone={stageTone(s.status)}>{s.status}</Pill>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          {showCreate ? (
            <CreateStrategyForm
              stages={stages}
              onCreated={handleCreated}
              onCancel={
                strategies && strategies.length > 0
                  ? () => setShowCreate(false)
                  : undefined
              }
            />
          ) : null}
        </div>

        {!showCreate && strategies && strategies.length > 0 ? (
          <footer className="flex items-center justify-between border-t border-border px-[18px] py-[12px]">
            <span className="text-xs text-text-mute">
              {strategies.length} strateg
              {strategies.length === 1 ? "y" : "ies"}
            </span>
            <Btn variant="primary" onClick={() => setShowCreate(true)}>
              + New strategy
            </Btn>
          </footer>
        ) : null}
      </div>
    </div>
  );
}

function CreateStrategyForm({
  stages,
  onCreated,
  onCancel,
}: {
  stages: string[];
  onCreated: (s: Strategy) => void;
  onCancel?: () => void;
}) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState(stages[0] ?? "idea");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (name.trim() === "" || slug.trim() === "") return;
    setSubmitting(true);
    setError(null);
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
        const detail = await response
          .json()
          .then(
            (b: { detail?: string }) =>
              b.detail ?? `${response.status} ${response.statusText}`,
          )
          .catch(() => `${response.status} ${response.statusText}`);
        setError(detail);
        return;
      }
      const created = (await response.json()) as Strategy;
      onCreated(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-xs text-text-mute">
          Name
          <input
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (slug === "") setSlug(autoSlug(e.target.value));
            }}
            placeholder="ORB Fade"
            className="rounded-md border border-border bg-surface-alt px-2.5 py-1.5 text-[13px] text-text outline-none placeholder:text-text-mute focus:border-border-strong"
            autoFocus
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-mute">
          Slug
          <input
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="orb-fade"
            className="rounded-md border border-border bg-surface-alt px-2.5 py-1.5 text-[13px] text-text outline-none placeholder:text-text-mute focus:border-border-strong"
          />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs text-text-mute">
        Stage
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-md border border-border bg-surface-alt px-2.5 py-1.5 text-[13px] text-text outline-none focus:border-border-strong"
        >
          {stages.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-text-mute">
        Description
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          placeholder="Optional — one-paragraph thesis."
          className="resize-y rounded-md border border-border bg-surface-alt px-2.5 py-1.5 text-[13px] text-text outline-none placeholder:text-text-mute focus:border-border-strong"
        />
      </label>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-neg">{error ?? " "}</span>
        <div className="flex items-center gap-2">
          {onCancel ? (
            <Btn type="button" onClick={onCancel} disabled={submitting}>
              Cancel
            </Btn>
          ) : null}
          <Btn
            type="submit"
            variant="primary"
            disabled={
              submitting || name.trim() === "" || slug.trim() === ""
            }
          >
            {submitting ? "Creating…" : "Create strategy"}
          </Btn>
        </div>
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

function stageTone(
  status: string,
): "pos" | "neg" | "warn" | "accent" | "neutral" {
  switch (status) {
    case "live":
    case "backtest_validated":
    case "forward_test":
      return "pos";
    case "research":
    case "building":
      return "warn";
    case "idea":
      return "accent";
    case "retired":
    case "archived":
      return "neutral";
    default:
      return "neutral";
  }
}
