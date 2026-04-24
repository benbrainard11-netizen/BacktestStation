import MetricCard from "@/components/MetricCard";
import { MOCK_KPIS } from "@/lib/mocks/commandCenter";

export default function KpiRow() {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 2xl:grid-cols-8">
      {MOCK_KPIS.map((kpi) => (
        <MetricCard
          key={kpi.key}
          label={kpi.label}
          value={kpi.value}
          valueTone={kpi.valueTone}
          delta={kpi.delta}
          deltaTone={kpi.deltaTone}
        />
      ))}
    </div>
  );
}
