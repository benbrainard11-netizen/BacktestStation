import PageHeader from "@/components/PageHeader";
import PhaseShell, { type PhaseFeature } from "@/components/PhaseShell";

const FEATURES: PhaseFeature[] = [
  {
    title: "Dataset inventory",
    detail:
      "Every ingested instrument · schema kind · date range · row count · file path. The Vault index for everything Databento has produced.",
    tag: "schema",
  },
  {
    title: "Gap / duplicate / out-of-order report",
    detail:
      "Per-day quality scan: missing minutes, duplicate ticks, out-of-order timestamps, halt detection. Surfaces the data lies before they reach the engine.",
    tag: "report",
  },
  {
    title: "sha256 checksum index",
    detail:
      "Every Parquet file fingerprinted. Reproducibility audits anchor on the dataset hash — a backtest run records the hash of the data it consumed.",
    tag: "audit",
  },
  {
    title: "Last-verified timestamp",
    detail:
      "When the file was last opened + scanned + checksummed. Visual flag when a dataset hasn't been verified in N days.",
    tag: "ui",
  },
  {
    title: "Storage footprint",
    detail:
      "Per-symbol Parquet tonnage. MBP-1 is ~1 GB/symbol/month — visibility prevents quiet disk fill.",
    tag: "ops",
  },
  {
    title: "Re-ingest workflow",
    detail:
      "Trigger Databento pulls for missing date ranges. Background job log + retry semantics surfaced inline.",
    tag: "api",
  },
];

export default function DataHealthPage() {
  return (
    <div>
      <PageHeader
        title="Data Health"
        description="Dataset inventory, quality reports, sha256 checksums"
        meta="phase 3 · planned"
      />
      <PhaseShell
        phase="Phase 3"
        status="planned"
        title="The Data Vault."
        subtitle="Once Databento ingestion lands, every dataset that the engine can consume gets registered, fingerprinted, and continuously quality-scored from this surface."
        rationale="Phase 1 imports the result files you already have (CSV trades, equity, metrics, config). Phase 2 polished that surface. Phase 3 is when the app starts ingesting raw market data itself — until then there's nothing to display here, and showing fake datasets would mislead. The shape of this page is a contract for what the ingestion pipeline must produce."
        sectionLabel="Data Vault"
        features={FEATURES}
        currentlyAt={{ label: "Imported runs", href: "/backtests" }}
      />
    </div>
  );
}
