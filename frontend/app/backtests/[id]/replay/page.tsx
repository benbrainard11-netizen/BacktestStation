import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

// Static export needs known IDs at build time. One placeholder route is
// enough for now; real run IDs will be plugged in once the importer lands.
export const dynamicParams = false;
export async function generateStaticParams() {
  return [{ id: "demo" }];
}

interface ReplayPageProps {
  params: Promise<{ id: string }>;
}

export default async function ReplayPage({ params }: ReplayPageProps) {
  const { id } = await params;
  return (
    <div>
      <PageHeader
        title={`Replay · Backtest ${id}`}
        description="Candlestick chart with entry/exit markers and stop/target lines"
      />
      <Placeholder phase="Phase 4 — Replay" />
    </div>
  );
}
