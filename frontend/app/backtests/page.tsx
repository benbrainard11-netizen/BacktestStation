import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

export default function BacktestsPage() {
  return (
    <div>
      <PageHeader
        title="Backtests"
        description="All runs, filterable; compare two runs side by side"
      />
      <Placeholder phase="Phase 3 — Backtest workflow" />
    </div>
  );
}
