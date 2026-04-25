import PageHeader from "@/components/PageHeader";
import PhaseShell, { type PhaseFeature } from "@/components/PhaseShell";

const FEATURES: PhaseFeature[] = [
  {
    title: "Data directory paths",
    detail:
      "Where raw Databento DBN, derived Parquet, and the SQLite metadata DB live. Edit-in-place with validation that the paths exist and are writable.",
    tag: "paths",
  },
  {
    title: "Futures contract specs",
    detail:
      "Per-symbol tick size, point value, commission, slippage, session hours. Authoritative source the engine reads — no magic numbers in code.",
    tag: "config",
  },
  {
    title: "Session hours",
    detail:
      "RTH / ETH ranges per instrument. Drives session labeling, EOD flatten, and the daily-loss accounting.",
    tag: "rules",
  },
  {
    title: "Theme + density",
    detail:
      "Dark is the default and likely the only theme we'll ever need. Density toggle (compact / regular) for table-heavy pages.",
    tag: "ui",
  },
  {
    title: "Keyboard shortcuts",
    detail:
      "Override Cmd+K, palette filters, default destinations. Power-user surface, off the main flow.",
    tag: "ui",
  },
  {
    title: "Telemetry + logs",
    detail:
      "Local-only diagnostic toggles — verbose engine logs, slow-query traces, data quality verbosity. Off by default.",
    tag: "diag",
  },
];

export default function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Local terminal configuration"
        meta="phase 3 · planned"
      />
      <PhaseShell
        phase="Phase 3"
        status="planned"
        title="Local terminal config."
        subtitle="Single source of truth for paths, contract specs, session hours, and the small handful of toggles a research workstation actually needs. Nothing here is account-level — this is a local-only app."
        rationale="Phase 1 + 2 hardcode the contract specs and paths because the imported-results loop is small enough that magic numbers don't bite yet. Settings becomes load-bearing when Phase 3 ingests data the engine consumes — at that point a wrong tick value silently invalidates every backtest, and a config surface stops being optional."
        sectionLabel="Settings"
        features={FEATURES}
        currentlyAt={{ label: "Sidebar nav", href: "/" }}
      />
    </div>
  );
}
