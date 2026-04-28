// Shared shell for "this section lands in a future phase" pages. Direction A
// — calm panel layout (no hero stamp, no dimensional treatment), just a
// header + rationale + planned-feature grid. Status is a Pill, the optional
// "currently at" link is a Btn.

import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill, { type PillTone } from "@/components/ui/Pill";

export interface PhaseFeature {
  title: string;
  detail: string;
  /** Optional small tag like "schema" / "ui" / "api". */
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

const STATUS_TONE: Record<PhaseShellProps["status"], PillTone> = {
  planned: "warn",
  "in-progress": "pos",
  blocked: "neg",
};

const STATUS_LABEL: Record<PhaseShellProps["status"], string> = {
  planned: "Planned",
  "in-progress": "In progress",
  blocked: "Blocked",
};

function FeatureCard({
  feature,
  index,
}: {
  feature: PhaseFeature;
  index: number;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-dashed border-border bg-surface p-4 transition-colors hover:border-border-strong">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs tabular-nums text-text-mute">
          {String(index + 1).padStart(2, "0")}
        </span>
        {feature.tag ? (
          <span className="rounded border border-border bg-surface-alt px-2 py-[2px] text-xs text-text-dim">
            {feature.tag}
          </span>
        ) : null}
      </div>
      <h3 className="m-0 text-[13px] font-medium text-text">{feature.title}</h3>
      <p className="m-0 text-xs leading-relaxed text-text-dim">
        {feature.detail}
      </p>
      <p className="m-0 mt-auto text-xs text-text-mute">Not built yet</p>
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
    <div className="flex flex-col gap-4 px-8 pb-10 pt-8 auto-enter">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-mute">{phase}</span>
            <Pill tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Pill>
          </div>
          <h1 className="m-0 text-[26px] font-medium leading-tight tracking-[-0.02em] text-text">
            {title}
          </h1>
          <p className="m-0 max-w-2xl text-sm leading-relaxed text-text-dim">
            {subtitle}
          </p>
        </div>
        {currentlyAt ? (
          <div className="flex flex-col items-end gap-1.5">
            <span className="text-xs text-text-mute">Currently at</span>
            <Btn href={currentlyAt.href}>{currentlyAt.label} →</Btn>
          </div>
        ) : null}
      </header>

      <Panel title="Why it's empty" meta="rationale">
        <p className="m-0 max-w-3xl text-sm leading-relaxed text-text-dim">
          {rationale}
        </p>
      </Panel>

      <Panel
        title={sectionLabel}
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
