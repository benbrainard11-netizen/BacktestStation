import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

interface BacktestDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function BacktestDetailPage({
  params,
}: BacktestDetailPageProps) {
  const { id } = await params;
  return (
    <div>
      <PageHeader
        title={`Backtest ${id}`}
        description="Equity curve, drawdown, trade table, stats"
      />
      <Placeholder phase="Phase 4 — Results" />
    </div>
  );
}
