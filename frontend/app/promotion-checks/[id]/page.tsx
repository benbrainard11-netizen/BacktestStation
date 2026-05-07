"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type PromotionCheck = components["schemas"]["StrategyPromotionCheckRead"];
type PromotionStatus = PromotionCheck["status"];

type LoadState =
  | { kind: "loading" }
  | { kind: "data"; check: PromotionCheck }
  | { kind: "error"; message: string };

const STATUS_TONE: Record<
  PromotionStatus,
  "pos" | "neg" | "warn" | "accent" | "default"
> = {
  pass_paper: "pos",
  research_only: "accent",
  killed: "neg",
  draft: "default",
  archived: "default",
};

const STATUS_LABEL: Record<PromotionStatus, string> = {
  pass_paper: "pass paper",
  research_only: "research only",
  killed: "killed",
  draft: "draft",
  archived: "archived",
};

/**
 * Promotion-check detail — full evidence view for one candidate verdict.
 * Reachable from the home catalog when no `strategy_id` is linked yet.
 */
export default function PromotionCheckDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const checkId = Number.parseInt(id, 10);
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    if (!Number.isFinite(checkId)) {
      setState({ kind: "error", message: `Invalid id: ${id}` });
      return;
    }
    let cancelled = false;
    const ctrl = new AbortController();
    async function load() {
      setState({ kind: "loading" });
      try {
        const r = await fetch(`/api/promotion-checks/${checkId}`, {
          cache: "no-store",
          signal: ctrl.signal,
        });
        if (!r.ok) {
          throw new Error(`${r.status} ${r.statusText || "Request failed"}`);
        }
        const check = (await r.json()) as PromotionCheck;
        if (!cancelled) setState({ kind: "data", check });
      } catch (err) {
        if (cancelled || (err instanceof Error && err.name === "AbortError")) return;
        setState({
          kind: "error",
          message: err instanceof Error ? err.message : "Network error",
        });
      }
    }
    void load();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [checkId, id]);

  if (state.kind === "loading") {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <PageHeader
          eyebrow="PROMOTION CHECK · LOADING"
          title="Loading evidence…"
        />
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <PageHeader eyebrow="PROMOTION CHECK · ERROR" title="Could not load check" />
        <Card className="mt-6 border-neg/30 bg-neg-soft">
          <div className="px-4 py-3 font-mono text-[12px] text-neg">{state.message}</div>
        </Card>
        <div className="mt-4">
          <Link
            href="/"
            className="font-mono text-[11px] text-accent hover:underline"
          >
            ← back to catalog
          </Link>
        </div>
      </div>
    );
  }

  const { check } = state;
  const tone = STATUS_TONE[check.status];

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <PageHeader
        eyebrow={`PROMOTION CHECK · #${check.id}`}
        title={check.candidate_name}
        sub={[check.source_repo, check.candidate_config_id]
          .filter(Boolean)
          .join(" · ")}
        right={<Chip tone={tone}>{STATUS_LABEL[check.status]}</Chip>}
      />

      <div className="mt-2 flex flex-wrap items-center gap-3 px-6 font-mono text-[10.5px] text-ink-3">
        <Link href="/" className="text-accent hover:underline">
          ← catalog
        </Link>
        {check.strategy_id != null && (
          <Link
            href={`/strategies/${check.strategy_id}`}
            className="hover:text-ink-1"
          >
            strategy #{check.strategy_id} →
          </Link>
        )}
        {check.strategy_version_id != null && (
          <span>version #{check.strategy_version_id}</span>
        )}
        {check.backtest_run_id != null && (
          <Link
            href={`/backtests/${check.backtest_run_id}`}
            className="hover:text-ink-1"
          >
            run #{check.backtest_run_id} →
          </Link>
        )}
        <span>created {fmtDate(check.created_at)}</span>
        {check.updated_at && <span>· updated {fmtDate(check.updated_at)}</span>}
      </div>

      <div className="mt-6 grid gap-4">
        {check.final_verdict && (
          <Card>
            <CardHead title="Final verdict" eyebrow="summary" />
            <div className="px-4 py-3 text-[13px] leading-relaxed text-ink-1">
              {check.final_verdict}
            </div>
          </Card>
        )}

        <ReasonsCard
          title="Pass reasons"
          eyebrow="why it works"
          tone="pos"
          reasons={check.pass_reasons}
        />

        <ReasonsCard
          title="Fail reasons"
          eyebrow="why it doesn't"
          tone="neg"
          reasons={check.fail_reasons}
        />

        {check.next_actions && check.next_actions.length > 0 && (
          <Card>
            <CardHead title="Next actions" eyebrow="follow-ups" />
            <ul className="grid gap-1.5 px-4 py-3 text-[12.5px] text-ink-1">
              {check.next_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-0.5 font-mono text-[11px] text-ink-4">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="flex-1 leading-snug">{a}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        <JsonCard title="Metrics" eyebrow="metrics_json" obj={check.metrics_json} />
        <JsonCard
          title="Robustness"
          eyebrow="robustness_json"
          obj={check.robustness_json}
        />
        <JsonCard
          title="Evidence paths"
          eyebrow="evidence_paths_json"
          obj={check.evidence_paths_json}
        />

        {check.notes && (
          <Card>
            <CardHead title="Notes" eyebrow="freeform" />
            <pre className="whitespace-pre-wrap px-4 py-3 text-[12.5px] leading-relaxed text-ink-1">
              {check.notes}
            </pre>
          </Card>
        )}
      </div>
    </div>
  );
}

function ReasonsCard({
  title,
  eyebrow,
  tone,
  reasons,
}: {
  title: string;
  eyebrow: string;
  tone: "pos" | "neg";
  reasons: string[] | null;
}) {
  if (!reasons || reasons.length === 0) return null;
  const sign = tone === "pos" ? "+" : "−";
  const color = tone === "pos" ? "text-pos" : "text-neg";
  return (
    <Card>
      <CardHead title={title} eyebrow={eyebrow} />
      <ul className="grid gap-1.5 px-4 py-3 text-[12.5px] text-ink-1">
        {reasons.map((r, i) => (
          <li key={i} className="flex items-start gap-2 leading-snug">
            <span className={cn("mt-0.5 font-mono text-[11px]", color)}>{sign}</span>
            <span className="flex-1">{r}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function JsonCard({
  title,
  eyebrow,
  obj,
}: {
  title: string;
  eyebrow: string;
  obj: { [key: string]: unknown } | null;
}) {
  if (!obj || Object.keys(obj).length === 0) return null;
  return (
    <Card>
      <CardHead title={title} eyebrow={eyebrow} />
      <pre className="max-h-96 overflow-auto px-4 py-3 font-mono text-[11px] leading-relaxed text-ink-1">
        {JSON.stringify(obj, null, 2)}
      </pre>
    </Card>
  );
}
