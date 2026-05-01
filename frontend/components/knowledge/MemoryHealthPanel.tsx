"use client";

import { Activity, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import Panel from "@/components/ui/Panel";
import Pill, { type PillTone } from "@/components/ui/Pill";
import { type BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type KnowledgeHealth = components["schemas"]["KnowledgeHealthRead"];
type Issue = components["schemas"]["KnowledgeHealthIssue"];

const SEVERITY_TONE: Record<Issue["severity"], PillTone> = {
  error: "neg",
  warn: "warn",
  info: "neutral",
};

const VISIBLE_ISSUES = 50;

export default function MemoryHealthPanel({
  refreshKey,
}: {
  // Bumped by the parent after card mutations so the panel re-fetches
  // — keeps the counts and issue list in step with what the user sees
  // in the card list without forcing a full page reload.
  refreshKey: number;
}) {
  const [health, setHealth] = useState<KnowledgeHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/knowledge/health", {
          cache: "no-store",
        });
        if (!response.ok) {
          if (!cancelled) setError(await describe(response));
          return;
        }
        const body = (await response.json()) as KnowledgeHealth;
        if (!cancelled) setHealth(body);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Network error");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (error !== null) {
    return (
      <Panel
        title="Memory health"
        meta={<span className="text-xs text-neg">{error}</span>}
      >
        <p className="m-0 text-xs text-text-mute">
          Could not load memory health.
        </p>
      </Panel>
    );
  }

  if (loading && health === null) {
    return (
      <Panel title="Memory health">
        <div className="flex items-center gap-2 text-text-dim">
          <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
          <span className="text-xs">Checking memory…</span>
        </div>
      </Panel>
    );
  }

  if (health === null) return null;

  const { counts, issues } = health;
  const warnCount = issues.filter((i) => i.severity === "warn").length;
  const errorCount = issues.filter((i) => i.severity === "error").length;
  const infoCount = issues.filter((i) => i.severity === "info").length;

  return (
    <Panel
      title="Memory health"
      meta={
        <span className="inline-flex items-center gap-1 text-xs text-text-mute">
          <Activity className="h-3.5 w-3.5" strokeWidth={1.5} />
          {counts.total_cards} cards
        </span>
      }
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <HealthTile label="Trusted" value={counts.trusted_cards} />
        <HealthTile
          label="Trusted w/o evidence"
          value={counts.trusted_without_evidence}
          tone={counts.trusted_without_evidence > 0 ? "warn" : "neutral"}
        />
        <HealthTile
          label="Needs testing"
          value={counts.needs_testing_cards}
          sub={
            counts.needs_testing_without_run > 0
              ? `${counts.needs_testing_without_run} no run`
              : undefined
          }
        />
        <HealthTile
          label="Stale drafts"
          value={counts.stale_drafts}
          sub={`>${30} days`}
          tone={counts.stale_drafts > 0 ? "info" : "neutral"}
        />
      </div>

      {issues.length === 0 ? (
        <p className="m-0 mt-3 text-xs text-text-mute">
          No memory health issues.
        </p>
      ) : (
        <div className="mt-3">
          <p className="m-0 mb-2 text-xs text-text-mute">
            {issues.length} issue{issues.length === 1 ? "" : "s"}
            {errorCount > 0 ? ` · ${errorCount} error` : ""}
            {warnCount > 0 ? ` · ${warnCount} warn` : ""}
            {infoCount > 0 ? ` · ${infoCount} info` : ""}
          </p>
          <ul className="m-0 flex max-h-64 list-none flex-col gap-1.5 overflow-y-auto p-0">
            {issues.slice(0, VISIBLE_ISSUES).map((issue, index) => (
              <li
                key={`${issue.code}-${issue.card_id ?? "x"}-${issue.research_entry_id ?? "x"}-${index}`}
                className="rounded-md border border-border bg-surface-alt p-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Pill tone={SEVERITY_TONE[issue.severity]}>
                    {issue.severity}
                  </Pill>
                  <span className="text-[12px] font-medium text-text">
                    {issue.title}
                  </span>
                  {issue.card_id !== null && issue.card_id !== undefined ? (
                    <span className="text-[10px] text-text-mute">
                      card #{issue.card_id}
                    </span>
                  ) : null}
                  {issue.research_entry_id !== null &&
                  issue.research_entry_id !== undefined ? (
                    <span className="text-[10px] text-text-mute">
                      research #{issue.research_entry_id}
                    </span>
                  ) : null}
                  {issue.strategy_id !== null &&
                  issue.strategy_id !== undefined ? (
                    <span className="text-[10px] text-text-mute">
                      strategy #{issue.strategy_id}
                    </span>
                  ) : null}
                </div>
                <p className="m-0 mt-1 text-[11px] leading-relaxed text-text-dim">
                  {issue.detail}
                </p>
              </li>
            ))}
          </ul>
          {issues.length > VISIBLE_ISSUES ? (
            <p className="m-0 mt-2 text-[11px] text-text-mute">
              +{issues.length - VISIBLE_ISSUES} more not shown
            </p>
          ) : null}
        </div>
      )}
    </Panel>
  );
}

function HealthTile({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: number;
  sub?: string;
  tone?: "neutral" | "warn" | "info";
}) {
  const valueClass =
    tone === "warn"
      ? "text-warn"
      : tone === "info"
        ? "text-text"
        : "text-text";
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2">
      <p className="m-0 text-[10px] uppercase tracking-wider text-text-mute">
        {label}
      </p>
      <p className={`m-0 mt-1 text-[18px] leading-none ${valueClass}`}>
        {value}
      </p>
      {sub ? (
        <p className="m-0 mt-1 text-[10px] text-text-mute">{sub}</p>
      ) : null}
    </div>
  );
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
