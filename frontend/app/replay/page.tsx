import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";

export default function ReplayIndexPage() {
  return (
    <div>
      <PageHeader
        title="Replay"
        description="Pick a backtest run to replay its trades on the chart"
        meta="PHASE 1 · AWAITING IMPORT"
      />
      <div className="px-6 pb-6">
        <EmptyState
          label="No runs available to replay yet"
          detail="Once a backtest is imported, open it from the Backtests list to launch replay."
          willContain={[
            "List of imported runs",
            "Per-run strategy / symbol / period summary",
            "Launch replay shortcut",
          ]}
        />
      </div>
    </div>
  );
}
