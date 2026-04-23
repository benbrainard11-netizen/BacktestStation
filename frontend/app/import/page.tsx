import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

export default function ImportPage() {
  return (
    <div>
      <PageHeader
        title="Import"
        description="Import existing backtest and live-trading result files (trades, equity, metrics, config, live status)"
      />
      <Placeholder
        phase="Phase 1 — Imported Results"
        note="Databento ingestion is a later phase; this page is for importing result files you already have."
      />
    </div>
  );
}
