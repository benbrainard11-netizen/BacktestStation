import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

// Static export needs known IDs at build time. One placeholder route is
// enough for now; real run IDs will be plugged in once the importer lands.
export const dynamicParams = false;
export async function generateStaticParams() {
  return [{ id: "demo" }];
}

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
