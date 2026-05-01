"use client";

import { BookPlus, Loader2, X } from "lucide-react";
import { useState } from "react";

import Btn from "@/components/ui/Btn";
import { type BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type ResearchEntry = components["schemas"]["ResearchEntryRead"];
type KnowledgeCard = components["schemas"]["KnowledgeCardRead"];
type PromotePayload = components["schemas"]["ResearchEntryPromoteRequest"];

// Hardcoded mirrors of backend/app/schemas/knowledge.py KNOWLEDGE_CARD_*.
// Kept inline to avoid a synchronous fetch on form mount; if the backend
// vocabulary changes, update this list and the test suite catches the
// drift via the typecheck on PromotePayload's `kind`/`status`.
const CARD_KINDS = [
  "market_concept",
  "orderflow_formula",
  "indicator_formula",
  "setup_archetype",
  "research_playbook",
  "risk_rule",
  "execution_concept",
] as const;

const CARD_STATUSES = [
  "draft",
  "needs_testing",
  "trusted",
  "rejected",
  "archived",
] as const;

// Mirrors backend _PROMOTE_STATUS_BY_ENTRY in app/api/research.py — used
// only to preselect the dropdown so the user sees what will happen if
// they save without changing it. The backend recomputes anyway.
const DEFAULT_STATUS_BY_ENTRY: Record<string, Record<string, string>> = {
  hypothesis: {
    open: "needs_testing",
    running: "needs_testing",
    confirmed: "trusted",
    rejected: "rejected",
  },
  decision: {
    done: "trusted",
  },
  question: {
    open: "draft",
    done: "trusted",
  },
};

function defaultStatusFor(entry: ResearchEntry): string {
  return DEFAULT_STATUS_BY_ENTRY[entry.kind]?.[entry.status] ?? "draft";
}

export default function PromoteEntryForm({
  entry,
  strategyId,
  onCancel,
  onPromoted,
}: {
  entry: ResearchEntry;
  strategyId: number;
  onCancel: () => void;
  onPromoted: (card: KnowledgeCard) => void;
}) {
  const linkedCount = entry.knowledge_card_ids?.length ?? 0;
  const needsConfirm = linkedCount > 0;

  const [kind, setKind] = useState<string>("research_playbook");
  const [status, setStatus] = useState<string>(defaultStatusFor(entry));
  const [name, setName] = useState<string>(entry.title);
  const [summary, setSummary] = useState<string>("");
  const [body, setBody] = useState<string>(entry.body ?? "");
  const [confirmReplace, setConfirmReplace] = useState<boolean>(!needsConfirm);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (name.trim() === "") {
      setSubmitError("Name is required.");
      return;
    }
    if (needsConfirm && !confirmReplace) {
      setSubmitError(
        "Confirm that you want to add another card to this entry.",
      );
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload: PromotePayload = {
        kind,
        status,
        name: name.trim(),
        summary: summary.trim() === "" ? null : summary.trim(),
        body: body.trim() === "" ? null : body,
      };
      const resp = await fetch(
        `/api/strategies/${strategyId}/research/${entry.id}/promote`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!resp.ok) {
        setSubmitError(await describe(resp));
        return;
      }
      const created = (await resp.json()) as KnowledgeCard;
      onPromoted(created);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Network error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-border-strong bg-surface-alt p-4"
    >
      <div className="flex items-baseline justify-between gap-3">
        <p className="m-0 text-[10px] uppercase tracking-wider text-text-mute">
          Promote to knowledge card
        </p>
        <button
          type="button"
          onClick={onCancel}
          className="rounded p-1 text-text-mute hover:bg-surface hover:text-text"
          aria-label="Cancel"
        >
          <X className="h-3.5 w-3.5" strokeWidth={1.5} />
        </button>
      </div>

      {needsConfirm ? (
        <label className="mt-3 flex items-start gap-2 rounded-md border border-warn/40 bg-warn/10 p-2 text-xs text-text-dim">
          <input
            type="checkbox"
            checked={confirmReplace}
            onChange={(e) => setConfirmReplace(e.target.checked)}
            className="mt-0.5 h-3.5 w-3.5 accent-current"
          />
          <span>
            This entry already has {linkedCount} linked card
            {linkedCount === 1 ? "" : "s"}. Promoting again creates a new
            card and appends it.
          </span>
        </label>
      ) : null}

      <div className="mt-3 grid grid-cols-2 gap-3">
        <Field label="Card kind">
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className={inputClass()}
          >
            {CARD_KINDS.map((k) => (
              <option key={k} value={k}>
                {formatLabel(k)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Card status">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className={inputClass()}
          >
            {CARD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {formatLabel(s)}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Name" className="mt-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClass()}
          autoFocus
        />
      </Field>

      <Field label="Summary (optional)" className="mt-3">
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
          className={textareaClass()}
        />
      </Field>

      <Field label="Body (markdown OK)" className="mt-3">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={5}
          className={cn(textareaClass(), "font-mono")}
        />
      </Field>

      {submitError !== null ? (
        <p className="mt-2 text-xs text-neg">{submitError}</p>
      ) : null}

      <div className="mt-3 flex items-center justify-end gap-2">
        <Btn type="button" onClick={onCancel} disabled={submitting}>
          Cancel
        </Btn>
        <Btn
          variant="primary"
          type="submit"
          disabled={submitting || (needsConfirm && !confirmReplace)}
        >
          {submitting ? (
            <Loader2 className="mr-1.5 inline-block h-3.5 w-3.5 animate-spin" />
          ) : (
            <BookPlus className="mr-1.5 inline-block h-3.5 w-3.5" />
          )}
          Create card
        </Btn>
      </div>
    </form>
  );
}

function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("flex flex-col gap-1", className)}>
      <span className="text-[10px] uppercase tracking-wider text-text-mute">
        {label}
      </span>
      {children}
    </label>
  );
}

function inputClass(): string {
  return "w-full border border-border bg-surface px-2 py-1.5 text-[13px] text-text";
}

function textareaClass(): string {
  return "w-full resize-y border border-border bg-surface px-2 py-1.5 text-[12px] leading-relaxed text-text";
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    // fall through
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
