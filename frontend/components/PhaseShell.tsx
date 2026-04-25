// Shared shell for "this section lands in a future phase" pages.
// Renders a dimensional hero with a phase stamp + a grid of feature
// preview cards in a blueprint-y treatment. Same visual language as
// the prop-simulator panels — depth shadows, ambient grid behind.

import Link from "next/link";

import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";

export interface PhaseFeature {
  title: string;
  detail: string;
  /** Optional small monospace tag like "schema" / "ui" / "api". */
  tag?: string;
}

interface PhaseShellProps {
  phase: string; // "Phase 3"
  status: "planned" | "in-progress" | "blocked";
  title: string;
  subtitle: string;
  rationale: string;
  sectionLabel: string; // "What will live here", "Configuration"
  features: PhaseFeature[];
  /** Optional pointer to the currently working alternative for this concept. */
  currentlyAt?: { label: string; href: string };
}

const STATUS_TONE: Record<PhaseShellProps["status"], string> = {
  planned: "border-amber-900 bg-amber-950/30 text-amber-300",
  "in-progress": "border-emerald-900 bg-emerald-950/30 text-emerald-300",
  blocked: "border-rose-900 bg-rose-950/30 text-rose-300",
};

const STATUS_LABEL: Record<PhaseShellProps["status"], string> = {
  planned: "Planned",
  "in-progress": "In progress",
  blocked: "Blocked",
};

function PhaseStamp({ phase }: { phase: string }) {
  return (
    <div
      aria-hidden="true"
      className="inline-flex shrink-0 items-center gap-2 rounded-md border border-zinc-700 bg-zinc-950 px-2.5 py-1"
    >
      <span className="h-1.5 w-1.5 rotate-45 bg-zinc-500" />
      <span className="font-mono text-[10px] uppercase tracking-[0.32em] text-zinc-300">
        {phase}
      </span>
      <span className="h-1.5 w-1.5 rotate-45 bg-zinc-500" />
    </div>
  );
}

function StatusPill({ status }: { status: PhaseShellProps["status"] }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.32em]",
        STATUS_TONE[status],
      )}
    >
      <span
        aria-hidden="true"
        className="h-1.5 w-1.5 rounded-full bg-current opacity-70"
      />
      {STATUS_LABEL[status]}
    </span>
  );
}

function FeatureCard({ feature, index }: { feature: PhaseFeature; index: number }) {
  return (
    <div className="group flex flex-col gap-3 rounded-md border border-dashed border-zinc-800/80 bg-zinc-950/40 p-4 shadow-edge-top transition-colors duration-200 hover:border-zinc-700">
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.32em] text-zinc-600">
          {String(index + 1).padStart(2, "0")}
        </span>
        {feature.tag ? (
          <span className="rounded-sm border border-zinc-800 bg-zinc-900 px-1.5 py-px font-mono text-[9px] uppercase tracking-widest text-zinc-500">
            {feature.tag}
          </span>
        ) : null}
      </div>
      <h3 className="text-sm font-light text-zinc-100">{feature.title}</h3>
      <p className="text-xs leading-relaxed text-zinc-500">{feature.detail}</p>
      <div className="mt-auto flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.32em] text-zinc-700">
        <span aria-hidden="true" className="h-px w-6 bg-zinc-800" />
        <span>not built yet</span>
      </div>
    </div>
  );
}

export default function PhaseShell({
  phase,
  status,
  title,
  subtitle,
  rationale,
  sectionLabel,
  features,
  currentlyAt,
}: PhaseShellProps) {
  return (
    <div className="flex flex-col gap-4 px-6 pb-10 pt-6">
      <Panel
        title={`${sectionLabel} · ${phase}`}
        meta="design preview · not wired"
        tone="hero"
      >
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <PhaseStamp phase={phase} />
              <StatusPill status={status} />
            </div>
            <h2
              className="font-extralight tracking-tight text-zinc-50"
              style={{ fontSize: "clamp(2.5rem, 6vw, 4.5rem)", lineHeight: 0.95 }}
            >
              {title}
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-zinc-400">
              {subtitle}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2 text-right">
            <span className="font-mono text-[10px] uppercase tracking-[0.32em] text-zinc-600">
              Currently at
            </span>
            {currentlyAt ? (
              <Link
                href={currentlyAt.href}
                className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 transition-all duration-150 hover:-translate-y-px hover:border-zinc-600 hover:bg-zinc-800 hover:shadow-dim-hover"
              >
                {currentlyAt.label} →
              </Link>
            ) : (
              <span className="font-mono text-[10px] uppercase tracking-[0.32em] text-zinc-700">
                no current surface
              </span>
            )}
          </div>
        </div>
      </Panel>

      <Panel title="Why it's empty" meta="rationale">
        <p className="max-w-3xl text-sm leading-relaxed text-zinc-300">
          {rationale}
        </p>
      </Panel>

      <Panel
        title="What will live here"
        meta={`${features.length} planned · ordered`}
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, i) => (
            <FeatureCard key={feature.title} feature={feature} index={i} />
          ))}
        </div>
      </Panel>
    </div>
  );
}
