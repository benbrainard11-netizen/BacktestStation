"use client";

import { Inbox as InboxIcon } from "lucide-react";

import { PageHeader } from "@/components/atoms";

/**
 * Research Inbox — placeholder page for Phase B.
 *
 * Phase D (next) wires this to the research_sidecar HTTP API:
 *   GET /ideas?label=promising,review&limit=50
 *
 * Each idea card will get a [Backtest] button that opens the run-a-backtest
 * form pre-filled with idea params, and submits with idea_id so the result
 * round-trips back to Discord.
 */
export default function InboxPage() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        eyebrow="RESEARCH · INBOX"
        title="Research Inbox"
        sub="Strategy ideas extracted by research_sidecar, scored and waiting for a backtest. Discord pings appear here too — click an idea to backtest it."
      />

      <div className="mt-8 rounded-lg border border-line bg-bg-2 p-12 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-accent-line bg-accent-soft">
          <InboxIcon size={20} className="text-accent" />
        </div>
        <h2 className="font-mono text-[13px] font-semibold uppercase tracking-[0.08em] text-ink-1">
          Inbox not wired yet
        </h2>
        <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-ink-3">
          The research_sidecar HTTP API ships in Phase C. After that, this page
          pulls live ideas score-sorted with one-click backtest buttons.
        </p>
        <p className="mx-auto mt-4 max-w-md font-mono text-[11px] text-ink-4">
          See <span className="text-ink-2">SIMPLIFY_PLAN.md</span> for the full
          end-to-end loop spec.
        </p>
      </div>
    </div>
  );
}
