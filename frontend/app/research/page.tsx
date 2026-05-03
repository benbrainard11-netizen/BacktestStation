"use client";

import {
  Book,
  Clipboard,
  FlaskConical,
  Layers,
  Microscope,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { Card, CardHead, PageHeader, Stat } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import type { components } from "@/lib/api/generated";
import { ago, usePoll } from "@/lib/poll";

type Strategy = components["schemas"]["StrategyRead"];
type Experiment = components["schemas"]["ExperimentRead"];
type Note = components["schemas"]["NoteRead"];
type KnowledgeCard = {
  id: number;
  status: string;
  updated_at: string;
};

const POLL_MS = 60_000;

export default function ResearchRollupPage() {
  const strategies = usePoll<Strategy[]>("/api/strategies", POLL_MS);
  const experiments = usePoll<Experiment[]>("/api/experiments", POLL_MS);
  const notes = usePoll<Note[]>("/api/notes", POLL_MS);
  const knowledge = usePoll<KnowledgeCard[]>("/api/knowledge/cards", POLL_MS);

  const stratList = strategies.kind === "data" ? strategies.data : [];
  const expList = experiments.kind === "data" ? experiments.data : [];
  const noteList = notes.kind === "data" ? notes.data : [];
  const cardList = knowledge.kind === "data" ? knowledge.data : [];

  const pendingExperiments = expList.filter(
    (e) => e.decision === "pending",
  ).length;

  function dashOrCount(
    poll: { kind: "loading" } | { kind: "error" } | { kind: "data" },
    n: number,
  ): string {
    if (poll.kind === "loading") return "—";
    return String(n);
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        eyebrow="RESEARCH · CROSS-STRATEGY"
        title="Research"
        sub="Open hypotheses, decisions, and questions live under each strategy. Cross-strategy ledgers are linked below."
      />

      <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Strategies"
            value={dashOrCount(strategies, stratList.length)}
            sub={
              strategies.kind === "error"
                ? "backend down"
                : `${stratList.length === 1 ? "1 strategy" : `${stratList.length} strategies`}`
            }
          />
        </Card>
        <Card>
          <Stat
            label="Open experiments"
            value={dashOrCount(experiments, pendingExperiments)}
            sub={
              experiments.kind === "error"
                ? "backend down"
                : `${expList.length} total`
            }
            tone={pendingExperiments > 0 ? "warn" : "default"}
          />
        </Card>
        <Card>
          <Stat
            label="Knowledge cards"
            value={dashOrCount(knowledge, cardList.length)}
            sub={knowledge.kind === "error" ? "backend down" : "all statuses"}
          />
        </Card>
        <Card>
          <Stat
            label="Notes"
            value={dashOrCount(notes, noteList.length)}
            sub={notes.kind === "error" ? "backend down" : "freestanding + attached"}
          />
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHead
            eyebrow="strategies"
            title="Open a strategy's research workspace"
          />
          {strategies.kind === "loading" ? (
            <div className="px-5 py-6 font-mono text-[12px] text-ink-3">
              Loading strategies…
            </div>
          ) : strategies.kind === "error" ? (
            <EmptyState
              title="couldn't load strategies"
              blurb={`Backend returned: ${strategies.message}. The page will refresh on its own when the backend comes back.`}
            />
          ) : stratList.length === 0 ? (
            <EmptyState
              title="no strategies yet"
              blurb="Create one in the Strategy Catalog. Per-strategy hypotheses, decisions, and questions live there."
              action={
                <Link href="/strategies" className="btn btn-primary btn-sm">
                  Open Strategy Catalog
                </Link>
              }
            />
          ) : (
            <ul className="divide-y divide-line">
              {stratList.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`/strategies/${s.id}/research`}
                    className="group flex items-center gap-3 px-4 py-3 text-sm text-ink-1 transition-colors hover:bg-bg-2"
                  >
                    <span className="grid h-7 w-7 flex-shrink-0 place-items-center rounded border border-line bg-bg-2 text-ink-3 group-hover:text-accent">
                      <Layers size={14} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-ink-1 group-hover:text-accent">
                        {s.name}
                      </span>
                      <span className="block truncate font-mono text-[10.5px] text-ink-3">
                        {s.status} · created {ago(s.created_at)}
                      </span>
                    </span>
                    <span className="font-mono text-[12px] text-ink-4 group-hover:text-accent">
                      →
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHead eyebrow="ledgers" title="Cross-strategy" />
          <div className="grid gap-2 px-4 py-4">
            <LedgerRow
              href="/experiments"
              icon={FlaskConical}
              label="Experiments"
              sub={
                experiments.kind === "data"
                  ? `${expList.length} on ledger · ${pendingExperiments} pending`
                  : experiments.kind === "loading"
                    ? "loading…"
                    : "backend down"
              }
            />
            <LedgerRow
              href="/knowledge"
              icon={Book}
              label="Knowledge cards"
              sub={
                knowledge.kind === "data"
                  ? `${cardList.length} cards`
                  : knowledge.kind === "loading"
                    ? "loading…"
                    : "backend down"
              }
            />
            <LedgerRow
              href="/notes"
              icon={Clipboard}
              label="Notes"
              sub={
                notes.kind === "data"
                  ? `${noteList.length} entries`
                  : notes.kind === "loading"
                    ? "loading…"
                    : "backend down"
              }
            />
            <LedgerRow
              href="/prompts"
              icon={Sparkles}
              label="AI prompts"
              sub="paste into Claude or GPT"
            />
            <LedgerRow
              href="/compare"
              icon={Microscope}
              label="Compare runs"
              sub="diff up to 4 backtest runs side-by-side"
            />
          </div>
        </Card>
      </div>
    </div>
  );
}

function LedgerRow({
  href,
  icon: Icon,
  label,
  sub,
}: {
  href: string;
  icon: LucideIcon;
  label: string;
  sub?: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 rounded border border-line bg-bg-2 px-3 py-2.5 text-sm text-ink-1 transition-colors hover:border-accent-line hover:bg-accent-soft"
    >
      <span className="grid h-7 w-7 flex-shrink-0 place-items-center rounded border border-line bg-bg-1 text-ink-3 group-hover:text-accent">
        <Icon size={14} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-ink-1 group-hover:text-accent">
          {label}
        </span>
        {sub ? (
          <span className="block truncate font-mono text-[10.5px] text-ink-3">
            {sub}
          </span>
        ) : null}
      </span>
      <span className="font-mono text-[12px] text-ink-4 group-hover:text-accent">
        →
      </span>
    </Link>
  );
}
