import Panel from "@/components/Panel";
import CalendarHeatmap from "@/components/prop-simulator/CalendarHeatmap";
import type { DailyPnL } from "@/lib/prop-simulator/types";

interface DailyPnLPanelProps {
  data: DailyPnL[];
}

export default function DailyPnLPanel({ data }: DailyPnLPanelProps) {
  return (
    <Panel
      title="Daily P&L · underlying backtest"
      meta={`${data.length} sessions · 26 weeks`}
    >
      <CalendarHeatmap data={data} />
    </Panel>
  );
}
