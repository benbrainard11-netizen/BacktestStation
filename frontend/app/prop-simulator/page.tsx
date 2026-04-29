import PageHeader from "@/components/PageHeader";
import NotImplemented from "@/components/prop-simulator/NotImplemented";
import Btn from "@/components/ui/Btn";

export default function PropSimulatorDashboardPage() {
  return (
    <div className="pb-10">
      <PageHeader
        title="Prop Firm Simulator"
        description="Monte Carlo simulation across imported backtests, firm rule profiles, sampling modes, and risk levels."
      />
      <div className="flex flex-col gap-4 px-8">
        <NotImplemented
          title="No dashboard summary yet"
          description="The cross-simulation dashboard (best setups, EV summary, recent runs preview) needs an aggregation endpoint that doesn't exist yet. Real simulation runs and firm rules already work — open them directly below."
        />
        <div className="grid grid-cols-3 gap-3">
          <Btn href="/prop-simulator/runs">Simulation runs</Btn>
          <Btn href="/prop-simulator/firms">Firm rules</Btn>
          <Btn href="/prop-simulator/new" variant="primary">
            New simulation
          </Btn>
        </div>
      </div>
    </div>
  );
}
