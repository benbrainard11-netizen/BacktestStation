import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

interface StrategyDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function StrategyDetailPage({
  params,
}: StrategyDetailPageProps) {
  const { id } = await params;
  return (
    <div>
      <PageHeader
        title={`Strategy ${id}`}
        description="Strategy versions, status, tags, linked backtest runs"
      />
      <Placeholder phase="Phase 1 — Strategy Library" />
    </div>
  );
}
