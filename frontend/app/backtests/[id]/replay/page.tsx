import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

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
