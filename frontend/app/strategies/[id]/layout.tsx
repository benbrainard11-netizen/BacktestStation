import { StrategyTabs } from "./StrategyTabs";

export default async function StrategyLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div>
      <StrategyTabs strategyId={id} />
      {children}
    </div>
  );
}
