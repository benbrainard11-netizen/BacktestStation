"use client";

import Link from "next/link";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { ago, usePoll } from "@/lib/poll";

type Strategy = {
  id: number;
  name: string;
  slug: string;
  status: string;
  updated_at: string;
};

export default function StrategyBuilderPicker() {
  const strategies = usePoll<Strategy[]>("/api/strategies", 60_000);
  const all = strategies.kind === "data" ? strategies.data : [];

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <PageHeader
        eyebrow="STRATEGY BUILDER · PICK ONE"
        title="Strategy Builder"
        sub="Pick a strategy to enter the visual feature builder for one of its versions."
      />

      <Card className="mt-2 border-warn/30 bg-warn/10">
        <div className="px-5 py-4 text-[12px] text-warn">
          <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em]">
            EXPERIMENTAL
          </span>
          <p className="mt-1 leading-relaxed">
            The visual builder ports the mockup from{" "}
            <code className="font-mono">
              design_extract/anthropic_design_2/.../strategy-builder.jsx
            </code>
            . The <code className="font-mono">spec_json</code> contract between
            the builder UI and the engine has not been verified. Save is gated
            by a per-machine localStorage toggle inside the builder; it is
            disabled by default to prevent corrupting existing strategy versions
            until you confirm the round-trip with a code review.
          </p>
        </div>
      </Card>

      <Card className="mt-4">
        <CardHead title="Strategies" eyebrow={`${all.length} total`} />
        {strategies.kind === "loading" && (
          <div className="px-4 py-8 text-center text-[12px] text-ink-3">
            Loading…
          </div>
        )}
        {strategies.kind === "error" && (
          <div className="px-4 py-8 text-center text-[12px] text-neg">
            {strategies.message}
          </div>
        )}
        {strategies.kind === "data" && all.length === 0 && (
          <EmptyState
            title="no strategies"
            blurb="Create a strategy on /strategies first."
          />
        )}
        {strategies.kind === "data" && all.length > 0 && (
          <ul className="m-0 list-none p-0">
            {all.map((s) => (
              <li
                key={s.id}
                className="flex items-center gap-3 border-b border-line px-4 py-3 last:border-b-0 hover:bg-bg-2"
              >
                <Link
                  href={`/strategies/${s.id}/build`}
                  className="flex-1 font-mono text-[13px] font-semibold text-ink-0 hover:text-accent"
                >
                  {s.name}
                </Link>
                <Chip>{s.slug}</Chip>
                <Chip tone={s.status === "live" ? "pos" : "default"}>
                  {s.status}
                </Chip>
                <span className="font-mono text-[10.5px] text-ink-3">
                  {ago(s.updated_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
