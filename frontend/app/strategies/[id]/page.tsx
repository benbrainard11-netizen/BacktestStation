import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

// Static export needs known IDs at build time. One placeholder route is
// enough for now; real strategy IDs will be plugged in once the importer
// lands in Phase 1.
export const dynamicParams = false;
export async function generateStaticParams() {
  return [{ id: "demo" }];
}

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
